-- Re-inject Notion inline formatting that Pandoc's LaTeX writer drops
-- when reading HTML: it keeps this info in the AST (visible via `-t native`)
-- but the writer itself has no built-in handling for it, so without this
-- filter the text is emitted with no color/underline at all.
--
-- Colored text: <mark data-notion-highlight="COLOR"> -> \textcolor{}{}.
-- Highlighted background: <mark data-notion-highlight="COLOR_background">
-- -> \hl{} (soul) with the highlight color set to Notion's own flattened
-- pastel tone (its CSS uses a low-alpha color over white; soul highlights
-- are opaque, so the colors below are that same alpha blend pre-computed).
--
-- Underline: Notion has no semantic <u> tag, it emits
-- <span style="border-bottom:...solid"> -> \ul{} (soul), matching what
-- Pandoc already produces natively for a real <u> tag.
--
-- Dark mode (--dark on the CLI): the pipeline sets NOTION2TEX_DARK=1 in
-- pandoc's environment so this filter can pick colors that stay readable
-- on the dark gray page fix_latex.py sets up in that case — Notion's own
-- palette above is tuned for a white page and washes out on dark gray.
local DARK_MODE = os.getenv("NOTION2TEX_DARK") == "1"
-- Matches _DARK_BODY_TEXT in fix_latex.py: tcolorbox composes its content in
-- its own box, which does not inherit the ambient \color set on the page,
-- so callouts/bookmark cards need this set explicitly or their text comes
-- out in LaTeX's default black — invisible on the dark page background.
local DARK_TEXT = "225,225,225"

local TEXT_COLORS = {
  gray   = "125,122,117",
  brown  = "159,118,90",
  orange = "210,123,45",
  yellow = "203,148,52",
  teal   = "80,148,110",
  blue   = "56,125,201",
  purple = "154,107,180",
  pink   = "193,76,138",
  red    = "207,81,72",
}

local DARK_TEXT_COLORS = {
  gray   = "190,190,188",
  brown  = "198,152,120",
  orange = "235,151,79",
  yellow = "224,183,88",
  teal   = "119,199,157",
  blue   = "109,163,224",
  purple = "190,150,224",
  pink   = "224,140,181",
  red    = "224,120,110",
}

local BACKGROUND_COLORS = {
  gray   = "240,239,237",
  brown  = "245,237,233",
  orange = "251,235,222",
  yellow = "249,243,220",
  teal   = "232,241,236",
  blue   = "229,242,252",
  purple = "243,235,249",
  pink   = "250,233,241",
  red    = "252,233,231",
}

local DARK_BACKGROUND_COLORS = {
  gray   = "55,55,55",
  brown  = "66,48,38",
  orange = "77,51,25",
  yellow = "72,60,20",
  teal   = "26,58,45",
  blue   = "26,52,74",
  purple = "58,40,74",
  pink   = "72,38,55",
  red    = "74,36,34",
}

if DARK_MODE then
  TEXT_COLORS = DARK_TEXT_COLORS
  BACKGROUND_COLORS = DARK_BACKGROUND_COLORS
end

local function wrap(inlines, before, after)
  local wrapped = { pandoc.RawInline("latex", before) }
  for _, inline in ipairs(inlines) do
    table.insert(wrapped, inline)
  end
  table.insert(wrapped, pandoc.RawInline("latex", after))
  return wrapped
end

function Span(el)
  local inlines = el.content
  local changed = false

  local highlight = el.attributes["notion-highlight"]
  if highlight then
    local base = highlight:match("^(.-)_background$")
    if base then
      local rgb = BACKGROUND_COLORS[base]
      if rgb then
        -- \sethlcolor takes a color name, not an inline model like
        -- \textcolor[RGB]{...}, so define one locally first.
        inlines = wrap(
          inlines,
          "{\\definecolor{notionhl}{RGB}{" .. rgb .. "}"
            .. "\\sethlcolor{notionhl}\\hl{",
          "}}"
        )
        changed = true
      end
    else
      local rgb = TEXT_COLORS[highlight]
      if rgb then
        inlines = wrap(inlines, "\\textcolor[RGB]{" .. rgb .. "}{", "}")
        changed = true
      end
    end
  end

  local style = el.attributes["style"]
  if style and style:match("border%-bottom%s*:") then
    inlines = wrap(inlines, "\\ul{", "}")
    changed = true
  end

  if not changed then
    -- Pandoc wraps every Span in a bare LaTeX {...} group by default. A
    -- span we don't do anything with (e.g. highlight-default, meaning "no
    -- color") would otherwise leave that empty group in the output; nested
    -- inside \st{}/\ul{} (from a sibling <del>/underline wrapper), soul
    -- cannot re-tokenize hyphenatable text across the extra group and
    -- errors with "Reconstruction failed". Unwrap instead of passing it
    -- through unchanged.
    return el.content
  end
  return inlines
end

-- Notion's side-by-side column layout: <div class="column-list"> containing
-- one <div class="column" data-notion-column-ratio="0.xx"> per column.
-- Pandoc has no notion of a flex/columns layout, so left alone this just
-- flattens every column into stacked paragraphs. Rebuild it as adjacent
-- top-aligned minipages, each sized from Notion's own ratio.
--
-- GAP_FRAC approximates Notion's 46px inter-column gap as a fraction of the
-- ~900px export content width.
local GAP_FRAC = 0.05

local function render_columns(el)
  local columns = {}
  for _, block in ipairs(el.content) do
    if block.t == "Div" and block.classes:includes("column") then
      table.insert(columns, block)
    end
  end

  local n = #columns
  if n < 2 then
    return nil
  end

  local usable = 1 - GAP_FRAC * (n - 1)
  local parts = { "\\noindent%\n" }
  for i, column in ipairs(columns) do
    local ratio = tonumber(column.attributes["notion-column-ratio"]) or (1 / n)
    local width = ratio * usable
    local content_latex = pandoc.write(pandoc.Pandoc(column.content), "latex")
    table.insert(parts, string.format(
      "\\begin{minipage}[t]{%.4f\\linewidth}\n%s\n\\end{minipage}%%\n",
      width,
      content_latex
    ))
    if i < n then
      table.insert(parts, string.format("\\hspace{%.4f\\linewidth}%%\n", GAP_FRAC))
    end
  end

  return pandoc.RawBlock("latex", table.concat(parts))
end

-- Notion's callout: <aside class="...callout" data-notion-callout-icon="X"
-- data-notion-callout-background="COLOR_background">, renamed to <div> by
-- clean_html.py so Pandoc keeps it as a Div (it drops <aside> outright).
-- Its children are an icon-only div and a content div; render as a rounded,
-- colored tcolorbox with the icon prefixed to the content.
local function is_icon_placeholder(block)
  if block.t ~= "Div" or #block.content ~= 1 or block.content[1].t ~= "Plain" then
    return false
  end
  local plain = block.content[1]
  return #plain.content == 1
    and plain.content[1].t == "Span"
    and plain.content[1].classes:includes("icon")
end

local function render_callout(el)
  local bg = el.attributes["notion-callout-background"]
  local base = (bg and bg:match("^(.-)_background$")) or bg
  local rgb = (base and BACKGROUND_COLORS[base]) or BACKGROUND_COLORS.gray
  local icon = el.attributes["notion-callout-icon"] or ""

  local body_blocks = {}
  for _, block in ipairs(el.content) do
    if not is_icon_placeholder(block) then
      table.insert(body_blocks, block)
    end
  end
  local body_latex = pandoc.write(pandoc.Pandoc(body_blocks), "latex")
  local prefix = icon ~= "" and ("\\textbf{\\large " .. icon .. "} ") or ""
  -- tcolorbox composes its content separately from the page's ambient
  -- \color (see DARK_TEXT above), so set it explicitly in dark mode.
  local text_color = DARK_MODE and ("\\color[RGB]{" .. DARK_TEXT .. "}") or ""

  local tex = "{\\definecolor{notioncallout}{RGB}{" .. rgb .. "}\n"
    .. "\\begin{tcolorbox}[colback=notioncallout,boxrule=0pt,arc=3mm,"
    .. "left=0.9em,right=0.9em,top=0.6em,bottom=0.6em]\n"
    .. text_color .. prefix .. body_latex .. "\n"
    .. "\\end{tcolorbox}}"
  return pandoc.RawBlock("latex", tex)
end

function Div(el)
  if el.classes:includes("column-list") then
    return render_columns(el)
  end
  if el.classes:includes("callout") then
    return render_callout(el)
  end
  return nil
end

-- Notion's "web bookmark" block: an <a class="bookmark source"> wrapping a
-- title/description/favicon/url panel plus a preview image. Pandoc reads
-- the outer <a> as an empty Link (it cannot wrap block content) and hoists
-- its actual children (the bookmark-info Div and the preview Image) up as
-- siblings inside a Figure — so the raw output is just a link, a floating
-- favicon and preview image, and loose title/description text, with no
-- card layout at all. Rebuild it as a bordered two-column card, matching
-- Notion's own bookmark CSS (thin gray border, text left, image right).
local function find_div(blocks, class_name)
  for _, block in ipairs(blocks) do
    if block.t == "Div" and block.classes:includes(class_name) then
      return block
    end
  end
  return nil
end

local function find_link_target(blocks)
  for _, block in ipairs(blocks) do
    if block.t == "Plain" or block.t == "Para" then
      for _, inline in ipairs(block.content) do
        if inline.t == "Link" then
          return inline.target
        end
      end
    end
  end
  return nil
end

local function find_image(blocks, class_name)
  for _, block in ipairs(blocks) do
    if block.t == "Plain" or block.t == "Para" then
      for _, inline in ipairs(block.content) do
        if inline.t == "Image" and inline.classes:includes(class_name) then
          return inline
        end
      end
    elseif block.t == "Div" then
      local found = find_image(block.content, class_name)
      if found then
        return found
      end
    end
  end
  return nil
end

local function render_bookmark(el, info)
  local url = find_link_target(el.content) or ""
  local title_latex, desc_latex = "", ""

  local text_div = find_div(info.content, "bookmark-text")
  if text_div then
    local title_div = find_div(text_div.content, "bookmark-title")
    local desc_div = find_div(text_div.content, "bookmark-description")
    if title_div then
      title_latex = pandoc.write(pandoc.Pandoc(title_div.content), "latex")
    end
    if desc_div then
      desc_latex = pandoc.write(pandoc.Pandoc(desc_div.content), "latex")
    end
  end

  local preview = find_image(el.content, "bookmark-image")
  local text_width = preview and "0.62" or "0.94"

  local text_block = "\\textbf{" .. title_latex .. "}\\\\[0.3em]\n"
    .. "{\\small " .. desc_latex .. "}\\\\[0.5em]\n"
    .. "{\\footnotesize\\url{" .. url .. "}}"

  -- In dark mode, slightly lighter than the dark page background (defined
  -- in fix_latex.py) with a light-gray border instead of near-black.
  local preamble = DARK_MODE
    and "{\\definecolor{notionbookmarkbg}{RGB}{45,45,45}"
    or ""
  local box_colors = DARK_MODE
    and "colback=notionbookmarkbg,colframe=white!30"
    or "colback=white,colframe=black!25"
  -- Same tcolorbox color-isolation issue as the callout above.
  local text_color = DARK_MODE and ("\\color[RGB]{" .. DARK_TEXT .. "}") or ""
  local parts = {
    preamble,
    "\\begin{tcolorbox}[" .. box_colors .. ",boxrule=0.5pt,arc=2mm,",
    "left=0.8em,right=0.8em,top=0.6em,bottom=0.6em]\n",
    text_color,
    "\\noindent\\begin{minipage}[c]{", text_width, "\\linewidth}\n",
    text_block,
    "\n\\end{minipage}%\n",
  }
  if preview then
    table.insert(parts, "\\hfill\\begin{minipage}[c]{0.30\\linewidth}\n"
      .. "\\includegraphics[width=\\linewidth,keepaspectratio]{" .. preview.src .. "}"
      .. "\n\\end{minipage}%\n")
  end
  table.insert(parts, "\\end{tcolorbox}")
  if DARK_MODE then
    table.insert(parts, "}")
  end

  return pandoc.RawBlock("latex", table.concat(parts))
end

function Figure(el)
  local info = find_div(el.content, "bookmark-info")
  if not info then
    return nil
  end
  return render_bookmark(el, info)
end

-- Notion's quote block is a plain <blockquote>, which Pandoc already
-- converts natively to \begin{quote}; that environment has no visual
-- marker at all though, while Notion always shows a left border. Match it
-- with framed's ready-made \begin{leftbar} (a 3pt vertical rule + padding,
-- same as Notion's own blockquote CSS) instead of plain \quote.
function BlockQuote(el)
  local body_latex = pandoc.write(pandoc.Pandoc(el.content), "latex")
  return pandoc.RawBlock("latex", "\\begin{leftbar}\n" .. body_latex .. "\n\\end{leftbar}")
end

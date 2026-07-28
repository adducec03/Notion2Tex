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

function Div(el)
  if not el.classes:includes("column-list") then
    return nil
  end

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

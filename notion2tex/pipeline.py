"""Orchestrate the full Notion HTML → PDF pipeline."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from notion2tex.clean_html import clean_html_for_pandoc
from notion2tex.cleanup import cleanup_build_artifacts
from notion2tex.console import console
from notion2tex.fix_latex import fix_latex
from notion2tex.zip_export import resolve_input


@dataclass(frozen=True)
class BuildResult:
    html: Path
    tex: Path
    pdf: Path | None


def required_external_tools() -> tuple[str, ...]:
    return ("pandoc", "pdflatex")


def missing_tools() -> list[str]:
    return [cmd for cmd in required_external_tools() if shutil.which(cmd) is None]


def _run(cmd: list[str], *, cwd: Path, quiet: bool, check: bool = True) -> int:
    kwargs: dict = {"cwd": cwd, "check": check, "text": True}
    if quiet:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    result = subprocess.run(cmd, **kwargs)
    return result.returncode


def _run_pdflatex(tex_name: str, *, cwd: Path, quiet: bool) -> int:
    """Run pdflatex; exit code may be non-zero even when a PDF is produced."""
    return _run(
        ["pdflatex", "-interaction=nonstopmode", tex_name],
        cwd=cwd,
        quiet=quiet,
        check=False,
    )


def convert(
    input_path: str | Path,
    *,
    extract_dir: Path | None = None,
    tex_only: bool = False,
    quiet: bool = True,
) -> BuildResult:
    """
    Run clean → pandoc → fix_latex → pdflatex (×2).

    *input_path* may be a Notion export ``.zip`` or a ``.html`` file.
    Outputs are written next to the HTML so relative image paths stay valid.
    """
    input_path = Path(input_path).expanduser().resolve()
    html = resolve_input(input_path, extract_dir=extract_dir)

    missing = missing_tools()
    if missing and not tex_only:
        raise RuntimeError(
            "Missing required tools: "
            + ", ".join(missing)
            + ". Install Pandoc and a TeX distribution (TeX Live / MacTeX), "
            "or use --tex-only to stop after generating the .tex file."
        )
    if "pandoc" in missing:
        raise RuntimeError("Missing required tool: pandoc")

    work_dir = html.parent
    base = html.stem
    clean_html = work_dir / f"{base}_clean.html"
    tex = work_dir / f"{base}.tex"
    pdf = work_dir / f"{base}.pdf"

    total_steps = 3 if tex_only else 4
    console.banner(input_path=str(input_path), page=html.name)

    console.step(1, total_steps, "Clean HTML")
    clean_html_for_pandoc(str(html), str(clean_html))

    console.step(2, total_steps, "Pandoc → LaTeX")
    with console.task("Converting HTML to LaTeX (pandoc)"):
        _run(
            ["pandoc", str(clean_html), "-f", "html", "-t", "latex", "-s", "-o", str(tex)],
            cwd=work_dir,
            quiet=quiet,
        )
    console.detail(f"Wrote {tex.name}")

    console.step(3, total_steps, "Fix LaTeX")
    with console.task("Applying LaTeX fixes"):
        fix_latex(str(tex))

    if tex_only:
        removed = cleanup_build_artifacts(work_dir, base)
        if removed:
            console.detail(f"Removed {len(removed)} intermediate file(s)")
        print()
        console.success(f"LaTeX ready: {tex}")
        return BuildResult(html=html, tex=tex, pdf=None)

    console.step(4, total_steps, "Build PDF")
    for aux in (f"{base}.aux", f"{base}.toc", f"{base}.out"):
        (work_dir / aux).unlink(missing_ok=True)

    pdf_bar = console.progress(2, "pdflatex")
    last_rc = 0
    for pass_num in range(1, 3):
        with console.task(f"pdflatex pass {pass_num}/2"):
            last_rc = _run_pdflatex(tex.name, cwd=work_dir, quiet=quiet)
        pdf_bar.advance(sublabel=f"Pass {pass_num}/2")
    pdf_bar.finish("PDF build")

    if not pdf.is_file():
        log = work_dir / f"{base}.log"
        hint = f" See {log} for details." if log.is_file() else ""
        raise RuntimeError(f"PDF was not created: {pdf}.{hint}")

    if last_rc != 0:
        log = work_dir / f"{base}.log"
        console.warn(
            f"pdflatex exited with code {last_rc}; PDF was written. "
            f"Review {log.name} for warnings."
        )

    removed = cleanup_build_artifacts(work_dir, base)
    if removed:
        console.detail(f"Removed {len(removed)} intermediate file(s)")

    print()
    console.success(f"PDF ready: {pdf}")
    return BuildResult(html=html, tex=tex, pdf=pdf)

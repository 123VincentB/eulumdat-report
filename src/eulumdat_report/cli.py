"""cli.py — eulumdat-report command-line interface."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from .collector import ReportCollector
from .renderer import ReportRenderer

logger = logging.getLogger(__name__)


@click.command()
@click.argument("ldt_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--output-dir", "-o",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Output directory (default: same directory as LDT_FILE).",
)
@click.option(
    "--template",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Custom Jinja2 HTML template (default: built-in default.html).",
)
@click.option("--html/--no-html", default=True, show_default=True, help="Generate HTML output.")
@click.option("--pdf/--no-pdf",   default=True, show_default=True, help="Generate PDF output.")
@click.option("-v", "--verbose",  is_flag=True, help="Enable debug logging.")
def main(
    ldt_file: Path,
    output_dir: Path | None,
    template: Path | None,
    html: bool,
    pdf: bool,
    verbose: bool,
) -> None:
    """Generate a photometric datasheet (HTML/PDF) from an EULUMDAT .ldt file."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not html and not pdf:
        click.echo("Nothing to do: both --no-html and --no-pdf specified.", err=True)
        sys.exit(1)

    dest = output_dir if output_dir is not None else ldt_file.parent
    dest.mkdir(parents=True, exist_ok=True)

    stem = ldt_file.stem

    # ── Collect ──────────────────────────────────────────────────────────────
    click.echo(f"Reading {ldt_file.name} ...")
    try:
        data = ReportCollector.collect(ldt_file)
    except Exception as exc:
        click.echo(f"Error reading {ldt_file}: {exc}", err=True)
        sys.exit(1)

    # ── HTML ─────────────────────────────────────────────────────────────────
    if html:
        html_path = dest / f"{stem}.html"
        try:
            html_str = ReportRenderer.render_html(data, template_path=template)
            html_path.write_text(html_str, encoding="utf-8")
            click.echo(f"HTML: {html_path}")
        except Exception as exc:
            click.echo(f"Error generating HTML: {exc}", err=True)
            sys.exit(1)

    # ── PDF ──────────────────────────────────────────────────────────────────
    if pdf:
        pdf_path = dest / f"{stem}.pdf"
        try:
            ReportRenderer.render_pdf(data, pdf_path, template_path=template)
            click.echo(f"PDF : {pdf_path}")
        except (ImportError, OSError) as exc:
            if "libgobject" in str(exc) or "GTK" in str(exc) or isinstance(exc, ImportError):
                click.echo(
                    "WeasyPrint requires GTK libraries which are not installed on this system. "
                    "PDF output skipped. See https://doc.courtbouillon.org/weasyprint/stable/first_steps.html",
                    err=True,
                )
            else:
                click.echo(f"Error generating PDF: {exc}", err=True)
                sys.exit(1)
        except Exception as exc:
            click.echo(f"Error generating PDF: {exc}", err=True)
            sys.exit(1)

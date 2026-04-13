"""renderer.py — Jinja2 HTML rendering and WeasyPrint PDF export."""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .collector import ReportData

_TEMPLATES_DIR = Path(__file__).parent / "templates"


# ── Custom Jinja2 filters ─────────────────────────────────────────────────────

def _filter_thousands(value, decimals: int = 0) -> str:
    """Format a number with narrow no-break space as thousands separator."""
    if value is None:
        return "\u2014"
    try:
        n = float(value)
        if decimals == 0:
            formatted = f"{round(n):,}".replace(",", "\u202f")
        else:
            formatted = f"{n:,.{decimals}f}".replace(",", "\u202f")
        return formatted
    except (TypeError, ValueError):
        return str(value)


def _filter_fmt1(value) -> str:
    """Format a number to 1 decimal place, or '—' if None."""
    if value is None:
        return "\u2014"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def _filter_ugr_fmt(value) -> str:
    """Format a UGR value to 1 decimal place, or '—' if None."""
    if value is None:
        return "\u2014"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def _filter_lum_fmt(value) -> str:
    """Format a luminance value (cd/m²): integer up to 99 999, scientific above.

    Examples: 1234 → '1234', 12345 → '12345', 123456 → '1.23e5'.
    """
    if value is None:
        return "\u2014"
    try:
        n = int(round(float(value)))
        if n < 100_000:
            return str(n)
        mantissa, exp = f"{n:.2e}".split("e")
        return f"{mantissa}e{int(exp)}"
    except (TypeError, ValueError):
        return str(value)


def _filter_svg_responsive(svg_str: str) -> str:
    """Add viewBox from width/height attributes, set width=100%, remove fixed height.

    Makes an SVG with fixed pixel dimensions responsive inside a flex container.
    If the SVG already has a percentage width, it is returned unchanged.
    If width/height attributes are absent, the SVG is returned unchanged.
    """
    if not svg_str:
        return svg_str

    # Match the opening <svg ...> tag (attributes only, no child elements)
    m_tag = re.search(r"<svg(\s[^>]*)?>", svg_str, re.DOTALL)
    if not m_tag:
        return svg_str

    attrs = m_tag.group(1) or ""

    m_w = re.search(r'\bwidth="([^"]*)"', attrs)
    m_h = re.search(r'\bheight="([^"]*)"', attrs)
    if not m_w or not m_h:
        return svg_str

    w_val = m_w.group(1)
    h_val = m_h.group(1)

    # Already responsive
    if "%" in w_val:
        return svg_str

    new_attrs = attrs

    # Add viewBox if absent
    if "viewBox" not in new_attrs:
        new_attrs = f' viewBox="0 0 {w_val} {h_val}"' + new_attrs

    # Replace width with 100%
    new_attrs = re.sub(r'\bwidth="[^"]*"', 'width="100%"', new_attrs)

    # Remove height
    new_attrs = re.sub(r'\s*\bheight="[^"]*"', "", new_attrs)

    return svg_str[: m_tag.start()] + f"<svg{new_attrs}>" + svg_str[m_tag.end() :]


# ── Renderer ──────────────────────────────────────────────────────────────────

class ReportRenderer:
    """Render a ReportData object to HTML (and optionally PDF)."""

    @classmethod
    def render_html(
        cls,
        data: ReportData,
        template_path: Path | None = None,
        show_lum_table: bool = False,
    ) -> str:
        """Return the rendered HTML as a string."""
        env = cls._make_env(template_path)
        template_name = template_path.name if template_path else "default.html"
        tmpl = env.get_template(template_name)
        return tmpl.render(data=data, show_lum_table=show_lum_table)

    @classmethod
    def render_pdf(
        cls,
        data: ReportData,
        output_path: Path,
        template_path: Path | None = None,
        show_lum_table: bool = False,
    ) -> None:
        """Write a PDF to *output_path* via Playwright (Chromium headless)."""
        from playwright.sync_api import sync_playwright  # lazy import

        html_str = cls.render_html(data, template_path, show_lum_table=show_lum_table)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_str, wait_until="networkidle")
            page.add_style_tag(content=(
                "@page { margin: 12mm 14mm !important; }"
                " body { background: white !important; padding: 0 !important; display: block !important; }"
                " .a4-page { box-shadow: none !important; padding: 0 !important; }"
            ))
            page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()

    @classmethod
    def render_ugr_image(
        cls,
        data: ReportData,
        width_cm: float = 17.0,
        dpi: int = 150,
    ) -> bytes:
        """Render the UGR section as a PNG image (bytes) via Playwright element screenshot.

        Parameters
        ----------
        data : ReportData
            Collected photometric data.
        width_cm : float
            Target image width in centimetres (default 17 cm).
        dpi : int
            Output resolution in dots per inch (default 150).
        """
        from playwright.sync_api import sync_playwright  # lazy import

        viewport_width = int(width_cm / 2.54 * 96)
        device_scale_factor = dpi / 96

        tmpl_path = _TEMPLATES_DIR / "ugr_image.html"
        env = cls._make_env(tmpl_path)
        html_str = env.get_template("ugr_image.html").render(data=data)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": viewport_width, "height": 3000},
                device_scale_factor=device_scale_factor,
            )
            page.set_content(html_str, wait_until="networkidle")
            png = page.locator(".ugr-image-wrapper").screenshot()
            browser.close()
        return png

    @classmethod
    def render_luminance_image(
        cls,
        data: ReportData,
        width_cm: float = 17.0,
        dpi: int = 150,
    ) -> bytes:
        """Render the luminance table as a PNG image (bytes) via Playwright element screenshot.

        Parameters
        ----------
        data : ReportData
            Collected photometric data (must have lum_table populated).
        width_cm : float
            Target image width in centimetres (default 17 cm).
        dpi : int
            Output resolution in dots per inch (default 150).
        """
        from playwright.sync_api import sync_playwright  # lazy import

        viewport_width = int(width_cm / 2.54 * 96)
        device_scale_factor = dpi / 96

        tmpl_path = _TEMPLATES_DIR / "luminance_image.html"
        env = cls._make_env(tmpl_path)
        html_str = env.get_template("luminance_image.html").render(data=data)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": viewport_width, "height": 3000},
                device_scale_factor=device_scale_factor,
            )
            page.set_content(html_str, wait_until="networkidle")
            png = page.locator(".lum-image-wrapper").screenshot()
            browser.close()
        return png

    @classmethod
    def _make_env(cls, template_path: Path | None) -> Environment:
        tmpl_dir = template_path.parent if template_path else _TEMPLATES_DIR
        env = Environment(
            loader=FileSystemLoader(str(tmpl_dir)),
            autoescape=True,
        )
        env.filters["thousands"]      = _filter_thousands
        env.filters["fmt1"]           = _filter_fmt1
        env.filters["ugr_fmt"]        = _filter_ugr_fmt
        env.filters["lum_fmt"]        = _filter_lum_fmt
        env.filters["svg_responsive"] = _filter_svg_responsive
        return env

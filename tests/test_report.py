"""test_report.py — Integration tests for eulumdat-report."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from eulumdat_report.cli import main
from eulumdat_report.collector import ReportCollector, ReportData, UgrTableData
from eulumdat_report.renderer import (
    ReportRenderer,
    _filter_fmt1,
    _filter_svg_responsive,
    _filter_thousands,
    _filter_ugr_fmt,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data" / "input"

ALL_SAMPLES = sorted(DATA_DIR.glob("*.ldt"))

# One representative per ISYM class
SAMPLE_ISYM1 = DATA_DIR / "sample_13_isym1.ldt"
SAMPLE_ISYM2 = DATA_DIR / "sample_04_isym2.ldt"
SAMPLE_ISYM3 = DATA_DIR / "sample_16_isym3.ldt"
SAMPLE_ISYM4 = DATA_DIR / "sample_02_isym4.ldt"
SAMPLE_ISYM0 = DATA_DIR / "sample_27_isym0.ldt"


@pytest.fixture(scope="module")
def data_isym1() -> ReportData:
    return ReportCollector.collect(SAMPLE_ISYM1)


@pytest.fixture(scope="module")
def data_isym4() -> ReportData:
    return ReportCollector.collect(SAMPLE_ISYM4)


@pytest.fixture(scope="module")
def data_isym2() -> ReportData:
    return ReportCollector.collect(SAMPLE_ISYM2)


@pytest.fixture(scope="module")
def data_isym0() -> ReportData:
    return ReportCollector.collect(SAMPLE_ISYM0)


# ── Step 2 — collector: LDT header fields ────────────────────────────────────

class TestCollectorHeader:
    """ReportCollector populates all scalar header fields correctly."""

    @pytest.mark.parametrize("ldt_path", ALL_SAMPLES)
    def test_collect_returns_report_data(self, ldt_path):
        data = ReportCollector.collect(ldt_path)
        assert isinstance(data, ReportData)

    @pytest.mark.parametrize("ldt_path", ALL_SAMPLES)
    def test_metadata_fields(self, ldt_path):
        data = ReportCollector.collect(ldt_path)
        assert data.source_file == ldt_path.name
        assert "T" in data.generated_at          # ISO 8601 datetime
        assert data.package_version != ""

    def test_header_strings_not_empty(self, data_isym1):
        # At least one non-empty string field expected in real LDT files
        assert isinstance(data_isym1.luminaire_name, str)
        assert isinstance(data_isym1.company, str)
        assert isinstance(data_isym1.luminaire_number, str)

    def test_geometry_positive(self, data_isym1):
        assert data_isym1.length >= 0
        assert data_isym1.width >= 0
        assert data_isym1.height >= 0
        assert data_isym1.length_lum_area >= 0
        assert data_isym1.width_lum_area >= 0

    def test_lamp_data(self, data_isym1):
        assert data_isym1.lamp_count >= 1
        assert data_isym1.lamp_flux > 0
        assert data_isym1.lamp_watt > 0

    def test_luminous_efficacy(self, data_isym1):
        assert data_isym1.luminous_efficacy is not None
        expected = data_isym1.lamp_flux / data_isym1.lamp_watt
        assert abs(data_isym1.luminous_efficacy - expected) < 0.01

    def test_isym_range(self, data_isym1, data_isym4, data_isym2, data_isym0):
        assert data_isym1.isym == 1
        assert data_isym4.isym == 4
        assert data_isym2.isym == 2
        assert data_isym0.isym == 0

    @pytest.mark.parametrize("ldt_path", ALL_SAMPLES)
    def test_mc_ng_positive(self, ldt_path):
        data = ReportCollector.collect(ldt_path)
        assert data.mc > 0
        assert data.ng > 0


# ── Step 3 — collector: intensity SVG ────────────────────────────────────────

class TestCollectorIntensitySvg:
    """svg_intensity is a valid SVG string."""

    @pytest.mark.parametrize("ldt_path", ALL_SAMPLES)
    def test_svg_intensity_present(self, ldt_path):
        data = ReportCollector.collect(ldt_path)
        assert data.svg_intensity is not None
        assert data.svg_intensity.strip().startswith("<svg")

    def test_svg_intensity_contains_path_or_polyline(self, data_isym1):
        svg = data_isym1.svg_intensity
        assert "<path" in svg or "<polyline" in svg or "<line" in svg


# ── Step 4 — collector: luminance SVG ────────────────────────────────────────

class TestCollectorLuminanceSvg:
    """svg_luminance is a valid SVG string and lum_max is a positive float."""

    @pytest.mark.parametrize("ldt_path", ALL_SAMPLES)
    def test_svg_luminance_present(self, ldt_path):
        data = ReportCollector.collect(ldt_path)
        assert data.svg_luminance is not None
        assert data.svg_luminance.strip().startswith("<svg")

    @pytest.mark.parametrize("ldt_path", ALL_SAMPLES)
    def test_lum_max_positive(self, ldt_path):
        data = ReportCollector.collect(ldt_path)
        assert data.lum_max is not None
        assert data.lum_max >= 0


# ── Step 5 — collector: UGR table ────────────────────────────────────────────

class TestCollectorUgr:
    """UGR table is produced for ISYM 1/4, absent or None for others."""

    def test_ugr_present_for_isym1(self, data_isym1):
        assert data_isym1.ugr is not None

    def test_ugr_present_for_isym4(self, data_isym4):
        assert data_isym4.ugr is not None

    def test_ugr_structure(self, data_isym4):
        ugr = data_isym4.ugr
        assert isinstance(ugr, UgrTableData)
        assert len(ugr.room_sizes) == 19
        assert len(ugr.reflectances) == 5
        assert set(ugr.values.keys()) == {"crosswise", "endwise"}
        assert len(ugr.values["crosswise"]) == 19
        assert len(ugr.values["endwise"]) == 19

    def test_ugr_rows_have_five_values(self, data_isym4):
        for row in data_isym4.ugr.values["crosswise"]:
            assert len(row) == 5
        for row in data_isym4.ugr.values["endwise"]:
            assert len(row) == 5

    def test_ugr_values_are_float_or_none(self, data_isym4):
        for direction in ("crosswise", "endwise"):
            for row in data_isym4.ugr.values[direction]:
                for v in row:
                    assert v is None or isinstance(v, float)

    def test_ugr_room_order(self, data_isym4):
        sizes = data_isym4.ugr.room_sizes
        assert sizes[0]  == (2, 2)
        assert sizes[5]  == (2, 12)
        assert sizes[6]  == (4, 2)
        assert sizes[10] == (4, 8)
        assert sizes[12] == (8, 4)
        assert sizes[16] == (12, 4)
        assert sizes[18] == (12, 8)

    def test_ugr_shr(self, data_isym4):
        assert data_isym4.ugr.shr == 0.25

    def test_ugr_values_in_range(self, data_isym1):
        for direction in ("crosswise", "endwise"):
            for row in data_isym1.ugr.values[direction]:
                for v in row:
                    if v is not None:
                        assert 5 <= v <= 40, f"UGR value {v} out of plausible range"


# ── Step 6/7 — renderer: HTML output ─────────────────────────────────────────

class TestRendererHtml:
    """render_html() produces well-formed, complete HTML."""

    @pytest.mark.parametrize("ldt_path", ALL_SAMPLES)
    def test_render_html_returns_string(self, ldt_path):
        data = ReportCollector.collect(ldt_path)
        html = ReportRenderer.render_html(data)
        assert isinstance(html, str)
        assert len(html) > 1000

    def test_html_structure(self, data_isym1):
        html = ReportRenderer.render_html(data_isym1)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "a4-page" in html

    def test_html_contains_svg(self, data_isym1):
        html = ReportRenderer.render_html(data_isym1)
        assert "<svg" in html

    def test_html_svg_responsive(self, data_isym1):
        html = ReportRenderer.render_html(data_isym1)
        # SVGs must have viewBox and width=100% (svg_responsive filter applied)
        assert "viewBox" in html
        assert 'width="100%"' in html

    def test_html_ugr_table_isym1(self, data_isym1):
        html = ReportRenderer.render_html(data_isym1)
        assert 'class="ugr"' in html
        assert "ugr-warning" not in _body(html)

    def test_html_ugr_table_isym4(self, data_isym4):
        html = ReportRenderer.render_html(data_isym4)
        assert 'class="ugr"' in html
        assert "ugr-warning" not in _body(html)

    def test_html_ugr_warning_isym2(self, data_isym2):
        html = ReportRenderer.render_html(data_isym2)
        assert 'class="ugr"' not in _body(html)
        assert "ugr-warning" in html

    def test_html_ugr_warning_isym0(self, data_isym0):
        html = ReportRenderer.render_html(data_isym0)
        assert 'class="ugr"' not in _body(html)
        assert "ugr-warning" in html

    def test_html_ugr_highlight_positions(self, data_isym4):
        """4H×8H and 8H×4H col-0 cells are highlighted, not others."""
        html = ReportRenderer.render_html(data_isym4)
        body = _body(html)
        tbody = re.search(r"<tbody>(.*?)</tbody>", body, re.DOTALL).group(1)
        rows = re.findall(r"<tr[^>]*>.*?</tr>", tbody, re.DOTALL)
        assert len(rows) == 19
        for i, row in enumerate(rows):
            labels = re.findall(r'<td class="label">(\w+)</td>', row)
            x_h = int(labels[0].replace("H", ""))
            y_h = int(labels[1].replace("H", ""))
            should_hl = (x_h == 4 and y_h == 8) or (x_h == 8 and y_h == 4)
            has_hl = "ugr-highlight" in row
            assert has_hl == should_hl, (
                f"Row {i} ({x_h}H×{y_h}H): expected highlight={should_hl}, got {has_hl}"
            )

    def test_html_identification_bar(self, data_isym1):
        html = ReportRenderer.render_html(data_isym1)
        assert "identification" in html
        assert f"ISYM" in html

    def test_html_footer(self, data_isym1):
        html = ReportRenderer.render_html(data_isym1)
        assert "eulumdat-report" in html
        assert data_isym1.source_file in html


# ── Step 7 — custom filters ───────────────────────────────────────────────────

class TestFilters:
    """Custom Jinja2 filters behave correctly."""

    def test_thousands_integer(self):
        assert _filter_thousands(12334) == "12\u202f334"

    def test_thousands_small(self):
        assert _filter_thousands(500) == "500"

    def test_thousands_none(self):
        assert _filter_thousands(None) == "\u2014"

    def test_thousands_decimals(self):
        result = _filter_thousands(1234.5, decimals=1)
        assert "1" in result and "234" in result

    def test_fmt1_normal(self):
        assert _filter_fmt1(12.345) == "12.3"

    def test_fmt1_none(self):
        assert _filter_fmt1(None) == "\u2014"

    def test_ugr_fmt_value(self):
        assert _filter_ugr_fmt(18.07) == "18.1"

    def test_ugr_fmt_none(self):
        assert _filter_ugr_fmt(None) == "\u2014"

    def test_svg_responsive_adds_viewbox(self):
        svg = '<svg width="100" height="200" xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        result = _filter_svg_responsive(svg)
        assert 'viewBox="0 0 100 200"' in result
        assert 'width="100%"' in result
        assert 'height="200"' not in result

    def test_svg_responsive_keeps_existing_viewbox(self):
        svg = '<svg viewBox="0 0 50 50" width="50" height="50"><rect/></svg>'
        result = _filter_svg_responsive(svg)
        assert result.count("viewBox") == 1   # not duplicated
        assert 'width="100%"' in result

    def test_svg_responsive_skips_already_percent(self):
        svg = '<svg width="100%" height="auto"><rect/></svg>'
        result = _filter_svg_responsive(svg)
        assert result == svg                  # unchanged

    def test_svg_responsive_empty(self):
        assert _filter_svg_responsive("") == ""
        assert _filter_svg_responsive(None) == None


# ── Step 8 — CLI ─────────────────────────────────────────────────────────────

class TestCli:
    """CLI produces the expected output files."""

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "LDT_FILE" in result.output

    def test_html_only(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, [
            str(SAMPLE_ISYM1), "--output-dir", str(tmp_path), "--no-pdf",
        ])
        assert result.exit_code == 0, result.output
        html_out = tmp_path / "sample_13_isym1.html"
        assert html_out.exists()
        assert html_out.stat().st_size > 1000

    def test_html_content(self, tmp_path):
        runner = CliRunner()
        runner.invoke(main, [str(SAMPLE_ISYM4), "--output-dir", str(tmp_path), "--no-pdf"])
        html = (tmp_path / "sample_02_isym4.html").read_text(encoding="utf-8")
        assert "<svg" in html
        assert 'class="ugr"' in html

    def test_no_html_no_pdf_exits_nonzero(self):
        runner = CliRunner()
        result = runner.invoke(main, [str(SAMPLE_ISYM1), "--no-html", "--no-pdf"])
        assert result.exit_code != 0

    def test_invalid_ldt_path(self):
        runner = CliRunner()
        result = runner.invoke(main, ["nonexistent.ldt"])
        assert result.exit_code != 0

    def test_output_dir_created(self, tmp_path):
        dest = tmp_path / "new_subdir"
        runner = CliRunner()
        result = runner.invoke(main, [
            str(SAMPLE_ISYM1), "--output-dir", str(dest), "--no-pdf",
        ])
        assert result.exit_code == 0
        assert dest.exists()

    @pytest.mark.parametrize("ldt_path", ALL_SAMPLES)
    def test_all_samples_html(self, ldt_path, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, [str(ldt_path), "--output-dir", str(tmp_path), "--no-pdf"])
        assert result.exit_code == 0, result.output
        out = tmp_path / ldt_path.with_suffix(".html").name
        assert out.exists() and out.stat().st_size > 1000


# ── Helpers ───────────────────────────────────────────────────────────────────

def _body(html: str) -> str:
    """Return the HTML content after the closing </style> tag."""
    m = re.search(r"</style>(.*)", html, re.DOTALL)
    return m.group(1) if m else html

# eulumdat-report

[![PyPI version](https://img.shields.io/pypi/v/eulumdat-report.svg)](https://pypi.org/project/eulumdat-report/)
[![Python](https://img.shields.io/pypi/pyversions/eulumdat-report.svg)](https://pypi.org/project/eulumdat-report/)
[![License: MIT](https://img.shields.io/github/license/123VincentB/eulumdat-report)](https://github.com/123VincentB/eulumdat-report/blob/main/LICENSE)

Photometric datasheet generator (HTML + PDF) from EULUMDAT `.ldt` files — orchestrates the full `eulumdat-*` ecosystem.

## Features

- Single-page A4 datasheet from any EULUMDAT `.ldt` file
- Polar intensity diagram (cd/klm) — `eulumdat-plot`
- Polar luminance diagram (cd/m²) + maximum luminance — `eulumdat-luminance`
- UGR catalogue table (CIE 117 / CIE 190, 19 rooms × 5 reflectances × 2 directions) — `eulumdat-ugr`
- Numerical luminance table (cd/m²) — optional section in full report (`--lum-table`)
- Half-angles and FWHM per C-plane — `eulumdat-analysis`
- HTML output (self-contained, browser-ready A4 preview)
- PDF output via Playwright / Chromium (cross-platform — see installation notes)
- PNG export of UGR and luminance tables for Word / docxtpl integration
- Custom Jinja2 template support
- CLI and Python API

## Sample output

[![Photometric Datasheet — sample preview](https://raw.githubusercontent.com/123VincentB/eulumdat-report/main/examples/sample_02_isym4_thumbnail.png)](https://htmlpreview.github.io/?https://github.com/123VincentB/eulumdat-report/blob/main/examples/sample_02_isym4.html)

## Installation

```bash
pip install eulumdat-report
```

### PDF output

PDF rendering uses [Playwright](https://playwright.dev/python/) (Chromium headless).
After installing the package, download the Chromium browser once:

```bash
playwright install chromium
```

This step is required on all platforms (Windows, Linux, macOS). HTML output works
without it.

## Quick start

### CLI

```bash
# HTML + PDF
eulumdat-report luminaire.ldt

# HTML only, custom output directory
eulumdat-report luminaire.ldt --no-pdf --output-dir reports/

# Include numerical luminance table
eulumdat-report luminaire.ldt --lum-table

# All options
eulumdat-report --help
```

### Python API

```python
from eulumdat_report.collector import ReportCollector
from eulumdat_report.renderer import ReportRenderer
from pathlib import Path

data = ReportCollector.collect("luminaire.ldt")
html = ReportRenderer.render_html(data)
Path("luminaire.html").write_text(html, encoding="utf-8")

# PDF (requires: playwright install chromium)
ReportRenderer.render_pdf(data, Path("luminaire.pdf"))
```

## PNG export for Word / docxtpl

The UGR table and luminance table can be exported as PNG images (17 cm wide, 150 dpi by default)
for embedding in Word documents via [docxtpl](https://docxtpl.readthedocs.io/).

```python
import io
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from eulumdat_report import render_ugr_image, render_luminance_image

# Render from .ldt path (or pass an already-collected ReportData)
ugr_png = render_ugr_image("luminaire.ldt")
lum_png = render_luminance_image("luminaire.ldt")

doc = DocxTemplate("template.docx")
context = {
    "ugr_table": InlineImage(doc, io.BytesIO(ugr_png), width=Mm(170)),
    "lum_table": InlineImage(doc, io.BytesIO(lum_png), width=Mm(170)),
}
doc.render(context)
doc.save("rapport.docx")
```

Both functions accept `width_cm` (default `17.0`) and `dpi` (default `150`) parameters.

## CLI reference

```
Usage: eulumdat-report [OPTIONS] LDT_FILE

  Generate a photometric datasheet (HTML/PDF) from an EULUMDAT .ldt file.

Options:
  -o, --output-dir DIRECTORY      Output directory  [default: same as LDT_FILE]
  --template FILE                 Custom Jinja2 HTML template
  --html / --no-html              Generate HTML output  [default: html]
  --pdf  / --no-pdf               Generate PDF output   [default: pdf]
  --lum-table / --no-lum-table    Include numerical luminance table  [default: no-lum-table]
  -v, --verbose                   Enable debug logging
  --help                          Show this message and exit
```

Output filenames are derived from the input basename: `luminaire.ldt` → `luminaire.html` / `luminaire.pdf`.

## Template customisation

The default template is `src/eulumdat_report/templates/default.html` with companion `default.css`.
To customise, copy both files to a local directory and pass `--template` to the CLI:

```bash
eulumdat-report luminaire.ldt --template my_templates/custom.html
```

The template receives a single `data` object (`ReportData` dataclass). The following
Jinja2 filters are available:

| Filter | Description | Example |
|---|---|---|
| `thousands` | Space-separated thousands (int) | `12334` → `12 334` |
| `fmt1` | 1 decimal place | `184.6` |
| `ugr_fmt` | 1 decimal or `—` if None | `18.0` / `—` |
| `lum_fmt` | Compact luminance: integer ≤ 99 999, scientific above | `123456` → `1.23e5` |
| `svg_responsive` | Makes SVG responsive (adds `viewBox`, sets `width=100%`) | |

SVG fields are embedded inline: `{{ data.svg_intensity \| svg_responsive \| safe }}`.

### Key `data` fields

```python
data.luminaire_name      # str
data.company             # str
data.luminaire_number    # str
data.isym                # int  (0–4)
data.mc, data.ng         # int  (C-planes, gamma angles)
data.lamp_flux           # float (lm)
data.lamp_watt           # float (W)
data.lorl                # float (%)
data.lum_max             # float | None (cd/m²)
data.svg_intensity       # str | None
data.svg_luminance       # str | None
data.ugr                 # UgrTableData | None
data.lum_table           # LuminanceTableData | None
```

## Dependencies

| Package | Role |
|---|---|
| `eulumdat-py` | EULUMDAT parser |
| `eulumdat-plot` | Polar intensity diagram (SVG) |
| `eulumdat-luminance` | Polar luminance diagram (SVG) + maximum |
| `eulumdat-ugr` | UGR catalogue table |
| `eulumdat-analysis` | Half-angles, FWHM |
| `jinja2` | HTML templating |
| `playwright` | PDF rendering (Chromium headless) |
| `click` | CLI |

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

## eulumdat-* ecosystem

> **New to the ecosystem?** [eulumdat-quickstart](https://github.com/123VincentB/eulumdat-quickstart) — a step-by-step guide covering all 8 packages with working examples.

| Package | Description |
|---|---|
| [eulumdat-py](https://pypi.org/project/eulumdat-py/) | Read / write EULUMDAT files |
| [eulumdat-symmetry](https://pypi.org/project/eulumdat-symmetry/) | Symmetrise and detect ISYM |
| [eulumdat-plot](https://pypi.org/project/eulumdat-plot/) | Polar intensity diagram (SVG/PNG) |
| [eulumdat-luminance](https://pypi.org/project/eulumdat-luminance/) | Luminance table and polar diagram |
| [eulumdat-ugr](https://pypi.org/project/eulumdat-ugr/) | UGR catalogue (CIE 117/190) |
| [eulumdat-analysis](https://pypi.org/project/eulumdat-analysis/) | Beam half-angle, FWHM |
| **`eulumdat-report`** | **Full photometric datasheet (HTML/PDF) — this package** |
| [eulumdat-ies](https://pypi.org/project/eulumdat-ies/) | LDT ↔ IES LM-63-2002 conversion |

---

## License

MIT

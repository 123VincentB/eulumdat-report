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
- Half-angles and FWHM per C-plane — `eulumdat-analysis`
- HTML output (self-contained, browser-ready A4 preview)
- PDF output via Playwright / Chromium (cross-platform — see installation notes)
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

## CLI reference

```
Usage: eulumdat-report [OPTIONS] LDT_FILE

  Generate a photometric datasheet (HTML/PDF) from an EULUMDAT .ldt file.

Options:
  -o, --output-dir DIRECTORY  Output directory  [default: same as LDT_FILE]
  --template FILE             Custom Jinja2 HTML template
  --html / --no-html          Generate HTML output  [default: html]
  --pdf  / --no-pdf           Generate PDF output   [default: pdf]
  -v, --verbose               Enable debug logging
  --help                      Show this message and exit
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

## License

MIT

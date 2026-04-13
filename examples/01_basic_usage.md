# Basic usage — eulumdat-report

[![Photometric Datasheet — sample preview](https://raw.githubusercontent.com/123VincentB/eulumdat-report/main/examples/sample_02_isym4_thumbnail.png)](https://htmlpreview.github.io/?https://github.com/123VincentB/eulumdat-report/blob/main/examples/sample_02_isym4.html)


## CLI

```bash
# Generate HTML + PDF in the same directory as the .ldt file
eulumdat-report luminaire.ldt

# Specify output directory
eulumdat-report luminaire.ldt --output-dir reports/

# HTML only (no Chromium required)
eulumdat-report luminaire.ldt --no-pdf --output-dir reports/

# PDF only
eulumdat-report luminaire.ldt --no-html --output-dir reports/

# Custom template
eulumdat-report luminaire.ldt --template my_templates/report.html --no-pdf
```

## Python API

```python
from pathlib import Path
from eulumdat_report.collector import ReportCollector
from eulumdat_report.renderer import ReportRenderer

# Collect all data from the .ldt file
data = ReportCollector.collect("luminaire.ldt")

# Inspect collected data
print(data.luminaire_name)          # luminaire description
print(f"{data.lamp_flux:.0f} lm")  # total luminous flux
print(f"{data.lum_max:.0f} cd/m²") # peak luminance

# Render to HTML (self-contained, browser-ready)
html = ReportRenderer.render_html(data)
Path("luminaire.html").write_text(html, encoding="utf-8")

# Render to PDF (requires: playwright install chromium)
ReportRenderer.render_pdf(data, Path("luminaire.pdf"))

# Custom template
from pathlib import Path
template = Path("my_templates/report.html")
html = ReportRenderer.render_html(data, template_path=template)
```

## Accessing UGR data

```python
data = ReportCollector.collect("luminaire.ldt")

if data.ugr is not None:
    # 19 room configurations × 5 reflectance combinations
    for i, room in enumerate(data.ugr.room_sizes):
        x_h, y_h = room
        cw = data.ugr.values["crosswise"][i]   # list of 5 floats (or None)
        ew = data.ugr.values["endwise"][i]      # list of 5 floats (or None)
        print(f"{x_h}H × {y_h}H  crosswise={cw[0]:.1f}  endwise={ew[0]:.1f}")
```

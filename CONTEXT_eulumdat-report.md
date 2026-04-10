# CONTEXT — eulumdat-report

> Source of truth for Claude Code. Read this before touching any file.
> Last updated: 2026-04-10

---

## 1. Purpose

`eulumdat-report` generates a photometric datasheet (HTML and PDF) from an EULUMDAT `.ldt` file.
It orchestrates the entire `eulumdat-*` ecosystem and renders a structured report via a Jinja2 HTML
template, converted to PDF by WeasyPrint.

The package is not a GUI tool. It is a CLI and Python API for technical users (lighting engineers,
architects) who may customise the HTML/CSS template with AI assistance.

**Statut** : v1.0.0, complet — wheel buildé, en attente de publication PyPI et création du dépôt GitHub.

---

## 2. Ecosystem dependencies

| Package               | PyPI name            | Import               | Version | Role                                        |
|-----------------------|----------------------|----------------------|---------|---------------------------------------------|
| `eulumdat-py`         | `eulumdat-py`        | `pyldt`              | 1.0.0   | LDT parser — source of all photometric data |
| `eulumdat-analysis`   | `eulumdat-analysis`  | `ldt_analysis`       | —       | Half-angles and FWHM per C-plane            |
| `eulumdat-plot`       | `eulumdat-plot`      | `eulumdat_plot`      | 1.0.3   | SVG polar intensity diagram (string API)    |
| `eulumdat-luminance`  | `eulumdat-luminance` | `eulumdat_luminance` | 1.3.1   | Luminance table + SVG polar diagram         |
| `eulumdat-ugr`        | `eulumdat-ugr`       | `eulumdat_ugr`       | 1.0.2   | UGR catalogue table (19 standard rooms)     |

### Key API calls used in collector.py

```python
# eulumdat-plot v1.0.3
from eulumdat_plot import plot_ldt_svg
svg_str = plot_ldt_svg(ldt_path, interpolate=True, interp_method="linear")  # → str

# eulumdat-luminance v1.3.1
from eulumdat_luminance import LuminanceCalculator, LuminancePlot
result = LuminanceCalculator.compute(ldt, full=False)
lum_max = result.maximum                    # float, cd/m²
svg_str = LuminancePlot(result).polar_svg() # → str (inline embedding)

# eulumdat-ugr v1.0.2
from eulumdat_ugr import UgrCalculator
result = UgrCalculator.compute(ldt)
v = result.values   # np.ndarray (19, 10) — columns 0:5 crosswise, 5:10 endwise

# eulumdat-analysis
from ldt_analysis import half_angle
half_angles = half_angle(ldt, [0.0, 90.0, 180.0, 270.0])  # → dict[float, float|None]
```

---

## 3. Architecture

```
eulumdat-report/
├── data/
│   ├── input/              # 10 sample .ldt files (ISYM 0–4, anonymised)
│   └── output/             # Generated reports (gitignored)
├── docs/
│   └── report_mockup.html  # Reference visual mockup
├── examples/
│   └── 01_basic_usage.md
├── src/
│   └── eulumdat_report/
│       ├── __init__.py          # __version__ = "1.0.0"
│       ├── cli.py               # Click CLI entry point
│       ├── collector.py         # ReportCollector, ReportData, UgrTableData
│       ├── renderer.py          # ReportRenderer, custom Jinja2 filters
│       └── templates/
│           ├── default.html     # Jinja2 template (CSS inlined via {% include %})
│           └── default.css      # A4 stylesheet
├── tests/
│   └── test_report.py           # 122 tests, all passing
├── .gitignore
├── CLAUDE.md
├── CONTEXT_eulumdat-report.md
├── LICENSE                      # MIT
├── pyproject.toml
└── README.md
```

---

## 4. Module responsibilities

### 4.1 `collector.py`

`ReportCollector.collect(ldt_path) → ReportData` — collecte toutes les données
en appelant les packages de l'écosystème. Chaque package est importé de façon
lazy avec gestion gracieuse des erreurs (`try/except`, log warning, champ → None).

```python
@dataclass
class UgrTableData:
    room_sizes: list[tuple[int, int]]          # 19 configs (X_div_H, Y_div_H)
    reflectances: list[tuple[int, int, int]]   # 5 combos (ceiling, wall, floor)
    values: dict[str, list[list[float|None]]]  # "crosswise" et "endwise"
    shr: float                                 # = 0.25

@dataclass
class ReportData:
    # Métadonnées
    source_file: str; generated_at: str; package_version: str
    # En-tête LDT
    company: str; luminaire_name: str; luminaire_number: str; date_user: str
    length: float; width: float; height: float
    length_lum_area: float; width_lum_area: float
    h_lum_c0: float; h_lum_c90: float; h_lum_c180: float; h_lum_c270: float
    lamp_count: int; lamp_name: str; lamp_flux: float; lamp_watt: float
    lorl: float; dff: float; isym: int; mc: int; ng: int
    # Champs calculés
    luminous_efficacy: float | None
    half_angles: dict[float, float|None] | None    # clés : 0.0, 90.0, 180.0, 270.0
    fwhm: dict[str, float|None] | None             # clés : "C0_C180", "C90_C270"
    lum_max: float | None
    # SVG (embedding inline)
    svg_intensity: str | None
    svg_luminance: str | None
    # Table UGR
    ugr: UgrTableData | None
```

**Ordre fixe des 19 configurations UGR** :
```
X=2H : Y = 2H, 3H, 4H, 6H, 8H, 12H   → indices 0–5
X=4H : Y = 2H, 3H, 4H, 6H, 8H, 12H   → indices 6–11
X=8H : Y = 4H, 6H, 8H, 12H            → indices 12–15
X=12H: Y = 4H, 6H, 8H                 → indices 16–18
```

**Ordre fixe des 5 réflectances** :
`(70,50,20)`, `(70,30,20)`, `(50,50,20)`, `(50,30,20)`, `(30,30,20)`

### 4.2 `renderer.py`

`ReportRenderer` — rendu Jinja2 + export PDF WeasyPrint.

```python
ReportRenderer.render_html(data, template_path=None) -> str
ReportRenderer.render_pdf(data, output_path, template_path=None) -> None
```

**Filtres Jinja2 personnalisés** :

| Filtre | Fonction | Exemple |
|---|---|---|
| `thousands` | Séparateur milliers espace fine (`\u202f`) | `12334` → `"12 334"` |
| `fmt1` | 1 décimale ou `—` si None | `184.6` → `"184.6"` |
| `ugr_fmt` | 1 décimale ou `—` si None | `None` → `"—"` |
| `svg_responsive` | Ajoute `viewBox`, passe `width="100%"`, supprime `height` | |

**`svg_responsive`** : nécessaire car `eulumdat-plot` génère des SVG avec
`width="1181" height="1181"` sans `viewBox`. Le filtre rend le SVG responsive
dans le conteneur flex du template.

**WeasyPrint** : import lazy dans `render_pdf()`. Sur Windows sans GTK,
lève `OSError` ("cannot load library 'libgobject-2.0-0'"). Intercepté dans
le CLI avec message informatif (exit 0, HTML toujours généré).

### 4.3 `templates/default.html` + `default.css`

Le CSS est inliné dans le HTML via `{% include 'default.css' %}` — le fichier
HTML généré est auto-contenu (navigateur + WeasyPrint sans chemin relatif).

**Sections du template** (dans l'ordre) :
1. Report header (titre, métadonnées source/date/version)
2. Identification bar (fond bleu foncé : nom, fabricant, catalogue, date/user, grille angulaire)
3. Two-column grid : Geometry card + Lamp data card
4. Diagrams row : Polar Intensity + Polar Luminance (côte à côte)
5. UGR section (conditionnel)
6. Footer

**Règle d'affichage UGR** :
```jinja2
{% if data.isym in (1, 4) and data.ugr %}
  {# tableau complet #}
{% else %}
  {# warning "not applicable" #}
{% endif %}
```

**Cellules ugr-highlight** (fond jaune `#fffbcc`) :
- Rooms 4H×8H (index 10) et 8H×4H (index 12) — colonne 0 de crosswise ET endwise
- Condition : `{% set is_hl_room = (x_h == 4 and y_h == 8) or (x_h == 8 and y_h == 4) %}`

**Séparateurs de lignes UGR** (`row-sep`) :
- Indices 0, 6, 12, 16 (première ligne de chaque groupe X)

**Aperçu navigateur** : `.a4-page` (794×1123 px, padding 45/53 px) centré sur
fond gris `#6b7280`. WeasyPrint ignore ce div et utilise `@page { size: A4; margin: 12mm 14mm }`.

### 4.4 `cli.py`

```
Usage: eulumdat-report [OPTIONS] LDT_FILE

Options:
  -o, --output-dir  DIRECTORY  [default: même dossier que LDT_FILE]
  --template        FILE       Template Jinja2 personnalisé
  --html / --no-html           [default: html]
  --pdf  / --no-pdf            [default: pdf]
  -v, --verbose
  --help
```

Noms de sortie : `{stem}.html`, `{stem}.pdf`.

---

## 5. Tests (`tests/test_report.py`)

**122 tests, tous passants** (10 fichiers LDT samples couvrant ISYM 0–4).

| Classe | Couvre | Tests |
|---|---|---|
| `TestCollectorHeader` | collector — champs LDT | 26 |
| `TestCollectorIntensitySvg` | collector — svg_intensity | 11 |
| `TestCollectorLuminanceSvg` | collector — svg_luminance, lum_max | 20 |
| `TestCollectorUgr` | collector — structure UGR | 8 |
| `TestRendererHtml` | renderer — HTML complet | 30 |
| `TestFilters` | filtres Jinja2 | 11 |
| `TestCli` | CLI | 16 |

```bash
.venv/Scripts/pytest                 # tous les tests
.venv/Scripts/pytest -v -k "Ugr"    # filtre par nom
```

---

## 6. Samples LDT (`data/input/`)

10 fichiers EULUMDAT anonymisés issus de mesures réelles :

| Fichier | ISYM | UGR |
|---|---|---|
| `sample_02_isym4.ldt` | 4 (quadrant) | ✓ |
| `sample_04_isym2.ldt` | 2 (C0-C180) | warning |
| `sample_13_isym1.ldt` | 1 (full sym.) | ✓ |
| `sample_16_isym3.ldt` | 3 (C90-C270) | warning |
| `sample_18_isym4.ldt` | 4 (quadrant) | ✓ |
| `sample_27_isym0.ldt` | 0 (asymétrique) | warning |
| `sample_31_isym1.ldt` | 1 (full sym.) | ✓ |
| `sample_32_isym1.ldt` | 1 (full sym.) | ✓ |
| `sample_39_isym1.ldt` | 1 (full sym.) | ✓ |
| `sample_40_isym4.ldt` | 4 (quadrant) | ✓ |

---

## 7. Packaging

```toml
[project]
name = "eulumdat-report"
version = "1.0.0"
license = "MIT"

[tool.setuptools.package-data]
eulumdat_report = ["templates/*.html", "templates/*.css"]
```

```bash
# Build
.venv/Scripts/python -m build

# Publish
.venv/Scripts/twine upload dist/*
```

Le wheel inclut : `__init__.py`, `cli.py`, `collector.py`, `renderer.py`,
`templates/default.html`, `templates/default.css`.

---

## 8. Conventions de développement

- Python `src/` layout, `pyproject.toml` uniquement
- Venv : `.venv/` à la racine
- SVG toujours embarqués inline — jamais écrits sur disque comme fichier intermédiaire
- WeasyPrint appelé avec `base_url` pointant vers le dossier `templates/`
- Commits sans mention de "Claude", titres en anglais, branche `main`
- Ne jamais committer `data/input/`, `data/output/`, `dist/`, `build/`

---

## 9. Historique des versions

| Version | Date       | Changements |
|---------|------------|-------------|
| 1.0.0   | 2026-04-10 | Première version stable : collector, renderer, template A4, CLI, 122 tests |

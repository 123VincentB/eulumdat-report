"""collector.py — Collect all report data from an EULUMDAT .ldt file."""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pyldt import LdtReader

from eulumdat_report import __version__

logger = logging.getLogger(__name__)

# CIE 190:2010 — 19 standard room configurations (x_dim_H, y_dim_H)
_ROOM_CONFIGS: list[tuple[int, int]] = [
    (2, 2), (2, 3), (2, 4), (2, 6), (2, 8), (2, 12),   # X=2H
    (4, 2), (4, 3), (4, 4), (4, 6), (4, 8), (4, 12),   # X=4H
    (8, 4), (8, 6), (8, 8), (8, 12),                    # X=8H
    (12, 4), (12, 6), (12, 8),                           # X=12H
]

# CIE 190:2010 — 5 reflectance combinations (rho_ceiling, rho_wall, rho_floor)
_REFLECTANCES: list[tuple[int, int, int]] = [
    (70, 50, 20),
    (70, 30, 20),
    (50, 50, 20),
    (50, 30, 20),
    (30, 30, 20),
]


@dataclass
class LuminanceTableData:
    """Luminance table — 24 C-planes × 5 γ angles (UGR grid, cd/m²)."""

    c_planes: list[float]           # [0.0, 15.0, ..., 345.0] — 24 values
    g_angles: list[float]           # [65.0, 70.0, 75.0, 80.0, 85.0]
    # values[g_idx][c_idx] — shape [5][24], rounded integers cd/m²
    values: list[list[int | None]]
    flux_total: float               # lm (num_lamps[0] × lamp_flux[0])


@dataclass
class UgrTableData:
    """UGR catalogue table data — 19 rooms × 5 reflectances × 2 directions."""

    room_sizes: list[tuple[int, int]]
    reflectances: list[tuple[int, int, int]]
    # keys: "crosswise", "endwise" — each: 19 rows × 5 floats (None if failed)
    values: dict[str, list[list[float | None]]]
    shr: float


@dataclass
class ReportData:
    """All data needed to render a photometric report."""

    # --- Metadata ---
    source_file: str
    generated_at: str
    package_version: str

    # --- LDT header fields ---
    company: str
    luminaire_name: str
    luminaire_number: str
    date_user: str
    length: float
    width: float
    height: float
    length_lum_area: float
    width_lum_area: float
    h_lum_c0: float
    h_lum_c90: float
    h_lum_c180: float
    h_lum_c270: float
    lamp_count: int
    lamp_name: str
    lamp_flux: float
    lamp_watt: float
    lorl: float
    dff: float
    isym: int
    mc: int
    ng: int

    # --- Computed scalar fields ---
    luminous_efficacy: float | None
    half_angles: dict[float, float | None] | None
    fwhm: dict[str, float | None] | None
    lum_max: float | None

    # --- SVG strings (inline embedding) ---
    svg_intensity: str | None
    svg_luminance: str | None

    # --- Luminance table (optional — collected always, displayed on demand) ---
    lum_table: LuminanceTableData | None

    # --- UGR table ---
    ugr: UgrTableData | None


class ReportCollector:
    """Collect all report data from an EULUMDAT .ldt file."""

    @classmethod
    def collect(cls, ldt_path: str | Path) -> ReportData:
        ldt_path = Path(ldt_path)
        ldt = LdtReader.read(ldt_path)
        h = ldt.header

        # --- Lamp data (first set only) ---
        lamp_count = h.num_lamps[0] if h.num_lamps else 0
        lamp_name  = h.lamp_types[0] if h.lamp_types else ""
        lamp_flux  = h.lamp_flux[0]  if h.lamp_flux  else 0.0
        lamp_watt  = h.lamp_watt[0]  if h.lamp_watt  else 0.0

        luminous_efficacy: float | None = None
        if lamp_watt > 0:
            luminous_efficacy = lamp_flux / lamp_watt

        # --- Half-angles (ldt_analysis) ---
        half_angles: dict[float, float | None] | None = None
        fwhm: dict[str, float | None] | None = None
        try:
            from ldt_analysis import half_angle
            half_angles = half_angle(ldt, [0.0, 90.0, 180.0, 270.0])
            ha = half_angles
            fwhm = {
                "C0_C180":  (ha[0.0]  + ha[180.0]) if (ha[0.0]  is not None and ha[180.0] is not None) else None,
                "C90_C270": (ha[90.0] + ha[270.0]) if (ha[90.0] is not None and ha[270.0] is not None) else None,
            }
        except ImportError:
            logger.warning("ldt_analysis not available — half_angles set to None")
        except Exception as e:
            logger.warning("half_angle computation failed: %s", e)

        # --- Intensity diagram (eulumdat_plot) ---
        svg_intensity: str | None = None
        try:
            from eulumdat_plot import plot_ldt_svg
            svg_intensity = plot_ldt_svg(ldt_path, interpolate=True, interp_method="linear")
        except ImportError:
            logger.warning("eulumdat_plot not available — svg_intensity set to None")
        except Exception as e:
            logger.warning("plot_ldt_svg failed: %s", e)

        # --- Luminance diagram + maximum + table (eulumdat_luminance) ---
        lum_max: float | None = None
        svg_luminance: str | None = None
        lum_table: LuminanceTableData | None = None
        try:
            import numpy as np
            from eulumdat_luminance import LuminanceCalculator, LuminancePlot
            _lum_result = LuminanceCalculator.compute(ldt, full=False)
            lum_max = _lum_result.maximum
            svg_luminance = LuminancePlot(_lum_result).polar_svg()
            _tbl = _lum_result.table   # ndarray (24, 5) — c_idx × g_idx
            lum_table = LuminanceTableData(
                c_planes   = _lum_result.c_axis.tolist(),
                g_angles   = _lum_result.g_axis.tolist(),
                values     = [
                    [
                        None if np.isnan(_tbl[c, g]) else int(round(float(_tbl[c, g])))
                        for c in range(len(_lum_result.c_axis))
                    ]
                    for g in range(len(_lum_result.g_axis))
                ],
                flux_total = float(h.num_lamps[0]) * float(h.lamp_flux[0]),
            )
        except ImportError:
            logger.warning("eulumdat_luminance not available — svg_luminance/lum_max set to None")
        except Exception as e:
            logger.warning("LuminanceCalculator/LuminancePlot failed: %s", e)

        # --- UGR table (eulumdat_ugr) ---
        ugr: UgrTableData | None = None
        try:
            import numpy as np
            from eulumdat_ugr import UgrCalculator
            _ugr_result = UgrCalculator.compute(ldt)
            v = _ugr_result.values  # ndarray (19, 10)
            crosswise = [
                [None if np.isnan(v[r, c]) else float(v[r, c]) for c in range(5)]
                for r in range(19)
            ]
            endwise = [
                [None if np.isnan(v[r, 5 + c]) else float(v[r, 5 + c]) for c in range(5)]
                for r in range(19)
            ]
            ugr = UgrTableData(
                room_sizes   = _ROOM_CONFIGS,
                reflectances = _REFLECTANCES,
                values       = {"crosswise": crosswise, "endwise": endwise},
                shr          = 0.25,
            )
        except ImportError:
            logger.warning("eulumdat_ugr not available — ugr set to None")
        except Exception as e:
            logger.warning("UgrCalculator failed: %s", e)

        return ReportData(
            source_file     = ldt_path.name,
            generated_at    = datetime.now().isoformat(timespec="seconds"),
            package_version = __version__,

            company          = h.company,
            luminaire_name   = h.luminaire_name,
            luminaire_number = h.luminaire_number,
            date_user        = h.date_user,
            length           = h.length,
            width            = h.width,
            height           = h.height,
            length_lum_area  = h.length_lum_area,
            width_lum_area   = h.width_lum_area,
            h_lum_c0         = h.h_lum_c0,
            h_lum_c90        = h.h_lum_c90,
            h_lum_c180       = h.h_lum_c180,
            h_lum_c270       = h.h_lum_c270,
            lamp_count       = lamp_count,
            lamp_name        = lamp_name,
            lamp_flux        = lamp_flux,
            lamp_watt        = lamp_watt,
            lorl             = h.lorl,
            dff              = h.dff,
            isym             = h.isym,
            mc               = h.mc,
            ng               = h.ng,

            luminous_efficacy = luminous_efficacy,
            half_angles       = half_angles,
            fwhm              = fwhm,
            lum_max           = lum_max,

            svg_intensity = svg_intensity,
            svg_luminance = svg_luminance,
            lum_table     = lum_table,
            ugr           = ugr,
        )

"""eulumdat-report — Photometric datasheet generator from EULUMDAT .ldt files."""

from __future__ import annotations

from pathlib import Path

__version__ = "1.1.0"


def render_ugr_image(
    source,
    width_cm: float = 17.0,
    dpi: int = 150,
) -> bytes:
    """Render the UGR section as a PNG image (bytes).

    Parameters
    ----------
    source : str | Path | ReportData
        Path to an EULUMDAT .ldt file, or an already-collected ReportData.
    width_cm : float
        Target image width in centimetres (default 17 cm = standard Word column).
    dpi : int
        Output resolution in dots per inch (default 150).

    Returns
    -------
    bytes
        PNG image of the UGR table, suitable for use with docxtpl.InlineImage.

    Example
    -------
    ::

        import io
        from docxtpl import DocxTemplate, InlineImage
        from docx.shared import Mm
        from eulumdat_report import render_ugr_image

        png = render_ugr_image("luminaire.ldt")
        doc = DocxTemplate("template.docx")
        context = {"ugr_table": InlineImage(doc, io.BytesIO(png), width=Mm(170))}
        doc.render(context)
        doc.save("rapport.docx")
    """
    from eulumdat_report.collector import ReportCollector, ReportData
    from eulumdat_report.renderer import ReportRenderer

    if not isinstance(source, ReportData):
        source = ReportCollector.collect(Path(source))
    return ReportRenderer.render_ugr_image(source, width_cm=width_cm, dpi=dpi)


def render_luminance_image(
    source,
    width_cm: float = 17.0,
    dpi: int = 150,
) -> bytes:
    """Render the luminance table as a PNG image (bytes).

    Parameters
    ----------
    source : str | Path | ReportData
        Path to an EULUMDAT .ldt file, or an already-collected ReportData.
    width_cm : float
        Target image width in centimetres (default 17 cm = standard Word column).
    dpi : int
        Output resolution in dots per inch (default 150).

    Returns
    -------
    bytes
        PNG image of the luminance table, suitable for use with docxtpl.InlineImage.

    Example
    -------
    ::

        import io
        from docxtpl import DocxTemplate, InlineImage
        from docx.shared import Mm
        from eulumdat_report import render_luminance_image

        png = render_luminance_image("luminaire.ldt")
        doc = DocxTemplate("template.docx")
        context = {"lum_table": InlineImage(doc, io.BytesIO(png), width=Mm(170))}
        doc.render(context)
        doc.save("rapport.docx")
    """
    from eulumdat_report.collector import ReportCollector, ReportData
    from eulumdat_report.renderer import ReportRenderer

    if not isinstance(source, ReportData):
        source = ReportCollector.collect(Path(source))
    return ReportRenderer.render_luminance_image(source, width_cm=width_cm, dpi=dpi)

"""
Genera la carátula de Contestación al Requerimiento Especial RETEICA.
Estilo: documento legal minimalista — línea azul top, tipografía limpia,
secciones separadas por divisores finos.
"""
from pathlib import Path
from datetime import date

from reportlab.lib.pagesizes  import letter
from reportlab.lib.units      import cm
from reportlab.lib            import colors
from reportlab.lib.styles     import ParagraphStyle
from reportlab.lib.enums      import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus       import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable)

from core.requerimiento_extractor import DatosRequerimiento

# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL        = colors.HexColor("#1B2D5B")
AZUL_CLARO  = colors.HexColor("#4A6FA5")
GRIS_LABEL  = colors.HexColor("#777777")
GRIS_BORDE  = colors.HexColor("#CCCCCC")
GRIS_BOX    = colors.HexColor("#F5F5F5")
NEGRO       = colors.HexColor("#1A1A1A")

W = 17 * cm   # ancho útil


def _s(name, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, **kw)


ST = {
    "label": _s("label",
        fontSize=7.5, fontName="Helvetica-Bold",
        textColor=AZUL_CLARO, leading=10,
        spaceAfter=2, spaceBefore=0,
        letterSpacing=1.2),

    "titulo": _s("titulo",
        fontSize=22, fontName="Helvetica-Bold",
        textColor=AZUL, leading=26, spaceAfter=4),

    "subtitulo": _s("subtitulo",
        fontSize=10, fontName="Helvetica",
        textColor=GRIS_LABEL, leading=14),

    "ref_num": _s("ref_num",
        fontSize=9, fontName="Helvetica",
        textColor=GRIS_LABEL, leading=12, spaceAfter=4),

    "nombre": _s("nombre",
        fontSize=12, fontName="Helvetica-Bold",
        textColor=NEGRO, leading=15, spaceAfter=3),

    "detalle": _s("detalle",
        fontSize=9.5, fontName="Helvetica",
        textColor=colors.HexColor("#444444"), leading=13),

    "referencia": _s("referencia",
        fontSize=9.5, fontName="Helvetica",
        textColor=NEGRO, leading=14),

    "tag_label": _s("tag_label",
        fontSize=7, fontName="Helvetica-Bold",
        textColor=GRIS_LABEL, leading=9,
        letterSpacing=1.0),

    "tag_valor": _s("tag_valor",
        fontSize=10, fontName="Helvetica-Bold",
        textColor=NEGRO, leading=13),

    "fecha": _s("fecha",
        fontSize=10, fontName="Helvetica",
        textColor=NEGRO, leading=13, alignment=TA_RIGHT),

    "doc_oficial": _s("doc_oficial",
        fontSize=8.5, fontName="Helvetica-Bold",
        textColor=AZUL, leading=11, letterSpacing=1.5),
}


def _fecha_larga() -> str:
    meses = ["enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    hoy = date.today()
    return f"Bogotá D.C.\n{hoy.day} de {meses[hoy.month-1]} de {hoy.year}"


def _hr(color=GRIS_BORDE, thickness=0.6) -> HRFlowable:
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceAfter=0, spaceBefore=0)


def generar_caratula(datos: DatosRequerimiento, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=0*cm, bottomMargin=2*cm,
        title=f"Caratula RE {datos.expediente}",
    )

    story = []

    # ── Banda azul superior ───────────────────────────────────────────────────
    banda = Table([[""]], colWidths=[W + 5*cm], rowHeights=[0.45*cm])
    banda.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), AZUL),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(banda)
    story.append(Spacer(1, 0.9*cm))

    # ── Fila: DOCUMENTO TRIBUTARIO OFICIAL  |  fecha ─────────────────────────
    fila_top = Table([[
        Paragraph("DOCUMENTO TRIBUTARIO OFICIAL", ST["doc_oficial"]),
        Paragraph(_fecha_larga(), ST["fecha"]),
    ]], colWidths=[W * 0.55, W * 0.45])
    fila_top.setStyle(TableStyle([
        ("VALIGN",  (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(fila_top)
    story.append(Spacer(1, 1.1*cm))

    # ── Bloque título con barra lateral azul ─────────────────────────────────
    # Simulamos la barra izquierda con una tabla de 2 columnas
    barra = Table([[
        "",   # columna angosta = barra azul
        [
            Paragraph(f"Requerimiento Especial No. {datos.radicado}", ST["ref_num"]),
            Paragraph("Contestación al\nRequerimiento Especial", ST["titulo"]),
            Paragraph(
                f"Rete ICA  ·  Año gravable {datos.vigencia or '—'}",
                ST["subtitulo"]),
        ]
    ]], colWidths=[0.35*cm, W - 0.35*cm])
    barra.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), AZUL),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (1,0), (1,-1), 12),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(barra)
    story.append(Spacer(1, 1.0*cm))
    story.append(_hr())
    story.append(Spacer(1, 0.8*cm))

    # ── Sección REMITENTE | DIRIGIDO A ────────────────────────────────────────
    col_rem = [
        Paragraph("REMITENTE", ST["label"]),
        Paragraph(datos.contribuyente or "—", ST["nombre"]),
        Paragraph(f"NIT {datos.nit}" if datos.nit else "—", ST["detalle"]),
    ]
    col_dest = [
        Paragraph("DIRIGIDO A", ST["label"]),
        Paragraph("Secretaría Distrital de Hacienda", ST["nombre"]),
        Paragraph(
            "Dirección Distrital de Impuestos de Bogotá – DIB\n"
            "Subdirección de Determinación de la\n"
            "Dirección Distrital de Impuestos de Bogotá",
            ST["detalle"]),
    ]
    sec_partes = Table(
        [[col_rem, col_dest]],
        colWidths=[W * 0.48, W * 0.52])
    sec_partes.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(sec_partes)
    story.append(Spacer(1, 0.9*cm))
    story.append(_hr())
    story.append(Spacer(1, 0.8*cm))

    # ── Caja REFERENCIA ───────────────────────────────────────────────────────
    texto_ref = (
        f'Contestación al Requerimiento Especial Rete ICA No. '
        f'<b>{datos.radicado}</b>, con expediente No. '
        f'<b>{datos.expediente}</b>.'
    )
    ref_inner = Table(
        [[Paragraph("REFERENCIA", ST["label"])],
         [Paragraph(texto_ref, ST["referencia"])]],
        colWidths=[W - 1.2*cm])
    ref_inner.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
    ]))
    caja_ref = Table([[ref_inner]], colWidths=[W])
    caja_ref.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), GRIS_BOX),
        ("BOX",           (0,0), (-1,-1), 0.5, GRIS_BORDE),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(caja_ref)
    story.append(Spacer(1, 0.8*cm))

    # ── Tags: EXPEDIENTE | AÑO GRAVABLE ──────────────────────────────────────
    def _tag(label: str, valor: str, w: float) -> Table:
        PAD = 14
        inner_w = w - 2 * PAD
        t = Table(
            [[Paragraph(label, ST["tag_label"])],
             [Paragraph(valor, ST["tag_valor"])]],
            colWidths=[inner_w])
        t.setStyle(TableStyle([
            ("BOX",           (0,0), (-1,-1), 0.5, GRIS_BORDE),
            ("LEFTPADDING",   (0,0), (-1,-1), PAD),
            ("RIGHTPADDING",  (0,0), (-1,-1), PAD),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        return t

    tag_exp = _tag("EXPEDIENTE",   datos.expediente or "—", 8.0*cm)
    tag_ano = _tag("AÑO GRAVABLE", datos.vigencia   or "—", 4.5*cm)

    tags = Table([[tag_exp, "", tag_ano]],
                 colWidths=[8.0*cm, 0.6*cm, 4.5*cm])
    tags.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(tags)

    doc.build(story)
    return output_path

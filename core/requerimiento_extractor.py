"""
Extrae los datos clave de un Requerimiento Especial RETEICA
directamente desde el texto del PDF.
"""
import re
from dataclasses import dataclass, field


@dataclass
class DeclaracionPrivada:
    numero:   int
    vigencia: str
    periodo:  str
    br:       str
    rp:       str
    dr:       str
    bh:       str
    vs:       str
    ha:       str


@dataclass
class SancionInexactitud:
    numero:            int
    vigencia:          str
    periodo:           str
    retenciones_det:   str
    retenciones_liq:   str
    mayor_valor:       str
    proporcionalidad:  str
    porcentaje:        str
    sancion_final:     str


@dataclass
class SancionReducida:
    numero:            int
    vigencia:          str
    periodo:           str
    sancion_det:       str
    sancion_prop:      str
    reducida_cuarta:   str
    reducida_aplicar:  str


@dataclass
class DatosRequerimiento:
    # Identificación
    radicado:          str = ""
    expediente:        str = ""
    tipo_documento:    str = "REQUERIMIENTO ESPECIAL RETEICA"

    # Contribuyente
    contribuyente:     str = ""
    nit:               str = ""
    vigencia:          str = ""

    # Totales globales
    total_bh_declarado:   str = ""
    total_bh_medios_mag:  str = ""
    diferencia:           str = ""

    # Tablas
    declaraciones_privadas:   list = field(default_factory=list)
    declaraciones_propuestas: list = field(default_factory=list)
    sanciones_inexactitud:    list = field(default_factory=list)
    sanciones_reducidas:      list = field(default_factory=list)

    # Firmante
    firmante:          str = ""
    cargo_firmante:    str = ""
    revisado_por:      str = ""
    proyectado_por:    str = ""


def _clean(val: str) -> str:
    return re.sub(r'\s+', ' ', val).strip() if val else ""


def _fmt_currency(val: str) -> str:
    val = _clean(val).replace('$', '').replace('.', '').replace(',', '').strip()
    try:
        return f"$ {int(val):,}".replace(',', '.')
    except ValueError:
        return val


def extract_requerimiento(text: str) -> DatosRequerimiento:
    datos = DatosRequerimiento()

    # ── Radicado y expediente ──────────────────────────────────────────────
    m = re.search(r'No\s+radicado[:\s]+(\S+)', text)
    if m:
        datos.radicado = _clean(m.group(1))

    m = re.search(r'No\s+expediente[:\s]+(\S+)', text)
    if m:
        datos.expediente = _clean(m.group(1))

    # ── Contribuyente y NIT ───────────────────────────────────────────────
    m = re.search(
        r'contribuyente\s+([A-Z][A-Z\s\.\-&]+?)\s+con\s+NIT\s+No\.?\s*([\d\.]+)',
        text, re.IGNORECASE)
    if m:
        datos.contribuyente = _clean(m.group(1))
        datos.nit           = _clean(m.group(2))

    # ── Vigencia ──────────────────────────────────────────────────────────
    _vigencia = None
    m = re.search(r'\b(20\d{2})-\d\b', text)
    if m:
        _vigencia = m.group(1)
    if not _vigencia:
        for m in re.finditer(r'vigencia\D*(20\d{2})', text, re.IGNORECASE):
            _vigencia = m.group(1)
            break
    if _vigencia:
        datos.vigencia = _vigencia

    # ── Totales resumen ───────────────────────────────────────────────────
    m = re.search(
        r'TOTAL\s+RETENCIONES\s+DECLARADAS[^\$]*(\$[\s\d\.]+)\s+'
        r'TOTAL\s+MONTO[^\$]*(\$[\s\d\.]+)\s+'
        r'DIFERENCIA[^\$]*(\$[\s\d\.]+)',
        text, re.IGNORECASE | re.DOTALL)
    if m:
        datos.total_bh_declarado  = _clean(m.group(1))
        datos.total_bh_medios_mag = _clean(m.group(2))
        datos.diferencia          = _clean(m.group(3))

    # fallback: buscar la tabla de análisis
    if not datos.total_bh_declarado:
        m = re.search(
            r'(\$\s*1[\.\d]+)\s+(\$\s*9[\.\d]+)\s+(\$\s*8[\.\d]+)',
            text)
        if m:
            datos.total_bh_declarado  = _clean(m.group(1))
            datos.total_bh_medios_mag = _clean(m.group(2))
            datos.diferencia          = _clean(m.group(3))

    # ── Tabla declaraciones propuestas ────────────────────────────────────
    # Busca el bloque entre DECLARACION(ES) PROPUESTA(S) y DETERMINACIÓN
    bloque_prop = re.search(
        r'DECLARACION\(ES\)\s+PROPUESTA\(S\)(.*?)DETERMINACI[OÓ]N\s+DE\s+LA\s+SANCI[OÓ]N',
        text, re.IGNORECASE | re.DOTALL)

    if bloque_prop:
        filas = re.findall(
            r'(\d)\s+(2\d{3})\s+(\d)\s+'
            r'(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)\s+(\$\s*[\d\.]*)\s+'
            r'(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)',
            bloque_prop.group(1))
        for f in filas:
            datos.declaraciones_propuestas.append(DeclaracionPrivada(
                numero=int(f[0]), vigencia=f[1], periodo=f[2],
                br=_clean(f[3]), rp=_clean(f[4]), dr=_clean(f[5]),
                bh=_clean(f[6]), vs=_clean(f[7]), ha=_clean(f[8])))

    # ── Tabla declaraciones privadas ──────────────────────────────────────
    bloque_priv = re.search(
        r'DECLARACION\(ES\)\s+PRIVADA\(S\)(.*?)DECLARACION\(ES\)\s+PROPUESTA\(S\)',
        text, re.IGNORECASE | re.DOTALL)
    if bloque_priv:
        filas = re.findall(
            r'(\d)\s+(2\d{3})\s+(\d)\s+'
            r'(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)\s+(\$\s*[\d\.]*)\s+'
            r'(\$\s*[\d\.]+)\s+(\$\s*[\d\.]*)\s+(\$\s*[\d\.]+)',
            bloque_priv.group(1))
        for f in filas:
            datos.declaraciones_privadas.append(DeclaracionPrivada(
                numero=int(f[0]), vigencia=f[1], periodo=f[2],
                br=_clean(f[3]), rp=_clean(f[4]), dr=_clean(f[5]),
                bh=_clean(f[6]), vs=_clean(f[7]), ha=_clean(f[8])))

    # ── Tabla sanciones inexactitud ───────────────────────────────────────
    bloque_sanc = re.search(
        r'DETERMINACI[OÓ]N\s+DE\s+LA\s+SANCI[OÓ]N\s+POR\s+INEXACTITUD(.*?)'
        r'(?:Todos los valores|RESPUESTA)',
        text, re.IGNORECASE | re.DOTALL)
    if bloque_sanc:
        filas = re.findall(
            r'(\d)\s+(2\d{3})\s+(\d)\s+'
            r'(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)\s+'
            r'(\$\s*[\d\.]+)\s+(\d+%)\s+(\$\s*[\d\.]+)',
            bloque_sanc.group(1))
        for f in filas:
            datos.sanciones_inexactitud.append(SancionInexactitud(
                numero=int(f[0]), vigencia=f[1], periodo=f[2],
                retenciones_det=_clean(f[3]), retenciones_liq=_clean(f[4]),
                mayor_valor=_clean(f[5]), proporcionalidad=_clean(f[6]),
                porcentaje=_clean(f[7]), sancion_final=_clean(f[8])))

    # ── Tabla sanciones reducidas ─────────────────────────────────────────
    bloque_red = re.search(
        r'DETERMINACI[OÓ]N\s+DE\s+LA\s+SANCI[OÓ]N\s+REDUCIDA(.*?)'
        r'(?:Para el efecto|NOTIF)',
        text, re.IGNORECASE | re.DOTALL)
    if bloque_red:
        filas = re.findall(
            r'(\d)\s+(2\d{3})\s+(\d)\s+'
            r'(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)\s+(\$\s*[\d\.]+)',
            bloque_red.group(1))
        for f in filas:
            datos.sanciones_reducidas.append(SancionReducida(
                numero=int(f[0]), vigencia=f[1], periodo=f[2],
                sancion_det=_clean(f[3]), sancion_prop=_clean(f[4]),
                reducida_cuarta=_clean(f[5]), reducida_aplicar=_clean(f[6])))

    # ── Firmante ──────────────────────────────────────────────────────────
    m = re.search(r'Firmado Digitalmente[^\n]*por:\s*([A-Z][A-ZÁ-Ú\s]+)', text)
    if m:
        datos.firmante = _clean(m.group(1))

    m = re.search(r'(Jefe[^\n]+Fiscalizaci[oó]n[^\n]*)', text, re.IGNORECASE)
    if m:
        datos.cargo_firmante = _clean(m.group(1))

    m = re.search(r'Revisado por[:\s]+([A-ZÁ-Ú][^\n]+)', text, re.IGNORECASE)
    if m:
        datos.revisado_por = _clean(m.group(1))

    m = re.search(r'Proyectado por[:\s]+([A-ZÁ-Ú][^\n]+)', text, re.IGNORECASE)
    if m:
        datos.proyectado_por = _clean(m.group(1))

    return datos
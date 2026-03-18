"""
Motor de extracción por expresiones regulares + heurísticas.
Diseñado para los documentos de ACEVEDO Y CIA. SAS ASESORES INMOBILIARIOS.
Funciona 100% offline, sin GPU, sin modelos.

Integra el sistema de aprendizaje por ejemplos (learner.py):
- Si el regex falla (confianza < 0.6), consulta ejemplos previos guardados.
- Cuando el usuario corrige un resultado, llama a learner.teach() para que
  futuros documentos similares sean extraídos correctamente.
"""
import re
from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    prueba: int
    data: dict
    confidence: float
    method: str = "regex"
    warnings: list = field(default_factory=list)


_NAME = r"[A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑA-Za-záéíóúüñ\s.,&'-]{2,60}"
_OCR_PREFIX = re.compile(r"^[^A-ZÁÉÍÓÚÜÑA-Za-záéíóúüñ]+")


def _clean(text: str) -> str:
    text = re.sub(r"\s{2,}", " ", text)
    text = _OCR_PREFIX.sub("", text)
    return text.strip(" ,.-:;")


class RegexEngine:

    # ── P4 ──────────────────────────────────────────────────────────────────
    _P4_PROPIETARIO = re.compile(
        r"MOVIMIENTO\s+CONTABLE\s+PROPIETARIO\s*\n+\s*(.+?)(?:\n|CC|NIT|DIRECCI)",
        re.IGNORECASE)
    _P4_ARRENDATARIO = re.compile(
        r"MOVIMIENTO\s+CONTABLE\s+ARRENDATARIO\s*\n+\s*(.+?)(?:\n|CC|NIT|DIRECCI)",
        re.IGNORECASE)
    _P4_DUAL = re.compile(r"(.+?)\s*/\s*(.+)")

    # ── P5 ──────────────────────────────────────────────────────────────────
    _P5_DESTINATARIO = re.compile(
        r"(?:Se[ñn]ores?|Se[ñn]or|A:|Para:|Destino:|propietaria?[:\s]+de)"
        r"[\s:\n]+(" + _NAME + r")", re.IGNORECASE)
    _P5_DEST_ALT = re.compile(
        r"de\s+(?:propiedad\s+de\s+)?(" + _NAME + r"),\s*identificad",
        re.IGNORECASE)

    # ── P6 ──────────────────────────────────────────────────────────────────
    _P6_PROPIETARIO = re.compile(
        r"de\s+propiedad\s+de\s+(" + _NAME + r"),?\s*identificad",
        re.IGNORECASE)
    _P6_PROP_ALT = re.compile(
        r"corresponden\s+a\s+(" + _NAME + r")\.", re.IGNORECASE)

    # ── P7: multicapa ────────────────────────────────────────────────────────
    _P7_OTRA_SOCIEDAD = re.compile(
        r"por\s+la\s+otra[:\s]+(?:la\s+)?(?:sociedad|empresa|persona\s+natural)?\s*"
        r"(" + _NAME + r")\s*Nit", re.IGNORECASE)
    _P7_OTRA_PERSONA = re.compile(
        r"por\s+la\s+otra[:\s]+(" + _NAME + r"),?\s*identific", re.IGNORECASE)
    _P7_DENOMINARA = re.compile(
        r"(" + _NAME + r")\s*[,.]?\s*(?:Nit\.?[^,]*,\s*)?(?:quien|quienes)"
        r"\s+(?:para\s+efectos\s+de\s+este\s+Contrato\s+)?se\s+denominar[aá]\s+El\s+Arrendatario",
        re.IGNORECASE)
    _P7_FIRMA = re.compile(
        r"EL\s+ARRENDATARIO\b[^\n]*\n+\s*(" + _NAME + r")\s*\n", re.IGNORECASE)
    _P7_FALLBACK = re.compile(
        r"(?:EL\s+ARRENDATARIO|arrendatario)[:\s]+(" + _NAME + r")"
        r"(?:\n|,\s*identific|\s+CC|\s+NIT)", re.IGNORECASE)

    # ── P8: multicapa ────────────────────────────────────────────────────────
    _P8_SUSCRITOS_PN = re.compile(
        r"suscritos?[:\s]+(" + _NAME + r")[\s.,-]+mayor\s+de\s+edad",
        re.IGNORECASE)
    _P8_SUSCRITOS_ID = re.compile(
        r"suscritos?[:\s]+(" + _NAME + r"),?\s*identific", re.IGNORECASE)
    _P8_OCR_SUSCRITOS = re.compile(
        r"suscritos?[:\s]+((?:[A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑA-Za-záéíóúüñ]+[. ]+){2,5})"
        r"[\s.,-]*(?:mayor|vecino|identificad)", re.IGNORECASE)
    _P8_DENOMINARA = re.compile(
        r"(" + _NAME + r")\s*[,.]?\s*(?:de\s+una\s+parte\s+y\s*)?"
        r"(?:quien\s+en\s+el\s+texto\s+)?(?:se\s+denominar[aá]\s+EL?\s*\(?LA?\)?\s*PROPIETARIO"
        r"|quien.*se\s+llamar[aá]\s+EL?\s*\(?LA?\)?\s*PROPIETARIO)", re.IGNORECASE)
    _P8_FIRMA = re.compile(
        r"EL\s+PROPIETARIO\b[^\n]*\n+\s*(" + _NAME + r")\s*\n", re.IGNORECASE)
    _P8_CC = re.compile(
        r"(" + _NAME + r")\s*\n?\s*C\.?\s*C\.?\s*(?:No\.?)?\s*[\d.,]+\s+de\s+",
        re.IGNORECASE)

    # ── P9 ──────────────────────────────────────────────────────────────────
    _P9_DESTINATARIO = re.compile(
        r"(?:Se[ñn]ores?|Se[ñn]or|A:|Doctor|Doctora)[:\s\n]+(" + _NAME + r")",
        re.IGNORECASE)

    # ── P10 ─────────────────────────────────────────────────────────────────
    _P10_FACTURA_NUM = re.compile(
        r"(?:No\.\s+[A-Z]*(\d+)|(?:FE|FV)-(\d+)"
        r"|Factura\s+No\.?\s*[A-Z]*(\d+)|N[°º]\s*Factura\s*[A-Z]*(\d+))",
        re.IGNORECASE)
    _P10_ARRENDATARIO = re.compile(
        r"SE[NÑ]ORES?[:\s]+(.+?)(?:\s+CC/NIT|\s*\n|$)", re.IGNORECASE)
    _P10_ARRENDATARIO_ALT = re.compile(
        r"(?:arrendatario|cliente|cobrar\s+a)[:\s]+(" + _NAME + r")"
        r"(?:\n|,|\s+CC|\s+NIT)", re.IGNORECASE)

    # ── Detectores ──────────────────────────────────────────────────────────
    _DETECTORS = {
        4:  [r"MOVIMIENTO CONTABLE PROPIETARIO", r"MOVIMIENTO CONTABLE ARRENDATARIO"],
        5:  [r"SOLICITUD.*CERTIFICADO.*ICA", r"SOLICITUD.*RETENCION.*ICA",
             r"certificados.*ICA.*impuesto.*Industria"],
        6:  [r"CERTIFICACI[OÓ]N DE RETENCIONES DE ICA",
             r"certifica.*retenciones.*impuesto.*Industria.*Comercio"],
        7:  [r"CONTRATO\s+DE\s+ARRENDAMIENTO", r"El\s+Arrendatario", r"El\s+Arrendador"],
        8:  [r"CONTRATO\s+DE\s+(?:MANDATO|ADMINISTRACI[OÓ]N)",
             r"EL\s+ADMINISTRADOR", r"EL\s+PROPIETARIO",
             r"contrato\s+de\s+administraci[oó]n"],
        9:  [r"INFORMACI[OÓ]N EX[OÓ]GENA DISTRITAL", r"CORRECCI[OÓ]N.*EX[OÓ]GENA",
             r"solicitud.*correcci[oó]n.*informaci[oó]n.*ex[oó]gena"],
        10: [r"FACTURA\s+ELECTR[OÓ]NICA\s+DE\s+VENTA", r"FACTURA\s+DE\s+VENTA",
             r"(?:FE|FV)-\d+", r"No\.\s+[A-Z]*\d{4,}"],
    }

    # ── Detección ────────────────────────────────────────────────────────────

    def detect_type(self, text: str) -> int | None:
        scores = {}
        for prueba, patterns in self._DETECTORS.items():
            hits = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
            if hits > 0:
                scores[prueba] = hits
        if not scores:
            return None
        if scores.get(7) and scores.get(8):
            if re.search(r"CONTRATO\s+DE\s+ADMINISTRACI[OÓ]N|EL\s+ADMINISTRADOR",
                         text, re.IGNORECASE):
                return 8
            if re.search(r"CONTRATO\s+DE\s+ARRENDAMIENTO", text, re.IGNORECASE):
                return 7
        return max(scores, key=scores.get)

    def extract(self, text: str, prueba: int) -> ExtractionResult:
        dispatch = {
            4: self._extract_p4,  5: self._extract_p5,  6: self._extract_p6,
            7: self._extract_p7,  8: self._extract_p8,  9: self._extract_p9,
            10: self._extract_p10,
        }
        fn = dispatch.get(prueba)
        if fn is None:
            return ExtractionResult(prueba=prueba, data={}, confidence=0.0,
                                    warnings=[f"Prueba {prueba} no implementada"])
        result = fn(text)
        if result.confidence < 0.6:
            result = self._apply_learned(result, text)
        return result

    # ── Extractores ──────────────────────────────────────────────────────────

    def _extract_p4(self, text: str) -> ExtractionResult:
        warnings, data = [], {}
        m = self._P4_PROPIETARIO.search(text)
        if m:
            raw = m.group(1).strip()
            dual = self._P4_DUAL.match(raw)
            data["propietarios"] = [dual.group(1).strip(), dual.group(2).strip()] if dual else [raw]
        else:
            data["propietarios"] = []
            warnings.append("No se encontró propietario en P4")
        m = self._P4_ARRENDATARIO.search(text)
        if m:
            data["arrendatario"] = m.group(1).strip()
        else:
            data["arrendatario"] = None
            warnings.append("No se encontró arrendatario en P4")
        return ExtractionResult(4, data, self._conf(data, ["propietarios", "arrendatario"]),
                                warnings=warnings)

    def _extract_p5(self, text: str) -> ExtractionResult:
        warnings, dest = [], None
        for pat in (self._P5_DESTINATARIO, self._P5_DEST_ALT):
            m = pat.search(text)
            if m:
                dest = _clean(m.group(1)); break
        if not dest:
            warnings.append("No se encontró destinatario en P5")
        return ExtractionResult(5, {"destinatario": dest}, 1.0 if dest else 0.3,
                                warnings=warnings)

    def _extract_p6(self, text: str) -> ExtractionResult:
        warnings, prop = [], None
        for pat in (self._P6_PROPIETARIO, self._P6_PROP_ALT):
            m = pat.search(text)
            if m:
                prop = _clean(m.group(1)); break
        if not prop:
            warnings.append("No se encontró propietario en P6")
        return ExtractionResult(6, {"propietario": prop}, 1.0 if prop else 0.3,
                                warnings=warnings)

    def _extract_p7(self, text: str) -> ExtractionResult:
        """Multicapa: por la otra → denominará → firma → fallback."""
        warnings, arr = [], None
        for pat in (self._P7_OTRA_SOCIEDAD, self._P7_OTRA_PERSONA,
                    self._P7_DENOMINARA, self._P7_FIRMA, self._P7_FALLBACK):
            m = pat.search(text)
            if m:
                candidate = _clean(m.group(1))
                if len(candidate.split()) >= 2 and not self._is_noise(candidate):
                    arr = candidate; break
        if not arr:
            warnings.append("No se encontró arrendatario en P7")
        return ExtractionResult(7, {"arrendatario": arr},
                                1.0 if arr else 0.3, warnings=warnings)

    def _extract_p8(self, text: str) -> ExtractionResult:
        """Multicapa: suscritos → OCR → denominará → firma → C.C."""
        warnings, prop = [], None
        for pat in (self._P8_SUSCRITOS_PN, self._P8_SUSCRITOS_ID,
                    self._P8_OCR_SUSCRITOS, self._P8_DENOMINARA,
                    self._P8_FIRMA, self._P8_CC):
            m = pat.search(text)
            if m:
                raw = m.group(1)
                # Limpiar puntos de ruido OCR: "ADOLFO. MARIA." → "ADOLFO MARIA"
                candidate = re.sub(r"\.(\s+)", r" ", raw)
                candidate = _clean(candidate)
                if len(candidate.split()) >= 2 and not self._is_noise(candidate):
                    prop = candidate; break
        if not prop:
            warnings.append("No se encontró propietario en P8")
        return ExtractionResult(8, {"propietario": prop},
                                1.0 if prop else 0.3, warnings=warnings)

    def _extract_p9(self, text: str) -> ExtractionResult:
        warnings, dest = [], None
        m = self._P9_DESTINATARIO.search(text)
        if m:
            dest = _clean(m.group(1))
        if not dest:
            warnings.append("No se encontró destinatario en P9")
        return ExtractionResult(9, {"destinatario": dest},
                                1.0 if dest else 0.3, warnings=warnings)

    def _extract_p10(self, text: str) -> ExtractionResult:
        warnings = []
        num = None
        m = self._P10_FACTURA_NUM.search(text)
        if m:
            num = next((g for g in m.groups() if g), None)
        arr = None
        m = self._P10_ARRENDATARIO.search(text)
        if m:
            arr = m.group(1).strip()
        else:
            m = self._P10_ARRENDATARIO_ALT.search(text)
            if m:
                arr = _clean(m.group(1))
        if not num:
            warnings.append("No se encontró número de factura en P10")
        if not arr:
            warnings.append("No se encontró arrendatario en P10")
        data = {"numero_factura": num, "arrendatario": arr}
        return ExtractionResult(10, data, self._conf(data, ["numero_factura", "arrendatario"]),
                                warnings=warnings)

    # ── Learner ──────────────────────────────────────────────────────────────

    def _apply_learned(self, result: ExtractionResult, text: str) -> ExtractionResult:
        try:
            from engines.learner import lookup
            for field_name, current_val in list(result.data.items()):
                if not current_val:
                    learned, score = lookup(result.prueba, text, field_name)
                    if learned:
                        result.data[field_name] = learned
                        result.warnings.append(
                            f"'{field_name}' de ejemplos guardados (sim={score:.0%})")
                        result.method = "regex+learned"
            result.confidence = self._conf(result.data, list(result.data.keys()))
        except Exception:
            pass
        return result

    # ── Utilidades ───────────────────────────────────────────────────────────

    @staticmethod
    def _conf(data: dict, required_keys: list) -> float:
        if not required_keys:
            return 0.0
        found = sum(1 for k in required_keys if data.get(k))
        return found / len(required_keys)

    _NOISE_WORDS = {
        "el", "la", "los", "las", "un", "una", "de", "del", "al", "en",
        "con", "por", "para", "que", "se", "su", "sus", "contrato",
        "presente", "inmueble", "arrendamiento",
    }

    @classmethod
    def _is_noise(cls, text: str) -> bool:
        words = text.lower().split()
        if not words:
            return True
        return sum(1 for w in words if w in cls._NOISE_WORDS) / len(words) > 0.6

"""
Motor de extracción usando Ollama (LLM local).
Requiere: ollama corriendo en localhost con un modelo descargado.
Instalar: https://ollama.com  →  ollama pull llama3
"""
import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT
from engines.regex_engine import ExtractionResult


SYSTEM_PROMPT = (
    "Eres un asistente especializado en documentos contables y legales colombianos "
    "de administración inmobiliaria. Extrae información estructurada del texto. "
    "Responde SOLO con JSON válido, sin texto extra, sin markdown, sin backticks."
)

PROMPTS = {
    4: (
        "Del siguiente movimiento contable extrae:\n"
        "- propietarios: array con el/los nombre(s) del propietario(s) "
        "(sección MOVIMIENTO CONTABLE PROPIETARIO, puede ser dual separado por /)\n"
        "- arrendatario: nombre del arrendatario "
        "(sección MOVIMIENTO CONTABLE ARRENDATARIO)\n"
        'Responde: {"propietarios": [...], "arrendatario": "..."}'
    ),
    5: (
        "De esta solicitud extrae:\n"
        "- destinatario: nombre completo de la persona a quien va dirigida\n"
        'Responde: {"destinatario": "..."}'
    ),
    6: (
        "De esta certificación de retenciones ICA extrae:\n"
        "- propietario: nombre completo del propietario del inmueble\n"
        'Responde: {"propietario": "..."}'
    ),
    7: (
        "De este contrato de arrendamiento extrae:\n"
        "- arrendatario: nombre completo del arrendatario\n"
        'Responde: {"arrendatario": "..."}'
    ),
    8: (
        "De este contrato de mandato/administración extrae:\n"
        "- propietario: nombre completo del propietario/mandante\n"
        'Responde: {"propietario": "..."}'
    ),
    9: (
        "De esta solicitud de corrección exógena distrital extrae:\n"
        "- destinatario: nombre completo del destinatario\n"
        'Responde: {"destinatario": "..."}'
    ),
    10: (
        "De esta factura electrónica de arrendamiento extrae:\n"
        "- numero_factura: SOLO los dígitos del número. "
        "Ejemplos: 'No. F491276' → '491276', 'FE-123' → '123', 'No. 491276' → '491276'.\n"
        "- arrendatario: nombre completo del cliente/arrendatario. "
        "Busca tras 'SEÑORES:' o en el campo del cliente. "
        "Ejemplo: 'SEÑORES: ALIMENTOS CRIOLLOS S.A.' → 'ALIMENTOS CRIOLLOS S.A.'.\n"
        'Responde SOLO con JSON: {"numero_factura": "491276", "arrendatario": "ALIMENTOS CRIOLLOS S.A."}'
    ),
}

AUTO_DETECT_PROMPT = (
    "Determina el tipo de documento. Opciones: "
    "prueba4 (movimiento contable), prueba5 (solicitud cert ICA), "
    "prueba6 (certificacion ICA), prueba7 (contrato arrendamiento), "
    "prueba8 (contrato mandato), prueba9 (correccion exogena), "
    "prueba10 (factura), desconocido.\n"
    'Responde: {"tipo": "prueba4|...|desconocido"}'
)


class OllamaEngine:

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def _chat(self, system: str, user: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
            return data["message"]["content"].strip()

    def _parse_json(self, raw: str) -> dict:
        raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
        return json.loads(raw)

    def detect_type(self, text: str) -> int | None:
        raw = self._chat(SYSTEM_PROMPT, f"{AUTO_DETECT_PROMPT}\n\n---\n{text[:3000]}")
        try:
            parsed = self._parse_json(raw)
            tipo = parsed.get("tipo", "")
            mapping = {
                "prueba4": 4, "prueba5": 5, "prueba6": 6,
                "prueba7": 7, "prueba8": 8, "prueba9": 9, "prueba10": 10,
            }
            return mapping.get(tipo)
        except Exception:
            return None

    def extract(self, text: str, prueba: int) -> ExtractionResult:
        prompt = PROMPTS.get(prueba)
        if not prompt:
            return ExtractionResult(prueba, {}, 0.0,
                                    method="ollama",
                                    warnings=[f"Prueba {prueba} sin prompt"])
        try:
            raw = self._chat(SYSTEM_PROMPT, f"{prompt}\n\n---\n{text[:5000]}")
            data = self._parse_json(raw)
            return ExtractionResult(prueba, data, 0.9, method="ollama")
        except Exception as e:
            return ExtractionResult(prueba, {}, 0.0,
                                    method="ollama",
                                    warnings=[f"Error Ollama: {e}"])

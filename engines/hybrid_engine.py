"""
Motor híbrido: corre regex primero (rápido, offline).
Si la confianza es baja, escala al LLM configurado.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.regex_engine import RegexEngine, ExtractionResult
from config import EXTRACTION_ENGINE, OLLAMA_MODEL


_CONFIDENCE_THRESHOLD = 0.6


def _get_llm_engine():
    if EXTRACTION_ENGINE == "ollama":
        from engines.ollama_engine import OllamaEngine
        return OllamaEngine()
    if EXTRACTION_ENGINE == "openai_compat":
        from engines.openai_compat_engine import OpenAICompatEngine
        return OpenAICompatEngine()
    return None


class HybridEngine:

    def __init__(self, force_llm: bool = False):
        self._regex = RegexEngine()
        self._llm   = _get_llm_engine()
        self._force = force_llm

    @property
    def llm_available(self) -> bool:
        if self._llm is None:
            return False
        return self._llm.is_available()

    def detect_type(self, text: str) -> int | None:
        detected = self._regex.detect_type(text)
        if detected:
            return detected
        if self.llm_available:
            return self._llm.detect_type(text)
        return None

    def extract(self, text: str, prueba: int) -> ExtractionResult:
        result = self._regex.extract(text, prueba)

        use_llm = (
            self._force or
            (result.confidence < _CONFIDENCE_THRESHOLD and self.llm_available)
        )

        if use_llm:
            llm_result = self._llm.extract(text, prueba)
            if llm_result.confidence > result.confidence:
                llm_result.warnings = result.warnings + llm_result.warnings
                llm_result.warnings.append(
                    f"regex conf={result.confidence:.1f} → escaló a {llm_result.method}"
                )
                return llm_result

        return result

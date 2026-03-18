"""
Sistema de aprendizaje por ejemplos.
Cuando el regex falla o el usuario corrige un resultado, guarda el par
(fragmento_texto → valor_correcto) y lo usa en extracciones futuras
mediante coincidencia difusa.
"""
import json
import re
from pathlib import Path
from difflib import SequenceMatcher


_STORE_PATH = Path(__file__).parent.parent / "learned_examples.json"
_SIMILARITY_THRESHOLD = 0.55   # mínimo de similitud para usar un ejemplo


def _load() -> dict:
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(store: dict):
    _STORE_PATH.write_text(
        json.dumps(store, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a[:500], b[:500]).ratio()


def _fingerprint(text: str) -> str:
    """Fragmento representativo del texto para comparación."""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:400]


class ExampleLearner:
    """
    Uso:
        learner = ExampleLearner()
        # Guardar corrección del usuario:
        learner.teach(prueba=7, text=full_text, field="arrendatario", value="ESTRUCTURAS SOSTENIBLES SAS")
        # Buscar en ejemplos guardados:
        result = learner.lookup(prueba=7, text=full_text, field="arrendatario")
    """

    def __init__(self):
        self._store = _load()

    def teach(self, prueba: int, text: str, field: str, value: str):
        """Guarda un ejemplo correcto."""
        key = str(prueba)
        if key not in self._store:
            self._store[key] = {}
        if field not in self._store[key]:
            self._store[key][field] = []

        fp = _fingerprint(text)
        # Evitar duplicados exactos
        for ex in self._store[key][field]:
            if ex["fingerprint"] == fp:
                ex["value"] = value
                _save(self._store)
                return

        self._store[key][field].append({
            "fingerprint": fp,
            "value": value,
        })
        _save(self._store)

    def lookup(self, prueba: int, text: str, field: str) -> tuple[str | None, float]:
        """
        Busca el valor más cercano en los ejemplos guardados.
        Devuelve (value, similarity) o (None, 0.0) si no hay match.
        """
        key = str(prueba)
        examples = self._store.get(key, {}).get(field, [])
        if not examples:
            return None, 0.0

        fp = _fingerprint(text)
        best_value = None
        best_score = 0.0

        for ex in examples:
            score = _similarity(fp, ex["fingerprint"])
            if score > best_score:
                best_score = score
                best_value = ex["value"]

        if best_score >= _SIMILARITY_THRESHOLD:
            return best_value, best_score
        return None, 0.0

    def list_examples(self, prueba: int | None = None) -> dict:
        if prueba is not None:
            return {str(prueba): self._store.get(str(prueba), {})}
        return self._store

    def clear(self, prueba: int | None = None, field: str | None = None):
        if prueba is None:
            self._store = {}
        elif field is None:
            self._store.pop(str(prueba), None)
        else:
            self._store.get(str(prueba), {}).pop(field, None)
        _save(self._store)


# Singleton global
_learner = ExampleLearner()


def teach(prueba: int, text: str, field: str, value: str):
    _learner.teach(prueba, text, field, value)


def lookup(prueba: int, text: str, field: str) -> tuple[str | None, float]:
    return _learner.lookup(prueba, text, field)


def get_learner() -> ExampleLearner:
    return _learner

"""
Motor OpenAI-compatible para cualquier servidor local:
- LM Studio      → http://localhost:1234/v1
- Jan            → http://localhost:1337/v1
- text-gen-webui → http://localhost:5000/v1
- llama.cpp      → http://localhost:8080/v1
"""
import json
import urllib.request
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OPENAI_COMPAT_BASE_URL, OPENAI_COMPAT_MODEL, OLLAMA_TIMEOUT
from engines.regex_engine import ExtractionResult
from engines.ollama_engine import SYSTEM_PROMPT, PROMPTS, AUTO_DETECT_PROMPT


class OpenAICompatEngine:

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or OPENAI_COMPAT_BASE_URL).rstrip("/")
        self.model    = model or OPENAI_COMPAT_MODEL
        self.timeout  = OLLAMA_TIMEOUT

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/models")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    def _chat(self, system: str, user: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": 512,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()

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
            mapping = {f"prueba{i}": i for i in range(4, 11)}
            return mapping.get(tipo)
        except Exception:
            return None

    def extract(self, text: str, prueba: int) -> ExtractionResult:
        prompt = PROMPTS.get(prueba)
        if not prompt:
            return ExtractionResult(prueba, {}, 0.0,
                                    method="openai_compat",
                                    warnings=[f"Prueba {prueba} sin prompt"])
        try:
            raw = self._chat(SYSTEM_PROMPT, f"{prompt}\n\n---\n{text[:5000]}")
            data = self._parse_json(raw)
            return ExtractionResult(prueba, data, 0.9, method="openai_compat")
        except Exception as e:
            return ExtractionResult(prueba, {}, 0.0,
                                    method="openai_compat",
                                    warnings=[f"Error: {e}"])

# Procesador PDF

Sistema local de renombrado inteligente de documentos contables/legales.
Funciona **100% offline** con regex. Escala a LLM local (Ollama, LM Studio)
cuando se tiene la posibilidad de usar un modelo.

---

## Instalación

```bash
pip install PyMuPDF rich python-dotenv
```

---

## Uso rápido

```bash
# Modo interactivo (te pregunta todo)
python main.py

# Procesar carpeta con tipo específico
python main.py --input ./pdfs --prueba 6

# Sin empaquetar en ZIP (solo copia renombrada)
python main.py --input ./pdfs --prueba 4 --no-zip

# Forzar LLM local para los que falle el regex
python main.py --input ./pdfs --prueba 7 --llm
```

---

## Estructura del proyecto

```
pdf_processor/
│
├── main.py                  ← Punto de entrada (CLI + interactivo)
├── processor.py             ← Orquestador principal
├── config.py                ← Configuración global
├── requirements.txt
│
├── core/
│   ├── extractor.py         ← Extrae texto de PDFs con PyMuPDF
│   ├── namer.py             ← Genera el nombre final
│   └── packager.py          ← Copia renombrada / empaqueta ZIP
│
├── engines/
│   ├── regex_engine.py      ← Extracción offline por patrones (principal)
│   ├── ollama_engine.py     ← LLM local vía Ollama
│   ├── openai_compat_engine.py  ← LLM local vía LM Studio / Jan / llama.cpp
│   └── hybrid_engine.py     ← Regex primero; LLM si confianza < 60%
│
└── rules/
    ├── formats.py           ← Plantillas de nombre por tipo de prueba
    └── sanitizer.py         ← Limpieza: tildes, ñ, caracteres inválidos
```

---

## Tipos de documento soportados

| Prueba | Documento | Formato de nombre |
|--------|-----------|-------------------|
| 4 | Movimiento contable mensual | `PRUEBA 4. Movimiento Contable Propietario [nombre(s)] Arrendatario [nombre].pdf` |
| 5 | Solicitud certificados retención ICA | `PRUEBA 5. Solicitud Certificados Retencion de ICA [destinatario].pdf` |
| 6 | Certificación retenciones ICA | `PRUEBA 6. Certificacion ICA [NIT] [propietario].pdf` |
| 7 | Contrato de arrendamiento | `PRUEBA 7. Contrato de Arrendamiento [arrendatario].pdf` |
| 8 | Contrato de mandato | `PRUEBA 8. Contrato de Mandato [propietario].pdf` |
| 9 | Corrección exógena distrital | `PRUEBA 9. Solicitud De Correccion Informacion Exogena Distrital [destinatario].pdf` |
| 10 | Factura (número más bajo) | `PRUEBA 10. Factura Arrendatario [nombre carpeta].pdf` |

---

## Reglas de nombrado

- Sin tildes ni `ñ` → equivalente ASCII
- `&` → `Y`
- `/` → ` - ` (propietario dual en PRUEBA 4)
- Caracteres inválidos en nombre de archivo → eliminados
- **PRUEBA 4**: solo lee la **primera página** para extraer nombres
- **PRUEBA 6**: el NIT se toma del prefijo numérico del archivo original

---

## Configurar LLM local (opcional)

Edita `config.py`:

```python
# "regex" | "ollama" | "openai_compat"
EXTRACTION_ENGINE = "ollama"

OLLAMA_MODEL    = "llama3"           # o mistral, phi3, gemma2
OLLAMA_BASE_URL = "http://localhost:11434"

# Para LM Studio / Jan / llama.cpp:
EXTRACTION_ENGINE          = "openai_compat"
OPENAI_COMPAT_BASE_URL     = "http://localhost:1234/v1"
OPENAI_COMPAT_MODEL        = "nombre-del-modelo"
```

### Instalar Ollama

```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3        # ~4 GB, bueno para extracción
# o más liviano:
ollama pull phi3          # ~2 GB
ollama pull mistral       # ~4 GB
```

El motor híbrido usa regex primero (instantáneo) y solo llama al LLM
cuando la confianza del regex cae por debajo del 60%.

---

## Extender para nuevos tipos de documento

**1. Agregar formato en `rules/formats.py`:**
```python
def format_prueba11(campo: str) -> str:
    return f"PRUEBA 11. Mi Documento {_s(campo)}.pdf"

FORMATTERS[11] = format_prueba11
```

**2. Agregar patrón regex en `engines/regex_engine.py`:**
```python
_DETECTORS[11] = [r"TEXTO IDENTIFICADOR DEL DOCUMENTO"]

def _extract_p11(self, text: str) -> ExtractionResult:
    m = re.search(r"mi_patron: (.+)", text)
    campo = m.group(1).strip() if m else None
    return ExtractionResult(11, {"campo": campo}, 1.0 if campo else 0.3)
```

**3. Agregar prompt LLM en `engines/ollama_engine.py`:**
```python
PROMPTS[11] = (
    "Extrae del documento:\n- campo: descripción\n"
    'Responde: {"campo": "..."}'
)
```

**4. Agregar builder en `core/namer.py`:**
```python
case 11:
    return fn(data.get("campo") or "DESCONOCIDO")
```

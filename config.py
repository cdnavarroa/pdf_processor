from pathlib import Path

# Motor de extracción: "regex" | "ollama" | "openai_compat"
EXTRACTION_ENGINE = "regex"

# Configuracion Ollama (si se usa)
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"          
OLLAMA_TIMEOUT = 120

# Configuracion OpenAI-compatible (si se usa)
OPENAI_COMPAT_BASE_URL = "http://localhost:1234/v1"
OPENAI_COMPAT_MODEL = "local-model"

# Directorios por defecto
DEFAULT_OUTPUT_DIR = Path("./output")
DEFAULT_INPUT_DIR  = Path("./input")
TEMP_DIR           = Path("/tmp/pdf_processor")

# Procesamiento
PDF_MAX_CHARS_FOR_LLM = 6000 # Limite de caracteres para enviar a LLM
PRUEBAS_DISPONIBLES   = [4, 5, 6, 7, 8, 9, 10]

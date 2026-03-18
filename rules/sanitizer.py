import re
import unicodedata


_CHAR_MAP = {
    "&": "Y",
    "/": " - ",
    "\\": " - ",
    ":": "",
    "*": "",
    "?": "",
    '"': "",
    "<": "",
    ">": "",
    "|": "",
    "\n": " ",
    "\r": " ",
    "\t": " ",
}


def remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def sanitize_name(name: str) -> str:
    name = name.upper().strip()
    name = remove_accents(name)
    for char, rep in _CHAR_MAP.items():
        name = name.replace(char, rep)
    name = re.sub(r" {2,}", " ", name).strip()
    return name


def extract_nit_prefix(filename: str) -> str:
    m = re.match(r"^(\d+)", Path(filename).stem if "." in filename else filename)
    return m.group(1) if m else ""


from pathlib import Path

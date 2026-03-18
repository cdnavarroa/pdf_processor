from pathlib import Path
from rules.formats import FORMATTERS
from rules.sanitizer import extract_nit_prefix


class Namer:

    def build(
        self,
        prueba: int,
        data: dict,
        original_filename: str = "",
    ) -> str:
        fn = FORMATTERS.get(prueba)
        if fn is None:
            raise ValueError(f"Prueba {prueba} no soportada")

        match prueba:
            case 4:
                props = data.get("propietarios") or ["DESCONOCIDO"]
                arr   = data.get("arrendatario") or "DESCONOCIDO"
                return fn(props, arr)
            case 5:
                return fn(data.get("destinatario") or "DESCONOCIDO")
            case 6:
                nit  = extract_nit_prefix(original_filename)
                prop = data.get("propietario") or "DESCONOCIDO"
                return fn(nit, prop)
            case 7:
                return fn(data.get("arrendatario") or "DESCONOCIDO")
            case 8:
                return fn(data.get("propietario") or "DESCONOCIDO")
            case 9:
                return fn(data.get("destinatario") or "DESCONOCIDO")
            case 10:
                # nombre_carpeta tiene prioridad (batch por carpetas)
                # si no hay carpeta, usar arrendatario extraído del PDF
                folder = data.get("nombre_carpeta") or data.get("arrendatario") or "DESCONOCIDO"
                return fn(folder)
            case _:
                raise ValueError(f"Prueba {prueba} no tiene builder")

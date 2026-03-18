from rules.sanitizer import sanitize_name


def _s(text: str) -> str:
    return sanitize_name(text) if text else "DESCONOCIDO"


def format_prueba4(propietarios: list, arrendatario: str) -> str:
    prop = " - ".join(_s(p) for p in propietarios) if len(propietarios) > 1 else _s(propietarios[0])
    return f"PRUEBA 4. Movimiento Contable Propietario {prop} Arrendatario {_s(arrendatario)}.pdf"


def format_prueba5(destinatario: str) -> str:
    return f"PRUEBA 5. Solicitud Certificados Retencion de ICA {_s(destinatario)}.pdf"


def format_prueba6(nit: str, propietario: str) -> str:
    return f"PRUEBA 6. Certificacion ICA {nit.strip()} {_s(propietario)}.pdf"


def format_prueba7(arrendatario: str) -> str:
    return f"PRUEBA 7. Contrato de Arrendamiento {_s(arrendatario)}.pdf"


def format_prueba8(propietario: str) -> str:
    return f"PRUEBA 8. Contrato de Mandato {_s(propietario)}.pdf"


def format_prueba9(destinatario: str) -> str:
    return f"PRUEBA 9. Solicitud De Correccion Informacion Exogena Distrital {_s(destinatario)}.pdf"


def format_prueba10(nombre_carpeta: str) -> str:
    return f"PRUEBA 10. Factura Arrendatario {_s(nombre_carpeta)}.pdf"


FORMATTERS = {
    4: format_prueba4,
    5: format_prueba5,
    6: format_prueba6,
    7: format_prueba7,
    8: format_prueba8,
    9: format_prueba9,
    10: format_prueba10,
}

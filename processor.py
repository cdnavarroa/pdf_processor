"""
Orquestador: une extractor, motor, namer y packager.

Cuando un campo no puede extraerse automáticamente, el Processor
registra qué faltó en FileResult.missing_fields. El método
interactive_correct() luego pregunta al usuario por cada campo
faltante y guarda la respuesta en el learner para usos futuros.
"""
from dataclasses import dataclass, field
from pathlib import Path

from core.extractor import PDFExtractor
from core.namer     import Namer
from core.packager  import Packager
from engines.hybrid_engine import HybridEngine
from config import DEFAULT_OUTPUT_DIR


# Etiquetas legibles para mostrar al usuario por campo
_FIELD_LABELS = {
    "propietarios":   "Nombre(s) del propietario (separados por / si son varios)",
    "propietario":    "Nombre del propietario",
    "arrendatario":   "Nombre del arrendatario",
    "destinatario":   "Nombre del destinatario",
    "numero_factura": "Número de factura (solo dígitos)",
    "nombre_carpeta": "Nombre del arrendatario (para el nombre de archivo)",
}


@dataclass
class FileResult:
    src:            Path
    new_name:       str | None  = None
    prueba:         int | None  = None
    confidence:     float       = 0.0
    method:         str         = ""
    warnings:       list        = field(default_factory=list)
    error:          str | None  = None
    missing_fields: list        = field(default_factory=list)  # campos que fallaron
    extracted_data: dict        = field(default_factory=dict)  # datos completos
    raw_text:       str         = ""                           # texto del PDF

    @property
    def ok(self) -> bool:
        return self.error is None and self.new_name is not None

    @property
    def needs_correction(self) -> bool:
        return bool(self.missing_fields)


@dataclass
class BatchResult:
    files:    list[FileResult] = field(default_factory=list)
    zip_path: Path | None      = None

    @property
    def success_count(self) -> int:
        return sum(1 for f in self.files if f.ok)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.files if not f.ok)

    @property
    def pending_correction(self) -> list[FileResult]:
        return [f for f in self.files if f.needs_correction]


class Processor:

    def __init__(self, force_llm: bool = False):
        self._extractor = PDFExtractor()
        self._engine    = HybridEngine(force_llm=force_llm)
        self._namer     = Namer()
        self._packer    = Packager()

    # ── Archivo individual ───────────────────────────────────────────────────

    def process_file(
        self,
        path: Path,
        prueba: int | None = None,
        first_page_only: bool = False,
    ) -> FileResult:
        result = FileResult(src=path)

        try:
            text = (
                self._extractor.first_page(path)
                if (first_page_only or prueba == 4)
                else self._extractor.extract(path)
            )
            result.raw_text = text

            if prueba is None:
                prueba = self._engine.detect_type(text)
                if prueba is None:
                    result.error = "No se pudo detectar el tipo de documento"
                    return result

            result.prueba = prueba

            extraction = self._engine.extract(text, prueba)
            result.confidence    = extraction.confidence
            result.method        = extraction.method
            result.warnings      = extraction.warnings
            result.extracted_data = dict(extraction.data)

            # Registrar campos que quedaron vacíos
            result.missing_fields = [
                k for k, v in extraction.data.items()
                if not v or (isinstance(v, list) and not v)
            ]

            result.new_name = self._namer.build(
                prueba=prueba,
                data=extraction.data,
                original_filename=path.name,
            )

        except Exception as exc:
            result.error = str(exc)

        return result

    # ── Lote ─────────────────────────────────────────────────────────────────

    def process_batch(
        self,
        input_dir: Path,
        prueba: int | None = None,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        pack_zip: bool = True,
        on_progress=None,
    ) -> BatchResult:
        pdfs  = sorted(input_dir.glob("*.pdf"))
        batch = BatchResult()

        for i, pdf in enumerate(pdfs):
            fr = self.process_file(pdf, prueba=prueba)
            batch.files.append(fr)
            if on_progress:
                on_progress(i + 1, len(pdfs), fr)

        self._pack(batch, prueba, output_dir, pack_zip)
        return batch

    def _pack(self, batch: BatchResult, prueba: int | None,
              output_dir: Path, pack_zip: bool):
        if not batch.success_count:
            return
        prueba_num = prueba or (batch.files[0].prueba if batch.files else 0)
        pairs = [(f.src, f.new_name) for f in batch.files if f.ok]
        if pack_zip:
            batch.zip_path = self._packer.to_zip(
                pairs, output_dir / self._packer.zip_name(prueba_num or 0))
        else:
            self._packer.to_folder(pairs, output_dir)

    # ── Corrección interactiva ───────────────────────────────────────────────

    def interactive_correct(
        self,
        batch: BatchResult,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        pack_zip: bool = True,
        ask_fn=None,       # fn(prompt) -> str   (permite inyectar en tests)
        print_fn=None,     # fn(msg, style)
    ) -> int:
        """
        Para cada archivo con campos faltantes, pregunta al usuario el valor
        correcto, enseña al learner y regenera el nombre.

        Devuelve el número de archivos corregidos.
        """
        from engines.learner import teach

        pending = batch.pending_correction
        if not pending:
            return 0

        _ask   = ask_fn   or _default_ask
        _print = print_fn or _default_print

        corrected = 0

        _print(f"\n[bold yellow]⚠  {len(pending)} archivo(s) necesitan corrección manual:[/bold yellow]")

        for fr in pending:
            _print(f"\n[cyan]Archivo:[/cyan] {fr.src.name}")
            if fr.prueba:
                _print(f"[dim]Tipo: Prueba {fr.prueba}[/dim]")

            # Mostrar lo que sí se extrajo
            for k, v in fr.extracted_data.items():
                if v and k not in fr.missing_fields:
                    _print(f"  [green]✓[/green] {k}: {v}")

            # Pedir cada campo faltante
            data_updated = dict(fr.extracted_data)
            any_filled   = False

            for field_name in fr.missing_fields:
                label = _FIELD_LABELS.get(field_name, field_name)
                _print(f"  [red]✗[/red] {field_name} no encontrado")

                value = _ask(f"  → {label}: ").strip()

                if not value:
                    _print("    [dim]Saltado (Enter vacío)[/dim]")
                    continue

                # Procesar propietarios como lista si hay "/"
                if field_name == "propietarios":
                    parsed = [p.strip() for p in value.split("/") if p.strip()]
                    data_updated[field_name] = parsed
                    # Enseñar cada nombre por separado para mejor matching
                    for p in parsed:
                        teach(fr.prueba, fr.raw_text, field_name, value)
                else:
                    data_updated[field_name] = value
                    teach(fr.prueba, fr.raw_text, field_name, value)

                any_filled = True

            if any_filled:
                # Regenerar nombre con datos corregidos
                try:
                    new_name = self._namer.build(
                        prueba=fr.prueba,
                        data=data_updated,
                        original_filename=fr.src.name,
                    )
                    fr.new_name        = new_name
                    fr.extracted_data  = data_updated
                    fr.missing_fields  = [
                        k for k, v in data_updated.items()
                        if not v or (isinstance(v, list) and not v)
                    ]
                    _print(f"  [green]✓ Nombre generado:[/green] {new_name}")
                    corrected += 1
                except Exception as e:
                    _print(f"  [red]Error generando nombre: {e}[/red]")

        # Re-empaquetar si hubo correcciones
        if corrected > 0:
            _print(f"\n[bold]Re-empaquetando con {corrected} archivo(s) corregido(s)...[/bold]")
            prueba_num = batch.files[0].prueba if batch.files else 0
            self._pack(batch, prueba_num, output_dir, pack_zip)
            if batch.zip_path:
                _print(f"[green]ZIP actualizado:[/green] {batch.zip_path}")

        return corrected

    # ── Factura más baja (P10) ───────────────────────────────────────────────

    def select_lowest_invoice(self, folder: Path) -> Path | None:
        import re
        candidates = {}
        for pdf in folder.glob("*.pdf"):
            text = self._extractor.first_page(pdf)
            m = re.search(
                r"(?:No\.\s+[A-Z]*(\d+)|(?:FE|FV)-(\d+)|Factura\s+No\.?\s*[A-Z]*(\d+))",
                text, re.IGNORECASE)
            if m:
                num = next((g for g in m.groups() if g), None)
                if num:
                    candidates[int(num)] = pdf
        return candidates[min(candidates)] if candidates else None


# ── Helpers de I/O por defecto ───────────────────────────────────────────────

def _default_ask(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def _default_print(msg: str, style: str = ""):
    # Eliminar tags Rich para salida plain
    import re
    clean = re.sub(r"\[/?[a-z_ ]+\]", "", msg)
    print(clean)

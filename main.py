"""
Procesador PDF — CLI interactivo y por argumentos
Uso: python main.py [--input DIR] [--output DIR] [--prueba N] [--no-zip] [--llm]
     python main.py --caratula [--input RE.pdf] [--output DIR]
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from rich.console  import Console
    from rich.table    import Table
    from rich.prompt   import Prompt, Confirm
    from rich.panel    import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    RICH = True
except ImportError:
    RICH = False

from processor import Processor, BatchResult, FileResult
from config    import DEFAULT_OUTPUT_DIR, DEFAULT_INPUT_DIR, PRUEBAS_DISPONIBLES

console = Console() if RICH else None


# ── I/O helpers ──────────────────────────────────────────────────────────────

def _print(msg: str, style: str = ""):
    if RICH:
        console.print(msg, style=style)
    else:
        import re
        print(re.sub(r"\[/?[^\]]+\]", "", msg))


def _ask(prompt: str) -> str:
    if RICH:
        return Prompt.ask(prompt, default="")
    return input(f"{prompt}: ").strip()


def _rich_ask(prompt: str) -> str:
    return Prompt.ask(f"[cyan]{prompt}[/cyan]", default="")


def _rich_print(msg: str, style: str = ""):
    console.print(msg)


def _header():
    if RICH:
        console.print(Panel.fit(
            "[bold blue]PDF Processor[/bold blue]\n"
            "[dim]Sistema de renombrado inteligente de documentos contables[/dim]",
            border_style="blue"))
    else:
        print("=" * 60)
        print("  PDF Processor — Renombrado de documentos contables")
        print("=" * 60)


def _engine_status(proc: Processor):
    if not RICH:
        return
    llm_ok = proc._engine.llm_available
    info = (
        f"[green]LLM disponible ({proc._engine._llm.__class__.__name__})[/green]"
        if llm_ok else "[yellow]Motor: regex offline[/yellow]"
    )
    console.print(f"Motor: {info}\n")


# ── Tabla de resultados ──────────────────────────────────────────────────────

def _results_table(batch: BatchResult):
    if not RICH:
        for f in batch.files:
            status = "✓" if f.ok else ("⚠" if f.needs_correction else "✗")
            print(f"  [{status}] {f.src.name} → {f.new_name or f.error or '(sin nombre)'}")
        _print_summary(batch)
        return

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Archivo original", style="dim",   no_wrap=True, max_width=36)
    table.add_column("Nombre generado",  style="green", no_wrap=False)
    table.add_column("Motor",            width=14)
    table.add_column("Conf.",            width=6)
    table.add_column("Estado",           width=9)

    for f in batch.files:
        if f.ok and not f.needs_correction:
            status = "[green]✓ OK[/green]"
        elif f.needs_correction:
            status = "[yellow]⚠ INCOMPLETO[/yellow]"
        else:
            status = "[red]✗ ERROR[/red]"

        table.add_row(
            f.src.name,
            f.new_name or f"[red]{f.error or '—'}[/red]",
            f.method or "-",
            f"{f.confidence:.0%}" if f.confidence else "-",
            status,
        )
        for w in f.warnings:
            table.add_row("", f"  [yellow]⚠ {w}[/yellow]", "", "", "")

    console.print(table)
    _print_summary(batch)


def _print_summary(batch: BatchResult):
    pending = len(batch.pending_correction)
    parts = [
        f"[green]{batch.success_count} exitosos[/green]",
        f"[red]{batch.error_count} errores[/red]",
    ]
    if pending:
        parts.append(f"[yellow]{pending} incompletos[/yellow]")
    _print("\n[bold]Resumen:[/bold] " + "  ".join(parts))
    if batch.zip_path:
        _print(f"\n[bold green]ZIP:[/bold green] {batch.zip_path}")


# ── Corrección interactiva ────────────────────────────────────────────────────

def _run_correction(proc: Processor, batch: BatchResult,
                    output_dir: Path, pack_zip: bool):
    pending = batch.pending_correction
    if not pending:
        return

    if RICH:
        if not Confirm.ask(
            f"\n[yellow]⚠  {len(pending)} archivo(s) con campos incompletos. "
            f"¿Deseas corregirlos ahora?[/yellow]",
            default=True,
        ):
            return
    else:
        resp = input(f"\n{len(pending)} archivo(s) incompletos. ¿Corregir ahora? [S/n]: ")
        if resp.strip().lower() == "n":
            return

    corrected = proc.interactive_correct(
        batch=batch,
        output_dir=output_dir,
        pack_zip=pack_zip,
        ask_fn=_rich_ask if RICH else None,
        print_fn=_rich_print if RICH else None,
    )

    if corrected:
        _print(f"\n[bold green]✓ {corrected} archivo(s) corregidos y re-empaquetados.[/bold green]")
    else:
        _print("[dim]No se realizaron correcciones.[/dim]")


# ── Carátula Requerimiento Especial RETEICA ───────────────────────────────────

def cmd_caratula(input_path=None, output_dir=None):
    from core.extractor               import PDFExtractor
    from core.requerimiento_extractor import extract_requerimiento
    from core.caratula_generator      import generar_caratula

    ask = _rich_ask if RICH else lambda p: input(f"{p}: ").strip()

    if input_path:
        pdf_path = Path(input_path)
    else:
        ruta = ask("Ruta del PDF del requerimiento")
        pdf_path = Path(ruta.strip())

    if not pdf_path.exists():
        _print(f"[red]Archivo no encontrado: {pdf_path}[/red]")
        return

    _print(f"Leyendo: [bold]{pdf_path.name}[/bold]")

    text  = PDFExtractor().extract(pdf_path)
    datos = extract_requerimiento(text)

    if not datos.contribuyente:
        _print("[red]No se pudo detectar el contribuyente. Verifica que sea un RE RETEICA.[/red]")
        return

    nombre_salida = f"Caratula RE {datos.expediente or pdf_path.stem}.pdf"
    dest_dir      = Path(output_dir or str(DEFAULT_OUTPUT_DIR))
    output_path   = dest_dir / nombre_salida

    generar_caratula(datos, output_path)

    _print(f"\n[green]Carátula generada:[/green] {output_path}")
    _print(f"  Contribuyente: {datos.contribuyente}")
    _print(f"  NIT:           {datos.nit}")
    _print(f"  Expediente:    {datos.expediente}")

    return output_path


# ── Modo interactivo ──────────────────────────────────────────────────────────

def _interactive(proc: Processor):
    _header()
    _engine_status(proc)

    modo = _ask(
        "[cyan]Modo[/cyan]: [1] Renombrar PDFs  [2] Carátula Requerimiento RETEICA  (Enter=1)"
    ).strip()

    if modo == "2":
        cmd_caratula()
        return

    input_dir = Path(
        _ask(f"[cyan]Carpeta con PDFs[/cyan] (default: {DEFAULT_INPUT_DIR})")
        or str(DEFAULT_INPUT_DIR)
    )
    if not input_dir.exists():
        _print(f"[red]La carpeta '{input_dir}' no existe.[/red]")
        return

    pdfs = list(input_dir.glob("*.pdf"))
    if not pdfs:
        _print("[red]No se encontraron PDFs.[/red]")
        return

    _print(f"\nEncontrados: [bold]{len(pdfs)}[/bold] PDFs\n")

    prueba_str = _ask(
        f"[cyan]Número de prueba[/cyan] {PRUEBAS_DISPONIBLES} (Enter = auto-detectar)"
    )
    prueba = int(prueba_str) if prueba_str.strip().isdigit() else None

    output_dir = Path(
        _ask(f"[cyan]Carpeta de salida[/cyan] (default: {DEFAULT_OUTPUT_DIR})")
        or str(DEFAULT_OUTPUT_DIR)
    )

    pack = (
        Confirm.ask("¿Empaquetar en ZIP?", default=True)
        if RICH else input("¿ZIP? [S/n]: ").lower() != "n"
    )

    _print("\n[bold]Procesando...[/bold]\n")

    if RICH:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                      BarColumn(), TaskProgressColumn(), console=console) as prog:
            task = prog.add_task("Procesando PDFs", total=len(pdfs))

            def on_progress(current, total, fr):
                mark = (
                    "[green]✓[/green]" if (fr.ok and not fr.needs_correction)
                    else ("[yellow]⚠[/yellow]" if fr.needs_correction else "[red]✗[/red]")
                )
                prog.update(task, advance=1,
                            description=f"{mark} {fr.src.name[:42]}")

            batch = proc.process_batch(
                input_dir=input_dir, prueba=prueba,
                output_dir=output_dir, pack_zip=pack,
                on_progress=on_progress)
    else:
        batch = proc.process_batch(
            input_dir=input_dir, prueba=prueba,
            output_dir=output_dir, pack_zip=pack)

    _print("")
    _results_table(batch)
    _run_correction(proc, batch, output_dir, pack)


# ── Modo CLI directo ──────────────────────────────────────────────────────────

def _cli(args):
    proc = Processor(force_llm=args.llm)
    _header()
    _engine_status(proc)

    input_path = Path(args.input)
    output_dir = Path(args.output)
    pack       = not args.no_zip

    if not input_path.exists():
        _print(f"[red]La carpeta '{input_path}' no existe.[/red]")
        sys.exit(1)

    batch = proc.process_batch(
        input_dir=input_path, prueba=args.prueba,
        output_dir=output_dir, pack_zip=pack)

    _results_table(batch)
    _run_correction(proc, batch, output_dir, pack)

    if batch.error_count > 0 and not batch.pending_correction:
        sys.exit(1)


# ── Entrada ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PDF Processor — Renombrado inteligente de documentos contables")
    parser.add_argument("--input",    "-i", default=None,
                        help="Carpeta de PDFs (renombrar) o ruta del RE.pdf (--caratula)")
    parser.add_argument("--output",   "-o", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--prueba",   "-p", type=int, default=None,
                        choices=PRUEBAS_DISPONIBLES)
    parser.add_argument("--no-zip",   action="store_true")
    parser.add_argument("--llm",      action="store_true")
    parser.add_argument("--caratula", action="store_true",
                        help="Generar carátula de un Requerimiento Especial RETEICA")
    args = parser.parse_args()

    if args.caratula:
        cmd_caratula(input_path=args.input, output_dir=args.output)
        return

    proc = Processor(force_llm=args.llm)

    if args.input:
        _cli(args)
    else:
        if RICH:
            _interactive(proc)
        else:
            _print("Instala 'rich' para el modo interactivo: pip install rich")
            _print("Uso: python main.py --input ./pdfs --prueba 4")
            sys.exit(1)


if __name__ == "__main__":
    main()
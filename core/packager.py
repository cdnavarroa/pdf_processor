import shutil
import zipfile
from pathlib import Path
from datetime import datetime


class Packager:

    def to_zip(
        self,
        files: list[tuple[Path, str]],   # (src_path, nombre_destino)
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for src, name in files:
                if src.exists():
                    zf.write(src, arcname=name)
        return output_path

    def to_folder(
        self,
        files: list[tuple[Path, str]],
        output_dir: Path,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        result = []
        for src, name in files:
            if src.exists():
                dest = output_dir / name
                shutil.copy2(src, dest)
                result.append(dest)
        return result

    def zip_name(self, prueba: int) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"PRUEBA_{prueba}_{ts}.zip"

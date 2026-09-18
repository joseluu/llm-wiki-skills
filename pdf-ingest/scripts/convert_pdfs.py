import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

SKILL_DIR = Path(__file__).resolve().parent.parent

# HF_CACHE_DIR est machine-specifique (chemin vers le cache de modeles
# docling, pas verse dans git) -> defini dans .env a cote de SKILL.md,
# voir .env.template.
load_dotenv(SKILL_DIR / ".env")
HF_CACHE_DIR = os.environ.get("HF_CACHE_DIR")
if not HF_CACHE_DIR:
    sys.exit(
        f"HF_CACHE_DIR non defini. Copier {SKILL_DIR / '.env.template'} "
        f"vers {SKILL_DIR / '.env'} et adapter le chemin."
    )

# Must be set before importing huggingface_hub / docling, since the cache
# location is resolved from env vars at import time.
os.environ.setdefault("HF_HOME", HF_CACHE_DIR)
# Limit torch/OpenMP thread pools: on a memory-constrained machine, running
# a single-threaded pipeline avoids extra per-thread buffer allocations.
os.environ.setdefault("OMP_NUM_THREADS", "1")


def convert_one(pdf_path: Path, out_path: Path) -> None:
    import torch

    torch.set_num_threads(1)
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    markdown = result.document.export_to_markdown()
    out_path.write_text(markdown, encoding="utf-8")


def convert_dir(input_dir: Path, output_dir: Path) -> None:
    pdf_files = sorted(input_dir.glob("*.pdf"), key=lambda p: p.stat().st_size)
    if not pdf_files:
        print(f"Aucun PDF trouve dans {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    ok, failed = 0, []
    for pdf_path in pdf_files:
        out_path = output_dir / (pdf_path.stem + ".md")
        print(f"[{pdf_path.name}] conversion...")
        # Each file runs in its own subprocess so model/page memory is
        # fully released by the OS between files (avoids accumulating
        # peak memory across a long-lived batch run).
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--single",
                str(pdf_path),
                str(out_path),
            ]
        )
        if proc.returncode == 0 and out_path.exists():
            print(f"[{pdf_path.name}] OK -> {out_path}")
            ok += 1
        else:
            print(f"[{pdf_path.name}] ECHEC (code {proc.returncode})")
            failed.append(pdf_path.name)

    print(f"\nTermine: {ok}/{len(pdf_files)} conversions reussies.")
    if failed:
        print("Echecs: " + ", ".join(failed))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--single":
        convert_one(Path(sys.argv[2]), Path(sys.argv[3]))
        sys.exit(0)

    if len(sys.argv) != 3:
        print("Usage: python convert_pdfs.py <repertoire_pdf> <repertoire_sortie_md>")
        sys.exit(1)

    convert_dir(Path(sys.argv[1]), Path(sys.argv[2]))

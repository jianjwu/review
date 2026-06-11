"""Clean stale generated SolidWorks artifacts by filename prefix.

This utility is intentionally scoped to generated CAD/export extensions and
matching name prefixes. It leaves source scripts and unrelated user files alone.
"""

from __future__ import annotations

import argparse
from pathlib import Path


GENERATED_EXTENSIONS = {
    ".sldprt",
    ".sldasm",
    ".slddrw",
    ".pdf",
    ".dwg",
    ".dxf",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".step",
    ".stp",
    ".iges",
    ".igs",
    ".stl",
}


def _norm(path: Path) -> str:
    try:
        return str(path.resolve()).lower()
    except OSError:
        return str(path).lower()


def _matches_prefix(path: Path, prefixes: list[str]) -> bool:
    name = path.name
    stem = path.stem
    if name.startswith("~$"):
        name = name[2:]
        stem = Path(name).stem
    return any(stem.startswith(prefix) or name.startswith(prefix) for prefix in prefixes)


def iter_cleanup_candidates(output_dir: Path, prefixes: list[str], keep: list[Path] | None = None):
    keep_set = {_norm(path) for path in (keep or [])}
    for path in output_dir.rglob("*"):
        if path.is_dir() or _norm(path) in keep_set or path.name == ".gitkeep":
            continue
        is_lock_file = path.name.startswith("~$")
        if not is_lock_file and path.suffix.lower() not in GENERATED_EXTENSIONS:
            continue
        if _matches_prefix(path, prefixes):
            yield path


def cleanup_generated_artifacts(
    output_dir: str | Path,
    prefixes: list[str],
    keep: list[str | Path] | None = None,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prefixes = [str(prefix) for prefix in prefixes if str(prefix)]
    keep_paths = [Path(path) for path in (keep or [])]
    candidates = sorted(iter_cleanup_candidates(output_dir, prefixes, keep_paths), key=lambda p: str(p).lower())

    removed: list[str] = []
    skipped: list[str] = []
    for path in candidates:
        rel = str(path.relative_to(output_dir))
        if dry_run:
            print(f"[cleanup] would remove: {rel}")
            removed.append(rel)
            continue
        try:
            path.unlink()
            print(f"[cleanup] removed: {rel}")
            removed.append(rel)
        except FileNotFoundError:
            continue
        except PermissionError as exc:
            print(f"[cleanup] skipped locked file: {rel} ({exc})")
            skipped.append(rel)

    return {"removed": removed, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean generated SolidWorks outputs by prefix.")
    parser.add_argument("output_dir", help="Root output directory, usually outputs/solidworks")
    parser.add_argument("prefix", nargs="+", help="Generated model prefix or prefixes to clean")
    parser.add_argument("--keep", action="append", default=[], help="Path to keep; may be repeated")
    parser.add_argument("--dry-run", action="store_true", help="List matching files without deleting")
    args = parser.parse_args()

    result = cleanup_generated_artifacts(args.output_dir, args.prefix, args.keep, args.dry_run)
    print(f"[cleanup] matched={len(result['removed']) + len(result['skipped'])} skipped={len(result['skipped'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

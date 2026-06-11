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


def _norm(path):
    try:
        return str(Path(path).resolve()).lower()
    except Exception:
        return str(path).lower()


def _read_member(obj, name):
    member = getattr(obj, name, None)
    if not callable(member):
        return member
    try:
        return member()
    except Exception:
        return member


def _unwrap_com_result(result):
    if isinstance(result, (list, tuple)):
        return result[0] if result else None
    return result


def _matches_stem(path, stems):
    name = path.name
    stem = path.stem
    if name.startswith("~$"):
        name = name[2:]
        stem = Path(name).stem
    return any(stem.startswith(prefix) or name.startswith(prefix) for prefix in stems)


def _close_open_document(sw_app, path):
    if sw_app is None:
        return False

    doc = None
    try:
        doc = _unwrap_com_result(sw_app.GetOpenDocumentByName(str(path)))
    except Exception:
        doc = None

    titles = []
    if doc is not None:
        title = _read_member(doc, "GetTitle")
        if title:
            titles.append(str(title))

    titles.extend([path.name, path.stem])
    for title in dict.fromkeys(titles):
        try:
            sw_app.CloseDoc(title)
            print(f"[cleanup] closed open SolidWorks document: {title}")
            return True
        except Exception:
            continue

    return False


def cleanup_generated_artifacts(output_dir, stems, keep=None, sw_app=None):
    """Delete stale SolidWorks outputs for the requested generated model prefixes.

    The cleanup is intentionally scoped to generated CAD/export file extensions and
    matching name prefixes, so source scripts and unrelated user files are left alone.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stems = [str(stem) for stem in stems if str(stem)]
    keep_set = {_norm(path) for path in (keep or [])}
    candidates = []

    for path in output_dir.rglob("*"):
        if path.is_dir() or _norm(path) in keep_set:
            continue
        if path.name == ".gitkeep":
            continue
        is_lock_file = path.name.startswith("~$")
        if not is_lock_file and path.suffix.lower() not in GENERATED_EXTENSIONS:
            continue
        if _matches_stem(path, stems):
            candidates.append(path)

    for path in sorted(candidates, key=lambda p: p.name.lower()):
        if not path.name.startswith("~$"):
            _close_open_document(sw_app, path)

    removed = []
    skipped = []
    for path in sorted(candidates, key=lambda p: p.name.lower()):
        try:
            path.unlink()
            removed.append(path.name)
            print(f"[cleanup] removed stale generated file: {path.name}")
        except FileNotFoundError:
            continue
        except PermissionError as exc:
            skipped.append((path.name, str(exc)))
            print(f"[cleanup] skipped locked file: {path.name} ({exc})")

    return {"removed": removed, "skipped": skipped}

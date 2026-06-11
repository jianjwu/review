# Output Management

Keep SolidWorks outputs searchable and avoid redundant files.

## Folder Layout

Use `outputs/solidworks/` by default:

- `scripts/`: Python, PowerShell, VBA, and macro build/export scripts.
- `models/`: `.SLDPRT` and `.SLDASM`.
- `drawings/`: `.SLDDRW`.
- `images/`: previews and rendered images.
- `exports/`: PDF, DWG, DXF, STEP, IGES, STL, and other exchange files.

## Cleanup Before Regeneration

Before rerunning a modeling or drawing-generation command, clean stale generated artifacts for the same model prefix across `outputs/solidworks/`.

Delete matching generated files only:

- `.SLDPRT`, `.SLDASM`, `.SLDDRW`
- `.pdf`, `.dwg`, `.dxf`
- `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`
- `.step`, `.stp`, `.iges`, `.igs`, `.stl`
- SolidWorks `~$` lock files only when they are stale or can be closed safely.

Do not delete source scripts or unrelated user files.

## Naming

Use a stable prefix for all artifacts produced by one build:

- Model: `models/<prefix>.SLDPRT`
- Drawing: `drawings/<prefix>_GB.SLDDRW`
- Images: `images/<prefix>_front.png`, `images/<prefix>_iso.png`
- Exports: `exports/<prefix>.pdf`, `exports/<prefix>.dwg`, `exports/<prefix>.step`

Pass that same prefix to the cleanup script before regeneration.

## Script Use

This skill includes `scripts/cleanup_solidworks_outputs.py`. Prefer the workspace cleanup script if the current project already has one, because it may include project-specific behavior. Otherwise use this bundled script.

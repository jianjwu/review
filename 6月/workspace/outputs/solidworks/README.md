# SolidWorks Outputs

Generated SolidWorks artifacts are grouped by file type:

- `scripts/`: Python, PowerShell, and VBA build/export scripts.
- `models/`: SolidWorks part and assembly models (`.SLDPRT`, `.SLDASM`).
- `drawings/`: SolidWorks drawing files (`.SLDDRW`).
- `images/`: Preview and rendered images.
- `exports/`: Exchange/review exports such as PDF, DWG, DXF, STEP, IGES, and STL.

Build scripts clean stale generated artifacts for the same model prefix before regenerating outputs.

## Drawing-Based Modeling Checklist

Before building from an engineering drawing, create a short confirmation table:

- Base datums and coordinate system: origin, center axis, front/top/right reference planes.
- Part type: revolved, non-revolved, or hybrid; choose revolve when a stable axis and radial section define the main body.
- Main-body method: revolve for shafts/flanges/sleeves, extrusion only for non-axisymmetric bases.
- Axial section order: every diameter, length, shoulder, groove, and bore from left to right.
- Hole table: count, diameter, through/blind, counterbore/countersink, depth, PCD, angle, start face.
- Boss/protrusion table: center, diameter/profile, start plane, direction, height/depth, merge behavior.
- Pattern/symmetry table: seed feature, circular/linear/mirror type, axis or mirror plane, count, spacing/angle, PCD if applicable, and merge/scope behavior.
- Key/keyway table: key type, shaft or hub/internal keyway, width, depth, length, end style, radius/chamfer, angular orientation, distance from shoulders/end faces, and referenced standard if present.
- Unclear items: stop and ask before modeling if they affect topology, fit, hole position, or extrusion direction.
- Verification: export front/top/isometric previews after major feature groups and compare against the drawing before continuing.

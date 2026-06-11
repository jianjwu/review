---
name: solidworks-ai-modeling
description: SolidWorks AI modeling workflow for natural-language part requests, engineering drawings, drawing-to-model tasks, GB/SW2022 part creation, holes, bosses, keyways, feature patterns, cleanup, organized outputs, and verification through a local SolidWorks MCP/COM bridge. Use when Codex must analyze drawings first, ask about unclear topology-driving dimensions, build or revise SolidWorks parts/drawings, export CAD artifacts, or inspect generated SolidWorks models.
---

# SolidWorks AI Modeling

## Core Workflow

Use this workflow before any SolidWorks modeling, drawing-generation, or CAD export task.

1. Read workspace instructions first, especially `AGENTS.md` when present.
2. Treat `solidworks_mcp` as a local Windows/SolidWorks COM bridge. Do not use WSL for real CAD operations.
3. Use millimeters by default unless the user explicitly asks for another unit.
4. For SW2022 part creation, pass `C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot` when a `create_part` tool call accepts a template path.
5. Convert natural-language part requests into a short ordered build plan before calling CAD tools.
6. Save generated artifacts under `outputs/solidworks/` unless the user gives another path, using `scripts/`, `models/`, `drawings/`, `images/`, and `exports/`.
7. Before rerunning a build or drawing command, delete stale generated artifacts for the same model prefix. Use `scripts/cleanup_solidworks_outputs.py` in this skill or the workspace cleanup utility if one already exists.
8. Before planning features, classify the part as revolved, non-revolved, or hybrid. If the main body has a stable axis and can be made from a radial section, use a revolve feature for the base instead of forcing many extrudes.
9. Define the modeling sequence from stable references: origin/axis and primary datums first, main body second, secondary bosses third, cuts and holes fourth, patterns fifth, chamfers/fillets last.
10. Build in small verified steps: create/open model, create sketch, add constrained geometry, create feature, inspect state, then continue.
11. After every mutating CAD tool call, read back model state with tools such as `get_model_info`, `list_features`, `get_mass_properties`, `export_image`, rebuild status, or an equivalent inspection.

Prefer parametric feature creation over one-shot macro execution. Use macros only when a repeated operation is too awkward through direct tools.

## Drawing First

For drawing-based modeling, do not begin geometry immediately. First produce a dimension and feature extraction table, then ask about unclear topology-driving items before building.

Read `references/drawing-modeling-checklist.md` when the input is an engineering drawing, PDF, screenshot, or image. Extract base datums, main body, axial lengths, diameters, hole counts, pitch-circle diameters, angular positions, boss directions, cut depths, tolerances, standards, and unclear items.

Stop and ask the user when an unclear value affects topology, fit, feature position, or extrusion direction. Approximate only noncritical cosmetic details, and label them as assumptions.

## Feature Strategy

Read `references/mechanical-feature-rules.md` when the model includes shafts, flanges, sleeves, bolt circles, repeated holes, slots, ribs, bosses, gears, keyways, or symmetric geometry.

Use this modeling order:

1. Origin, center axis, and primary datums.
2. Part-type classification: revolved, non-revolved, or hybrid, with the chosen main-body method.
3. Main revolved or extruded base.
4. Secondary bosses, pads, sleeves, ribs, and local protrusions.
5. Holes, cuts, slots, grooves, bores, counterbores, countersinks, and keyways.
6. Circular patterns, linear patterns, mirrors, or sketch patterns.
7. Chamfers, fillets, cosmetic threads, annotations, drawings, and exports.

For shafts, flanges, sleeves, pulleys, gears, bushings, and other axisymmetric parts, create the main body from a revolved section around a named center axis whenever possible. Add holes, keyways, slots, bolt circles, and local bosses only after the revolved base has been inspected.

Use feature patterns and symmetry deliberately. For repeated holes, slots, ribs, teeth, grooves, and bosses, create one fully defined seed feature and then use circular pattern, linear pattern, mirror, or sketch pattern from stable axes/planes instead of manually duplicating geometry. Prefer feature-level patterns over sketch-level duplication when it keeps the model tree easier to edit.

Before patterning, confirm the pattern definition: count, spacing or pitch-circle diameter, angular increment, pattern axis/plane, seed orientation, and whether geometry should merge. Inspect the patterned result immediately after creation.

For every boss, extrude, and cut, explicitly state and verify the start plane, direction, depth/end condition, and whether it adds or removes material. After creating an axial boss or sleeve, inspect an isometric or section-like preview to catch reverse-direction features.

## Keyways

For keyways and key-seat features, identify the key type before modeling:

- Parallel key.
- Woodruff key.
- Taper key.
- Spline or keyed bore.
- Shaft keyseat.
- Hub/internal keyway.

Confirm width, depth, length, end shape, fillet/chamfer, angular orientation, distance from shoulders/end faces, and whether dimensions apply to the key or to the cut feature. Use standard key/keyway proportions only when the drawing references a standard or the user confirms the standard.

## Output Management

Read `references/output-management.md` when creating scripts, regenerating models, producing drawings, exporting PDF/DWG/images/STEP/STL, or cleaning old results.

Use stable model prefixes. For example, rerunning `spur_gear_z20_m1_pa20_b8_bore4` should clean old files matching that prefix across `outputs/solidworks/` before writing the new model, drawing, previews, and exports.

## Failure Handling

Stop and report the exact tool or COM error when SolidWorks is not running, COM is unavailable, a sketch is underdefined in a way that blocks modeling, a feature rebuild fails, or a generated model cannot be saved/exported.

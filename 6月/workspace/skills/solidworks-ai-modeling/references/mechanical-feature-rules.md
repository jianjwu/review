# Mechanical Feature Rules

Use these rules to reduce modeling errors and keep the feature tree editable.

## Main Body

- Classify the part before modeling: revolved, non-revolved, or hybrid.
- Choose revolved when a stable axis exists and the main outside/inside profile is defined by diameters, radii, tapers, grooves, shoulders, or axial lengths.
- Choose non-revolved extrusion when the base is mainly a plate, block, bracket, housing, ribbed frame, or irregular prismatic outline with no dominant axis.
- Choose hybrid when the base is revolved but local lugs, bosses, ears, ribs, holes, keyways, slots, flats, or cutouts are added afterward.
- Use a revolved section for axisymmetric shafts, sleeves, flanges, pulleys, gears, bushings, and stepped parts.
- Name or clearly define the center axis before using revolve, circular pattern, or angular dimensions.
- Use extrusion for genuinely non-axisymmetric bases, plates, ribs, and prismatic housings.
- Inspect the main body before adding holes or local features.

## Bosses, Extrudes, and Cuts

For every boss, extrude, and cut, explicitly track:

- Start plane or face.
- Direction vector or side.
- Depth/end condition.
- Add material or remove material.
- Merge behavior or feature scope.

For axial bosses and sleeves, inspect an isometric or section-like preview immediately to catch reverse-direction features.

## Patterns and Symmetry

Use one fully defined seed feature, then pattern or mirror it.

- Circular pattern: bolt holes, teeth, radial grooves, repeated bosses, radial slots.
- Linear pattern: hole rows, repeated slots, ribs, fins.
- Mirror: symmetric bosses, holes, ribs, pockets, and slots across a stable plane.
- Sketch pattern: acceptable for simple repeated sketch entities, but prefer feature-level patterns when it improves editability.

Before patterning, confirm count, spacing or angle, pitch-circle diameter if relevant, axis or mirror plane, seed orientation, and merge/scope behavior.

## Holes

Prefer Hole Wizard or parametric hole features when available. Track hole type, diameter, depth, counterbore/countersink, thread callout, start face, and position references.

For bolt circles, confirm count, PCD, first-hole angle, equal spacing, and whether holes pass through all bodies.

## Keyways

Identify the key type before modeling:

- Parallel key.
- Woodruff key.
- Taper key.
- Spline or keyed bore.
- Shaft keyseat.
- Hub/internal keyway.

Confirm width, depth, length, end style, radius/chamfer, angular orientation, shoulder/end-face distances, and whether dimensions describe the key itself or the cut feature. Use standard proportions only when the drawing references a standard or the user confirms the standard.

## Gears

For straight spur gears, track tooth count, module, pressure angle, face width, bore, addendum/dedendum assumptions, keyway, hub details, chamfers, and drawing/export requirements. Use circular patterns for teeth when teeth are modeled explicitly; use simplified/cosmetic representation only when acceptable for the purpose.

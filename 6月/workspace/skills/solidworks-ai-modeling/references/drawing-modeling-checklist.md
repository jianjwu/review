# Drawing-Based Modeling Checklist

Use this before creating geometry from an engineering drawing, PDF, screenshot, or photo.

## Extraction Table

Create a short table with these rows:

- Source and scale: drawing file/page/view used, units, any scale assumptions.
- Base datums: origin, center axis, front/top/right reference planes, symmetry planes.
- Part type: revolved, non-revolved, or hybrid; explain why the main body should use revolve, extrusion, sweep, loft, or another method.
- Main body: revolve/extrude choice, profile, total length/thickness, main diameters/widths.
- Axial order: every diameter, length, shoulder, groove, bore, and end face from left to right.
- Hole table: count, diameter, through/blind, counterbore/countersink, depth, pitch-circle diameter, angular position, start face.
- Boss/protrusion table: center, diameter/profile, start plane, direction, height/depth, merge behavior.
- Cuts/slots/grooves: profile size, reference edges, depth/end condition, through direction.
- Pattern/symmetry: seed feature, circular/linear/mirror type, axis or plane, count, spacing/angle, PCD, merge/scope behavior.
- Key/keyway: key type, shaft or hub/internal keyway, width, depth, length, end style, fillet/chamfer, angular orientation, shoulder/end-face distances, referenced standard.
- Tolerances/standards: fits, threads, surface roughness, heat treatment, material, GB/ISO/DIN references.
- Unclear items: each ambiguity, why it matters, and the exact confirmation needed.

## Ask Before Modeling

Ask for confirmation before modeling when any of these are unclear:

- Whether the part is primarily a revolved body, a prismatic/non-revolved body, or a hybrid body.
- Hole location, PCD, angle, count, depth, or start face.
- Boss center, height, protrusion direction, or whether it merges.
- Axial step order or whether a shoulder belongs before/after another feature.
- Extrude/revolve start plane, direction, end condition, or cut versus protrusion.
- Key/keyway type, dimensions, position, end form, or applicable standard.
- Pattern count, spacing, pitch circle, axis/plane, or seed orientation.
- Any value that changes topology, mating behavior, fit, or manufacturing intent.

## Verification Gates

After each major feature group, export or inspect at least one useful view:

- Main body: front/section-like or isometric preview.
- Holes and bosses: top/front views showing positions.
- Patterns/mirrors: view normal to pattern plane plus isometric.
- Keyways/slots: view showing width, depth, and end shape.

Compare against the drawing before continuing.

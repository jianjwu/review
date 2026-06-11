import math
from pathlib import Path

import pythoncom
import win32com.client

from solidworks_output_cleanup import cleanup_generated_artifacts


TEMPLATE_PATH = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot"
OUTPUT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = OUTPUT_DIR / "models"
IMAGES_DIR = OUTPUT_DIR / "images"
PART_PATH = MODELS_DIR / "spur_gear_z20_m1_pa20_b8_bore4.SLDPRT"
PNG_PATH = IMAGES_DIR / "spur_gear_z20_m1_pa20_b8_bore4.png"
PNG_FRONT_PATH = IMAGES_DIR / "spur_gear_z20_m1_pa20_b8_bore4_front.png"


def mm(value):
    return value / 1000.0


def flag_methods(obj, interface):
    try:
        from solidworks_mcp.adapters import sw_type_info

        sw_type_info.flag_methods(obj, interface)
    except Exception:
        pass


def read_member(obj, name):
    member = getattr(obj, name, None)
    if not callable(member):
        return member
    try:
        return member()
    except Exception:
        return member


def iter_features(model, limit=500):
    flag_methods(model, "IModelDoc2")
    feat = read_member(model, "FirstFeature")
    count = 0
    while feat is not None and count < limit:
        flag_methods(feat, "IFeature")
        yield feat
        feat = read_member(feat, "GetNextFeature")
        count += 1


def feature_rows(model):
    rows = []
    for feat in iter_features(model):
        try:
            rows.append((str(read_member(feat, "Name")), str(read_member(feat, "GetTypeName2"))))
        except Exception:
            continue
    return rows


def mass_summary(model):
    try:
        mass_props = model.Extension.CreateMassProperty()
        if mass_props:
            return (
                f"volume={mass_props.Volume * 1e9:.3f} mm^3, "
                f"surface_area={mass_props.SurfaceArea * 1e6:.3f} mm^2, "
                f"mass={mass_props.Mass:.6g} kg"
            )
    except Exception:
        pass

    try:
        raw = read_member(model, "GetMassProperties")
        if isinstance(raw, (list, tuple)) and len(raw) >= 6:
            return (
                f"volume={raw[3] * 1e9:.3f} mm^3, "
                f"surface_area={raw[4] * 1e6:.3f} mm^2, "
                f"mass={raw[5]:.6g} kg"
            )
    except Exception:
        pass

    return "unavailable"


def print_state(model, label):
    print(f"\n[{label}]")
    print(f"ActiveDoc: {read_member(model, 'GetTitle')}")
    for i, (name, type_name) in enumerate(feature_rows(model)[:80]):
        print(f"  {i:02d} {name} ({type_name})")
    print(f"  Mass properties: {mass_summary(model)}")


def select_named_plane(model, candidates):
    model.ClearSelection2(True)
    for name in candidates:
        feat = model.FeatureByName(name)
        if feat is not None and feat.Select2(False, 0):
            return feat
    raise RuntimeError(f"Failed to select plane. Tried: {', '.join(candidates)}")


def add_profile_point(sketch_manager, state, x_mm, y_mm):
    if not state["has_point"]:
        state.update(
            {
                "has_point": True,
                "first_x": x_mm,
                "first_y": y_mm,
                "prev_x": x_mm,
                "prev_y": y_mm,
            }
        )
        return

    dx = x_mm - state["prev_x"]
    dy = y_mm - state["prev_y"]
    if math.hypot(dx, dy) <= 1e-6:
        return

    sketch_manager.CreateLine(
        mm(state["prev_x"]),
        mm(state["prev_y"]),
        0.0,
        mm(x_mm),
        mm(y_mm),
        0.0,
    )
    state["prev_x"] = x_mm
    state["prev_y"] = y_mm


def close_profile(sketch_manager, state):
    dx = state["first_x"] - state["prev_x"]
    dy = state["first_y"] - state["prev_y"]
    if math.hypot(dx, dy) > 1e-6:
        sketch_manager.CreateLine(
            mm(state["prev_x"]),
            mm(state["prev_y"]),
            0.0,
            mm(state["first_x"]),
            mm(state["first_y"]),
            0.0,
        )


def create_spur_profile_sketch(model):
    select_named_plane(model, ["Front Plane", "前视基准面", "前基准面"])
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.AddToDB = True

    z = 20
    m = 1.0
    alpha = math.radians(20.0)
    rp = z * m / 2.0
    ra = rp + m
    rf = rp - 1.25 * m
    rb = rp * math.cos(alpha)
    pitch = 2.0 * math.pi / z
    half_tooth = math.pi / (2.0 * z)
    tp = math.sqrt((rp / rb) ** 2 - 1.0)
    psi_p = tp - math.atan(tp)
    ta = math.sqrt((ra / rb) ** 2 - 1.0)
    psi_a = ta - math.atan(ta)

    state = {"has_point": False}
    flank_segments = 10
    top_segments = 3
    root_segments = 3

    for k in range(z):
        c = k * pitch
        minus_root = c - half_tooth - psi_p
        plus_root = c + half_tooth + psi_p
        minus_tip = c - half_tooth - psi_p + psi_a
        plus_tip = c + half_tooth + psi_p - psi_a

        if k == 0:
            add_profile_point(sm, state, rf * math.cos(minus_root), rf * math.sin(minus_root))

        add_profile_point(sm, state, rb * math.cos(minus_root), rb * math.sin(minus_root))

        for j in range(1, flank_segments + 1):
            t = ta * j / flank_segments
            radius = rb * math.sqrt(1.0 + t * t)
            psi = t - math.atan(t)
            angle = c - half_tooth - psi_p + psi
            add_profile_point(sm, state, radius * math.cos(angle), radius * math.sin(angle))

        for j in range(1, top_segments + 1):
            angle = minus_tip + (plus_tip - minus_tip) * j / top_segments
            add_profile_point(sm, state, ra * math.cos(angle), ra * math.sin(angle))

        for j in range(flank_segments - 1, -1, -1):
            t = ta * j / flank_segments
            radius = rb * math.sqrt(1.0 + t * t)
            psi = t - math.atan(t)
            angle = c + half_tooth + psi_p - psi
            add_profile_point(sm, state, radius * math.cos(angle), radius * math.sin(angle))

        add_profile_point(sm, state, rf * math.cos(plus_root), rf * math.sin(plus_root))

        next_minus_root = (k + 1) * pitch - half_tooth - psi_p
        for j in range(1, root_segments + 1):
            angle = plus_root + (next_minus_root - plus_root) * j / root_segments
            add_profile_point(sm, state, rf * math.cos(angle), rf * math.sin(angle))

    close_profile(sm, state)
    sm.AddToDB = False
    sm.InsertSketch(True)
    print("Created 20-tooth spur involute profile sketch")


def last_profile_name(model):
    profiles = [name for name, type_name in feature_rows(model) if type_name == "ProfileFeature"]
    if not profiles:
        raise RuntimeError("No profile sketch found.")
    return profiles[-1]


def create_extruded_body(model, sketch_name):
    model.ClearSelection2(True)
    feat = model.FeatureByName(sketch_name)
    if feat is None or not feat.Select2(False, 0):
        raise RuntimeError(f"Failed to select spur profile sketch: {sketch_name}")

    feature = model.FeatureManager.FeatureExtrusion2(
        True,
        False,
        False,
        0,
        0,
        mm(8.0),
        0.0,
        False,
        False,
        False,
        False,
        0.0,
        0.0,
        False,
        False,
        False,
        False,
        True,
        False,
        True,
        0,
        0.0,
        False,
    )
    if feature is None:
        raise RuntimeError("Failed to create 8 mm spur gear extrusion.")
    print(f"Created extrusion: {feature.Name}")


def create_center_hole(model):
    select_named_plane(model, ["Front Plane", "前视基准面", "前基准面"])
    sm = model.SketchManager
    sm.InsertSketch(True)
    circle = sm.CreateCircleByRadius(0.0, 0.0, 0.0, mm(2.0))
    if circle is None:
        raise RuntimeError("Failed to create 4 mm bore circle.")
    sm.InsertSketch(True)
    hole_sketch = last_profile_name(model)

    for api_name in ("FeatureCut4", "FeatureCut3"):
        for reverse in (False, True):
            model.ClearSelection2(True)
            feat = model.FeatureByName(hole_sketch)
            if feat is None or not feat.Select2(False, 0):
                raise RuntimeError(f"Failed to select bore sketch for cut: {hole_sketch}")

            if api_name == "FeatureCut4":
                feature = model.FeatureManager.FeatureCut4(
                    True,
                    False,
                    reverse,
                    1,
                    0,
                    mm(10.0),
                    0.0,
                    False,
                    False,
                    False,
                    False,
                    0.0,
                    0.0,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    0,
                    0.0,
                    False,
                    False,
                )
            else:
                feature = model.FeatureManager.FeatureCut3(
                    True,
                    reverse,
                    False,
                    1,
                    0,
                    mm(10.0),
                    mm(10.0),
                    False,
                    False,
                    False,
                    False,
                    0.0,
                    0.0,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    0,
                    0.0,
                    False,
                )

            if feature is not None:
                print(f"Created center hole cut: {feature.Name}")
                return

    raise RuntimeError("Failed to create 4 mm through center hole.")


def hide_features(model, type_names):
    model.ClearSelection2(True)
    selected = 0
    for name, type_name in feature_rows(model):
        if type_name in type_names:
            feat = model.FeatureByName(name)
            if feat is not None and feat.Select2(selected > 0, 0):
                selected += 1
    if selected:
        try:
            if "ProfileFeature" in type_names:
                model.BlankSketch()
        except Exception:
            pass
        try:
            if "RefPlane" in type_names:
                model.BlankRefGeom()
        except Exception:
            pass
    model.ClearSelection2(True)


def save_part(model):
    PART_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PART_PATH.exists():
        PART_PATH.unlink()
    result = model.SaveAs3(str(PART_PATH), 0, 0)
    if not PART_PATH.exists():
        raise RuntimeError(f"SaveAs3 did not write part file: {PART_PATH}; result={result}")
    print(f"Saved part: {PART_PATH}")


def save_view(model, path, view_const):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    try:
        model.ShowNamedView2("", view_const)
    except Exception:
        pass
    try:
        model.ViewDisplayShaded()
    except Exception:
        pass
    try:
        model.ViewZoomToFit2()
    except Exception:
        pass
    model.SaveAs3(str(path), 0, 2)
    if not path.exists():
        raise RuntimeError(f"Failed to export image: {path}")
    print(f"Exported image: {path}")


def main():
    if not Path(TEMPLATE_PATH).exists():
        raise RuntimeError(f"Part template not found: {TEMPLATE_PATH}")

    pythoncom.CoInitialize()
    try:
        sw_app = win32com.client.GetActiveObject("SldWorks.Application")
        cleanup_generated_artifacts(OUTPUT_DIR, [PART_PATH.stem], sw_app=sw_app)
        model = sw_app.NewDocument(TEMPLATE_PATH, 0, 0, 0)
        if model is None:
            raise RuntimeError(f"Failed to create part from template: {TEMPLATE_PATH}")
        model.SetTitle2("spur_gear_z20_m1_pa20_b8_bore4")

        create_spur_profile_sketch(model)
        model.ForceRebuild3(False)
        profile = last_profile_name(model)
        print_state(model, "After spur profile sketch")

        create_extruded_body(model, profile)
        model.ForceRebuild3(False)
        print_state(model, "After 8 mm extrusion")

        create_center_hole(model)
        model.ForceRebuild3(False)
        print_state(model, "After 4 mm through bore")

        save_part(model)
        print_state(model, "After save")

        hide_features(model, {"ProfileFeature"})
        hide_features(model, {"RefPlane"})
        save_view(model, PNG_PATH, 7)
        save_view(model, PNG_FRONT_PATH, 1)
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()

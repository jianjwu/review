import math
from pathlib import Path

import pythoncom
import win32com.client

from solidworks_output_cleanup import cleanup_generated_artifacts


TEMPLATE_PATH = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot"
MATERIAL_DB_PATH = r"D:\SW\Crop\SOLIDWORKS\lang\chinese-simplified\sldmaterials\solidworks materials.sldmat"
MATERIAL_NAME = "AISI 1045 \u94a2\uff0c\u51b7\u62d4"
OUTPUT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = OUTPUT_DIR / "models"
IMAGES_DIR = OUTPUT_DIR / "images"
EXPORTS_DIR = OUTPUT_DIR / "exports"
PART_STEM = "driven_short_shaft_from_hand_sketch"
PART_PATH = MODELS_DIR / f"{PART_STEM}.SLDPRT"
STEP_PATH = EXPORTS_DIR / f"{PART_STEM}.step"
PNG_ISO_PATH = IMAGES_DIR / f"{PART_STEM}_iso.png"
PNG_FRONT_PATH = IMAGES_DIR / f"{PART_STEM}_front.png"


# Dimensions interpreted from the user's hand sketch. Units are millimeters.
LEFT_END_DIA = 40.0
LEFT_END_LENGTH = 55.0
COLLAR_DIA = 51.0
COLLAR_LENGTH = 40.0  # 230 - 55 - 80 - 55
MIDDLE_DIA = 45.0
MIDDLE_LENGTH = 80.0
RIGHT_END_DIA = 40.0
RIGHT_END_LENGTH = 55.0
TOTAL_LENGTH = 230.0
END_CHAMFER_DISTANCE = 2.0
END_CHAMFER_ANGLE_DEG = 45.0

# Keyseat assumption:
# - Slot begins 1 mm to the right of the Ø51 shoulder, as sketched.
# - The lower section view dimension 38 is treated as remaining diameter to
#   the flat keyseat floor, so cut depth = 45 - 38 = 7 mm.
KEYSEAT_LENGTH = 36.0
KEYSEAT_WIDTH = 14.0
KEYSEAT_START_OFFSET_FROM_COLLAR = 1.0
KEYSEAT_DEPTH = MIDDLE_DIA - 38.0
KEYSEAT_CENTER_X = LEFT_END_LENGTH + COLLAR_LENGTH + KEYSEAT_START_OFFSET_FROM_COLLAR + KEYSEAT_LENGTH / 2.0
KEYSEAT_CENTER_Y = MIDDLE_DIA / 2.0


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
    for i, (name, type_name) in enumerate(feature_rows(model)[:100]):
        print(f"  {i:02d} {name} ({type_name})")
    print(f"  Mass properties: {mass_summary(model)}")


def select_named_plane(model, candidates):
    model.ClearSelection2(True)
    for name in candidates:
        feat = model.FeatureByName(name)
        if feat is not None and feat.Select2(False, 0):
            return feat
    raise RuntimeError(f"Failed to select plane. Tried: {', '.join(candidates)}")


def select_front_plane(model):
    return select_named_plane(model, ["Front Plane", "前视基准面", "前基准面"])


def select_top_plane(model):
    return select_named_plane(model, ["Top Plane", "上视基准面", "上基准面"])


def last_profile_name(model):
    profiles = [name for name, type_name in feature_rows(model) if type_name == "ProfileFeature"]
    if not profiles:
        raise RuntimeError("No profile sketch found.")
    return profiles[-1]


def create_shaft_revolve_sketch(model):
    select_front_plane(model)
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.AddToDB = True

    r40 = LEFT_END_DIA / 2.0
    r51 = COLLAR_DIA / 2.0
    r45 = MIDDLE_DIA / 2.0
    c = END_CHAMFER_DISTANCE
    x0 = 0.0
    x1 = LEFT_END_LENGTH
    x2 = x1 + COLLAR_LENGTH
    x3 = x2 + MIDDLE_LENGTH
    x4 = TOTAL_LENGTH

    # Closed half-profile around y=0. End chamfers are included in the profile.
    points = [
        (x0, 0.0),
        (x4, 0.0),
        (x4, r40 - c),
        (x4 - c, r40),
        (x3, r40),
        (x3, r45),
        (x2, r45),
        (x2, r51),
        (x1, r51),
        (x1, r40),
        (x0 + c, r40),
        (x0, r40 - c),
    ]

    for start, end in zip(points, points[1:] + points[:1]):
        sm.CreateLine(mm(start[0]), mm(start[1]), 0.0, mm(end[0]), mm(end[1]), 0.0)

    sm.CreateCenterLine(mm(-10.0), 0.0, 0.0, mm(TOTAL_LENGTH + 10.0), 0.0, 0.0)
    sm.AddToDB = False
    sm.InsertSketch(True)

    sketch_name = last_profile_name(model)
    try:
        feat = model.FeatureByName(sketch_name)
        if feat is not None:
            feat.Name = "Shaft_Revolve_Profile"
            sketch_name = "Shaft_Revolve_Profile"
    except Exception:
        pass
    print(f"Created revolve profile sketch: {sketch_name}")
    return sketch_name


def create_revolve(model, sketch_name):
    model.ClearSelection2(True)
    sketch = model.FeatureByName(sketch_name)
    if sketch is None or not sketch.Select2(False, 0):
        raise RuntimeError(f"Failed to select revolve sketch: {sketch_name}")

    feature = model.FeatureManager.FeatureRevolve2(
        True,
        True,
        False,
        False,
        False,
        False,
        0,
        0,
        2.0 * math.pi,
        0.0,
        False,
        False,
        0.0,
        0.0,
        0,
        0.0,
        0.0,
        True,
        False,
        True,
    )
    if feature is None:
        raise RuntimeError("Failed to create revolved shaft body.")
    try:
        feature.Name = "Revolved_Stepped_Shaft"
    except Exception:
        pass
    print("Created revolve: Revolved_Stepped_Shaft")
    return feature


def create_offset_plane_from_top(model, offset_mm, feature_name):
    select_top_plane(model)
    plane = model.FeatureManager.InsertRefPlane(8, mm(offset_mm), 0, 0.0, 0, 0.0)
    if plane is None:
        raise RuntimeError(f"InsertRefPlane failed at offset {offset_mm} mm.")
    try:
        plane.Name = feature_name
    except Exception:
        pass
    model.ClearSelection2(True)
    print(f"Created reference plane: {feature_name} at {offset_mm} mm from Top Plane")
    return plane


def create_keyseat_sketch(model, plane_feature):
    if not plane_feature.Select2(False, 0):
        raise RuntimeError("Failed to select keyseat start plane.")

    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.AddToDB = True

    # Sketch lies on a plane tangent to the shaft top. Plane coordinates map to
    # shaft axial X and lateral Z, creating an obround slot footprint.
    half_straight = (KEYSEAT_LENGTH - KEYSEAT_WIDTH) / 2.0
    radius = KEYSEAT_WIDTH / 2.0
    cx = KEYSEAT_CENTER_X

    left_cx = cx - half_straight
    right_cx = cx + half_straight
    top_z = radius
    bottom_z = -radius

    sm.CreateLine(mm(left_cx), mm(top_z), 0.0, mm(right_cx), mm(top_z), 0.0)
    sm.CreateArc(mm(right_cx), 0.0, 0.0, mm(right_cx), mm(top_z), 0.0, mm(right_cx), mm(bottom_z), 0.0, -1)
    sm.CreateLine(mm(right_cx), mm(bottom_z), 0.0, mm(left_cx), mm(bottom_z), 0.0)
    sm.CreateArc(mm(left_cx), 0.0, 0.0, mm(left_cx), mm(bottom_z), 0.0, mm(left_cx), mm(top_z), 0.0, -1)

    sm.AddToDB = False
    sm.InsertSketch(True)

    sketch_name = last_profile_name(model)
    try:
        feat = model.FeatureByName(sketch_name)
        if feat is not None:
            feat.Name = "Keyseat_Obround_Profile"
            sketch_name = "Keyseat_Obround_Profile"
    except Exception:
        pass
    print(f"Created keyseat sketch: {sketch_name}")
    return sketch_name


def create_keyseat_cut(model, sketch_name):
    for api_name in ("FeatureCut4", "FeatureCut3"):
        for reverse in (False, True):
            model.ClearSelection2(True)
            sketch = model.FeatureByName(sketch_name)
            if sketch is None or not sketch.Select2(False, 0):
                raise RuntimeError(f"Failed to select keyseat sketch: {sketch_name}")
            try:
                if api_name == "FeatureCut4":
                    feature = model.FeatureManager.FeatureCut4(
                        True,
                        False,
                        reverse,
                        0,
                        0,
                        mm(KEYSEAT_DEPTH),
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
                        0,
                        0,
                        mm(KEYSEAT_DEPTH),
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
                    )
                if feature is not None:
                    try:
                        feature.Name = "Keyseat_14w_36l_7d"
                    except Exception:
                        pass
                    print("Created cut: Keyseat_14w_36l_7d")
                    return feature
            except Exception as exc:
                print(f"  {api_name} reverse={reverse} failed: {exc}")
                continue
    raise RuntimeError("Failed to create keyseat cut.")


def set_material_and_properties(model):
    try:
        config_name = model.ConfigurationManager.ActiveConfiguration.Name
        model.SetMaterialPropertyName2(config_name, MATERIAL_DB_PATH, MATERIAL_NAME)
        print(f"Assigned SolidWorks material: {MATERIAL_NAME}")
    except Exception as exc:
        print(f"SolidWorks material assignment skipped: {exc}")
    try:
        manager = model.Extension.CustomPropertyManager("")
        manager.Add3("Material", 30, "45 steel / AISI 1045 cold drawn", 2)
        manager.Add3("SolidWorks material", 30, MATERIAL_NAME, 2)
        manager.Add3("Drawing source", 30, "User hand sketch reference", 2)
        manager.Add3("Heat treatment", 30, "Quenched and tempered HB220-250, per original drawing note", 2)
        manager.Add3("Keyseat assumption", 30, "36 mm long, 14 mm wide, 7 mm deep, starts 1 mm right of Ø51 shoulder", 2)
    except Exception as exc:
        print(f"Custom properties skipped: {exc}")


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


def save_step(model):
    STEP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STEP_PATH.exists():
        STEP_PATH.unlink()
    result = model.SaveAs3(str(STEP_PATH), 0, 2)
    if not STEP_PATH.exists():
        raise RuntimeError(f"SaveAs3 did not write STEP file: {STEP_PATH}; result={result}")
    print(f"Saved STEP: {STEP_PATH}")


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
    if abs(TOTAL_LENGTH - (LEFT_END_LENGTH + COLLAR_LENGTH + MIDDLE_LENGTH + RIGHT_END_LENGTH)) > 1e-6:
        raise RuntimeError("Axial segment lengths do not add up to TOTAL_LENGTH.")
    if KEYSEAT_LENGTH <= KEYSEAT_WIDTH:
        raise RuntimeError("Obround keyseat length must exceed width.")
    if KEYSEAT_DEPTH <= 0.0:
        raise RuntimeError("Keyseat depth must be positive.")

    pythoncom.CoInitialize()
    try:
        sw_app = win32com.client.GetActiveObject("SldWorks.Application")
        cleanup_generated_artifacts(OUTPUT_DIR, [PART_STEM], sw_app=sw_app)

        model = sw_app.NewDocument(TEMPLATE_PATH, 0, 0, 0)
        if model is None:
            raise RuntimeError(f"Failed to create part from template: {TEMPLATE_PATH}")
        model.SetTitle2(PART_STEM)

        revolve_sketch = create_shaft_revolve_sketch(model)
        model.ForceRebuild3(False)
        print_state(model, "After revolve profile sketch")

        create_revolve(model, revolve_sketch)
        model.ForceRebuild3(False)
        print_state(model, "After revolved stepped shaft")

        plane = create_offset_plane_from_top(model, KEYSEAT_CENTER_Y, "Keyseat_Tangent_Start_Plane")
        keyseat_sketch = create_keyseat_sketch(model, plane)
        create_keyseat_cut(model, keyseat_sketch)
        model.ForceRebuild3(False)
        print_state(model, "After keyseat cut")

        set_material_and_properties(model)
        hide_features(model, {"ProfileFeature"})
        hide_features(model, {"RefPlane"})
        model.ForceRebuild3(False)
        print_state(model, "After hide reference geometry")

        save_part(model)
        save_step(model)
        save_view(model, PNG_ISO_PATH, 7)
        save_view(model, PNG_FRONT_PATH, 1)
        print_state(model, "Final")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()

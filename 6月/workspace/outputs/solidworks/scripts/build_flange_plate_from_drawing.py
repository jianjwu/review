import math
from pathlib import Path

import pythoncom
import win32com.client

from solidworks_output_cleanup import cleanup_generated_artifacts


TEMPLATE_PATH = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot"
OUTPUT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = OUTPUT_DIR / "models"
IMAGES_DIR = OUTPUT_DIR / "images"
PART_STEM = "flange_plate_from_drawing"
PART_PATH = MODELS_DIR / f"{PART_STEM}.SLDPRT"
PNG_ISO_PATH = IMAGES_DIR / f"{PART_STEM}.png"
PNG_FRONT_PATH = IMAGES_DIR / f"{PART_STEM}_front.png"


# Dimensions inferred from the supplied drawing. Units are millimeters.
FLANGE_OD = 94.0
BOLT_CIRCLE_DIA = 72.0
BOLT_HOLE_COUNT = 3
BOLT_HOLE_DIA = 11.0
BOLT_COUNTERBORE_DIA = 17.0
BOLT_COUNTERBORE_DEPTH = 8.0

HUB_OD = 54.0
CENTER_BORE_DIA = 35.0
TOTAL_LENGTH = 50.0
FLANGE_THICKNESS = 8.0


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


def print_state(model, label):
    print(f"\n[{label}]")
    print(f"ActiveDoc: {read_member(model, 'GetTitle')}")
    for i, (name, type_name) in enumerate(feature_rows(model)[:100]):
        print(f"  {i:02d} {name} ({type_name})")


def select_front_plane(model):
    model.ClearSelection2(True)
    for name in ("Front Plane", "\u524d\u89c6\u57fa\u51c6\u9762", "\u524d\u57fa\u51c6\u9762"):
        feat = model.FeatureByName(name)
        if feat is not None and feat.Select2(False, 0):
            return
    raise RuntimeError("Could not select the Front Plane.")


def last_profile_name(model):
    profiles = [name for name, type_name in feature_rows(model) if type_name == "ProfileFeature"]
    if not profiles:
        raise RuntimeError("No profile sketch found.")
    return profiles[-1]


def extrude_selected(model, depth_mm, feature_name):
    feature = model.FeatureManager.FeatureExtrusion2(
        True,
        False,
        False,
        0,
        0,
        mm(depth_mm),
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
        raise RuntimeError(f"Failed to create extrusion: {feature_name}")
    try:
        feature.Name = feature_name
    except Exception:
        pass
    print(f"Created extrusion: {feature_name}")
    return feature


def cut_selected(model, depth_mm, feature_name):
    for api_name in ("FeatureCut4", "FeatureCut3"):
        for reverse in (False, True):
            try:
                if api_name == "FeatureCut4":
                    feature = model.FeatureManager.FeatureCut4(
                        True,
                        False,
                        reverse,
                        1,
                        0,
                        mm(depth_mm),
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
                        mm(depth_mm),
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
                        feature.Name = feature_name
                    except Exception:
                        pass
                    print(f"Created cut: {feature_name}")
                    return feature
            except Exception:
                continue
    raise RuntimeError(f"Failed to create cut: {feature_name}")


def create_circle_extrude(model, diameter_mm, depth_mm, feature_name):
    select_front_plane(model)
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.CreateCircleByRadius(0.0, 0.0, 0.0, mm(diameter_mm / 2.0))
    sm.InsertSketch(True)
    sketch_name = last_profile_name(model)
    model.ClearSelection2(True)
    feat = model.FeatureByName(sketch_name)
    if feat is None or not feat.Select2(False, 0):
        raise RuntimeError(f"Failed to select sketch for {feature_name}: {sketch_name}")
    return extrude_selected(model, depth_mm, feature_name)


def create_hole_cut(model, holes, diameter_mm, depth_mm, feature_name):
    select_front_plane(model)
    sm = model.SketchManager
    sm.InsertSketch(True)
    for x_mm, y_mm in holes:
        sm.CreateCircleByRadius(mm(x_mm), mm(y_mm), 0.0, mm(diameter_mm / 2.0))
    sm.InsertSketch(True)
    sketch_name = last_profile_name(model)
    model.ClearSelection2(True)
    feat = model.FeatureByName(sketch_name)
    if feat is None or not feat.Select2(False, 0):
        raise RuntimeError(f"Failed to select sketch for cut {feature_name}: {sketch_name}")
    return cut_selected(model, depth_mm, feature_name)


def bolt_circle_points(radius_mm, count):
    # Drawing shows two upper holes and one lower hole, 120 degrees apart.
    pts = []
    for angle_deg in (30.0, 150.0, 270.0):
        angle = math.radians(angle_deg)
        pts.append((radius_mm * math.cos(angle), radius_mm * math.sin(angle)))
    return pts[:count]


def create_model(model):
    create_circle_extrude(model, FLANGE_OD, FLANGE_THICKNESS, "front flange dia94 x 8")
    model.ForceRebuild3(False)
    print_state(model, "After front flange")

    create_circle_extrude(model, HUB_OD, TOTAL_LENGTH, "rear hub dia54 x 50")
    model.ForceRebuild3(False)
    print_state(model, "After rear hub")

    create_hole_cut(
        model,
        [(0.0, 0.0)],
        CENTER_BORE_DIA,
        TOTAL_LENGTH + 2.0,
        "center bore dia35 through",
    )
    model.ForceRebuild3(False)
    print_state(model, "After center bore")

    bolt_pts = bolt_circle_points(BOLT_CIRCLE_DIA / 2.0, BOLT_HOLE_COUNT)
    create_hole_cut(
        model,
        bolt_pts,
        BOLT_HOLE_DIA,
        FLANGE_THICKNESS + 2.0,
        "3 x dia11 through holes on PCD dia72",
    )
    model.ForceRebuild3(False)
    print_state(model, "After bolt through holes")

    create_hole_cut(
        model,
        bolt_pts,
        BOLT_COUNTERBORE_DIA,
        BOLT_COUNTERBORE_DEPTH,
        "3 x dia17 counterbores depth 8",
    )
    model.ForceRebuild3(False)
    print_state(model, "After bolt counterbores")


def save_part(model):
    PART_PATH.parent.mkdir(parents=True, exist_ok=True)
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
        cleanup_generated_artifacts(OUTPUT_DIR, [PART_STEM], sw_app=sw_app)

        model = sw_app.NewDocument(TEMPLATE_PATH, 0, 0, 0)
        if model is None:
            raise RuntimeError(f"Failed to create part from template: {TEMPLATE_PATH}")
        flag_methods(model, "IModelDoc2")
        model.SetTitle2(PART_STEM)

        create_model(model)
        save_part(model)
        print_state(model, "After save")
        save_view(model, PNG_ISO_PATH, 7)
        save_view(model, PNG_FRONT_PATH, 1)
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()

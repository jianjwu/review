import math
import os
from pathlib import Path

import pythoncom
import win32com.client

from create_helical_gear_sketches import build_gear_profile_sketch, build_sweep_path_sketch
from solidworks_output_cleanup import cleanup_generated_artifacts


TEMPLATE_PATH = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot"
OUTPUT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = OUTPUT_DIR / "models"
IMAGES_DIR = OUTPUT_DIR / "images"
PART_PATH = MODELS_DIR / "helical_gear_z20_mn1_beta20.SLDPRT"
PNG_PATH = IMAGES_DIR / "helical_gear_z20_mn1_beta20.png"


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
    title = read_member(model, "GetTitle")
    print(f"ActiveDoc: {title}")
    rows = feature_rows(model)
    for i, (name, type_name) in enumerate(rows[:80]):
        print(f"  {i:02d} {name} ({type_name})")
    try:
        mass = model.Extension.CreateMassProperty()
        volume = read_member(mass, "Volume")
        surface = read_member(mass, "SurfaceArea")
        print(f"  Mass properties: volume={volume} m^3, surface_area={surface} m^2")
    except Exception as exc:
        print(f"  Mass properties unavailable: {exc}")


def select_feature(model, candidates, mark, append):
    for name in candidates:
        feat = model.FeatureByName(name)
        if feat is not None and feat.Select2(append, mark):
            return name
    rows = feature_rows(model)
    sketches = [name for name, type_name in rows if type_name == "ProfileFeature"]
    for name in sketches:
        if name in candidates:
            feat = model.FeatureByName(name)
            if feat is not None and feat.Select2(append, mark):
                return name
    return None


def create_twisted_sweep(model):
    model.ClearSelection2(True)
    profile = select_feature(model, ["Gear_Profile", "Sketch1", "草图1"], 1, False)
    if not profile:
        raise RuntimeError("Failed to select sweep profile sketch.")
    path = select_feature(model, ["Helix_Path", "Sketch2", "草图2"], 4, True)
    if not path:
        raise RuntimeError("Failed to select sweep path sketch.")

    feature = model.FeatureManager.InsertProtrusionSwept4(
        False,
        False,
        8,
        False,
        False,
        0,
        0,
        False,
        0.0,
        0.0,
        0,
        0,
        True,
        True,
        True,
        math.radians(15.6770),
        True,
        False,
        0.0,
        0,
    )
    if feature is None:
        raise RuntimeError(f"Failed to create sweep from profile={profile}, path={path}.")
    print(f"Created sweep: {feature.Name} from profile={profile}, path={path}")


def select_plane(model, candidates):
    model.ClearSelection2(True)
    for name in candidates:
        feat = model.FeatureByName(name)
        if feat is not None and feat.Select2(False, 0):
            return name
    raise RuntimeError(f"Failed to select plane. Tried: {', '.join(candidates)}")


def create_center_hole(model):
    select_plane(model, ["Front Plane", "前视基准面", "前基准面"])
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.CreateCircleByRadius(0.0, 0.0, 0.0, 0.002)
    sm.InsertSketch(True)
    model.ClearSelection2(True)

    feature = model.FeatureManager.FeatureCut4(
        True,
        False,
        False,
        1,
        0,
        0.010,
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
    if feature is None:
        raise RuntimeError("Failed to create 4 mm through center hole.")
    print(f"Created center hole cut: {feature.Name}")


def save_part(model):
    PART_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PART_PATH.exists():
        PART_PATH.unlink()
    result = model.SaveAs3(str(PART_PATH), 0, 0)
    if not PART_PATH.exists():
        raise RuntimeError(f"SaveAs3 did not write part file: {PART_PATH}; result={result}")
    print(f"Saved part: {PART_PATH}")


def export_png(model):
    PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PNG_PATH.exists():
        PNG_PATH.unlink()

    try:
        model.ShowNamedView2("*Isometric", 7)
    except Exception:
        pass
    try:
        model.ViewZoomtofit2()
    except Exception:
        pass

    try:
        model.SaveAs3(str(PNG_PATH), 0, 2)
    except Exception:
        pass

    if not PNG_PATH.exists():
        raise RuntimeError(f"PNG export failed: {PNG_PATH}")
    print(f"Exported image: {PNG_PATH}")


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
        model.SetTitle2("helical_gear_z20_mn1_beta20")

        build_gear_profile_sketch(model)
        build_sweep_path_sketch(model)
        model.ForceRebuild3(False)
        print_state(model, "After sketches")

        create_twisted_sweep(model)
        model.ForceRebuild3(False)
        print_state(model, "After twisted sweep")

        create_center_hole(model)
        model.ForceRebuild3(False)
        print_state(model, "After center hole")

        save_part(model)
        print_state(model, "After save")

        export_png(model)
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()

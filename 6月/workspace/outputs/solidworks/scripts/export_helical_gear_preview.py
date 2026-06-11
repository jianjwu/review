from pathlib import Path

import pythoncom
import win32com.client

from build_helical_gear_loft_complete import feature_rows


OUTPUT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = OUTPUT_DIR / "models"
IMAGES_DIR = OUTPUT_DIR / "images"
PART_PATH = MODELS_DIR / "helical_gear_z20_mn1_beta20.SLDPRT"
PNG_PATH = IMAGES_DIR / "helical_gear_z20_mn1_beta20.png"
PNG_FRONT_PATH = IMAGES_DIR / "helical_gear_z20_mn1_beta20_front.png"


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
    print(f"Exported {path}")


def main():
    pythoncom.CoInitialize()
    try:
        sw_app = win32com.client.GetActiveObject("SldWorks.Application")
        model = sw_app.ActiveDoc
        if model is None:
            model = sw_app.OpenDoc6(str(PART_PATH), 1, 0, "", 0, 0)
        if model is None:
            raise RuntimeError(f"Could not open part: {PART_PATH}")

        hide_features(model, {"ProfileFeature"})
        hide_features(model, {"RefPlane"})
        model.ForceRebuild3(False)

        save_view(model, PNG_PATH, 7)
        save_view(model, PNG_FRONT_PATH, 1)
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()

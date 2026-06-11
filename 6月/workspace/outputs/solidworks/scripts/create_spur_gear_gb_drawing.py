from pathlib import Path
import time

import pythoncom
import win32com.client
from win32com.client import dynamic

from solidworks_output_cleanup import cleanup_generated_artifacts


OUTPUT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = OUTPUT_DIR / "models"
DRAWINGS_DIR = OUTPUT_DIR / "drawings"
EXPORTS_DIR = OUTPUT_DIR / "exports"
IMAGES_DIR = OUTPUT_DIR / "images"
PART_PATH = MODELS_DIR / "spur_gear_z20_m1_pa20_b8_bore4.SLDPRT"
DRAWING_PATH = DRAWINGS_DIR / "spur_gear_z20_m1_pa20_b8_bore4_GB.SLDDRW"
PDF_PATH = EXPORTS_DIR / "spur_gear_z20_m1_pa20_b8_bore4_GB.pdf"
DWG_PATH = EXPORTS_DIR / "spur_gear_z20_m1_pa20_b8_bore4_GB.dwg"
PNG_PATH = IMAGES_DIR / "spur_gear_z20_m1_pa20_b8_bore4_GB.png"

DRAWING_TEMPLATE = Path(
    r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_a3.drwdot"
)
SHEET_FORMAT = Path(
    r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\lang\Chinese-Simplified\sheetformat\a3 - gb.slddrt"
)


def mm(value):
    return value / 1000.0


def dispatch(obj):
    return dynamic.Dispatch(obj._oleobj_) if hasattr(obj, "_oleobj_") else obj


def flag_methods(obj, *interfaces):
    try:
        from solidworks_mcp.adapters import sw_type_info

        sw_type_info.flag_methods(obj, *interfaces)
    except Exception:
        pass


def unwrap_com_result(result):
    if isinstance(result, (list, tuple)):
        return result[0] if result else None
    return result


def read_member(obj, name):
    member = getattr(obj, name, None)
    if callable(member):
        try:
            return member()
        except Exception:
            return member
    return member


def connect_solidworks():
    try:
        app = win32com.client.GetActiveObject("SldWorks.Application")
    except Exception:
        app = win32com.client.Dispatch("SldWorks.Application")
    app.Visible = True
    flag_methods(app, "ISldWorks")
    return app


def require_path(path):
    if not path.exists():
        raise FileNotFoundError(path)


def delete_output(path):
    if path.exists():
        try:
            path.unlink()
        except PermissionError as exc:
            print(f"[warn] could not delete locked output {path.name}: {exc}")


def model_title(model):
    try:
        return read_member(model, "GetTitle")
    except Exception:
        return "<unknown>"


def readback(label, model):
    print(f"[readback] {label}: active={model_title(model)}")


def open_part(app):
    # swDocPART=1. Keep the call shape used by the local SolidWorks scripts.
    part = unwrap_com_result(app.OpenDoc6(str(PART_PATH), 1, 0, "", 0, 0))
    if part is None:
        raise RuntimeError(f"SolidWorks could not open part: {PART_PATH}")
    part = dispatch(part)
    flag_methods(part, "IModelDoc2", "IPartDoc")
    part.ForceRebuild3(False)
    readback("opened part", part)
    return part


def close_existing_output_drawing(app):
    try:
        doc = unwrap_com_result(app.GetOpenDocumentByName(str(DRAWING_PATH)))
    except Exception:
        doc = None
    if doc is not None:
        doc = dispatch(doc)
        flag_methods(doc, "IModelDoc2", "IDrawingDoc")
        title = model_title(doc)
        try:
            app.CloseDoc(title)
            print(f"[readback] closed existing drawing: {title}")
            return
        except Exception as exc:
            print(f"[warn] could not close existing drawing {title}: {exc}")

    for title in (DRAWING_PATH.name, DRAWING_PATH.stem):
        try:
            app.CloseDoc(title)
        except Exception:
            pass


def set_custom_properties(model):
    mgr = model.Extension.CustomPropertyManager("")
    props = {
        "图样名称": "直齿圆柱齿轮",
        "图号": "SW-GEAR-Z20-M1-PA20-B8-BORE4",
        "材料": "普通碳钢",
        "比例": "5:1",
        "阶段标记": "零件图",
    }
    for key, value in props.items():
        # swCustomInfoText=30, swCustomPropertyReplaceValue=2
        mgr.Add3(key, 30, value, 2)
    readback("custom properties updated", model)


def new_gb_drawing(app):
    # swDwgPaperA3size=8. Width/height are read from the template.
    drawing_model = unwrap_com_result(app.NewDocument(str(DRAWING_TEMPLATE), 8, 0, 0))
    if drawing_model is None:
        raise RuntimeError(f"SolidWorks could not create drawing from: {DRAWING_TEMPLATE}")
    drawing_model = dispatch(drawing_model)
    flag_methods(drawing_model, "IModelDoc2", "IDrawingDoc")
    drawing = dispatch(drawing_model)
    flag_methods(drawing, "IModelDoc2", "IDrawingDoc")

    try:
        sheet = drawing.GetCurrentSheet()
        sheet.SetScale(5, 1, True, True)
        sheet.SetName("GB-A3-零件图")
        sheet.SetTemplateName(str(SHEET_FORMAT))
        sheet.ReloadTemplate(True)
    except Exception as exc:
        print(f"[warn] sheet format reload skipped: {exc}")

    readback("created GB drawing", drawing_model)
    return drawing_model, drawing


def set_view_scale(view, numerator=5, denominator=1):
    if view is None:
        return
    view = dispatch(view)
    for attr, value in (
        ("UseSheetScale", False),
        ("ScaleDecimal", numerator / denominator),
        ("ScaleRatio", [numerator, denominator]),
    ):
        try:
            setattr(view, attr, value)
        except Exception:
            pass


def add_standard_views(drawing_model, drawing):
    views = []
    specs = [
        (("*Front", "*前视", "*前視"), mm(115), mm(160), "主视图", 5, 1),
        (("*Right", "*右视", "*右視"), mm(250), mm(160), "右视图", 5, 1),
        (("*Top", "*上视", "*上視"), mm(115), mm(68), "俯视图", 5, 1),
    ]

    try:
        app_doc_title = model_title(drawing_model)
        print(f"[readback] target drawing before views: {app_doc_title}")
    except Exception:
        pass

    for orientations, x, y, label, scale_num, scale_den in specs:
        view = None
        tried = []
        for orientation in orientations:
            tried.append(orientation)
            view = unwrap_com_result(
                drawing.CreateDrawViewFromModelView3(str(PART_PATH), orientation, x, y, 0)
            )
            if view is not None:
                view = dispatch(view)
                flag_methods(view, "IView")
                break
        if view is None:
            if label == "主视图":
                try:
                    result = drawing.Create1stAngleViews2(str(PART_PATH))
                    print(f"[readback] fallback Create1stAngleViews2 result: {result}")
                    readback("standard views complete by first-angle fallback", drawing_model)
                    return views
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to create drawing view: {label}; tried {tried}; fallback error: {exc}"
                    ) from exc
            raise RuntimeError(f"Failed to create drawing view: {label}; tried {tried}")
        set_view_scale(view, scale_num, scale_den)
        views.append((label, view))
        print(f"[readback] created view: {label} {tried[-1]}")

    try:
        drawing_model.ViewZoomToFit2()
    except Exception:
        pass
    readback("standard views complete", drawing_model)
    return views


def note_text(note):
    flag_methods(note, "INote")
    try:
        return str(read_member(note, "GetText") or "")
    except Exception:
        return ""


def next_annotation(ann):
    for method_name in ("GetNext3", "GetNext2", "GetNext"):
        try:
            nxt = unwrap_com_result(getattr(ann, method_name)())
            if nxt is not None:
                nxt = dispatch(nxt)
                flag_methods(nxt, "IAnnotation")
            return nxt
        except Exception:
            continue
    return None


def annotation_specific_note(ann):
    flag_methods(ann, "IAnnotation")
    for method_name in ("GetSpecificAnnotation", "IGetSpecificAnnotation"):
        try:
            note = unwrap_com_result(getattr(ann, method_name)())
            if note is not None:
                note = dispatch(note)
                flag_methods(note, "INote")
                return note
        except Exception:
            continue
    return None


def find_annotation_for_note(drawing_model, note, text):
    flag_methods(note, "INote", "IAnnotation")

    for method_name in ("GetAnnotation", "IGetAnnotation"):
        try:
            ann = unwrap_com_result(getattr(note, method_name)())
            if ann is not None:
                ann = dispatch(ann)
                flag_methods(ann, "IAnnotation")
                return ann
        except Exception:
            continue

    try:
        # If SolidWorks returned the annotation directly, this method exists.
        getattr(note, "GetSpecificAnnotation")()
        flag_methods(note, "IAnnotation")
        return note
    except Exception:
        pass

    target = text.strip()
    for first_method in ("GetFirstAnnotation2", "GetFirstAnnotation"):
        try:
            ann = unwrap_com_result(getattr(drawing_model, first_method)())
        except Exception:
            ann = None
        if ann is None:
            continue

        ann = dispatch(ann)
        flag_methods(ann, "IAnnotation")
        for _ in range(500):
            specific = annotation_specific_note(ann)
            if specific is not None and note_text(specific).strip() == target:
                return ann
            ann = next_annotation(ann)
            if ann is None:
                break

    return None


def annotation_texts(drawing_model, limit=50):
    texts = []
    for first_method in ("GetFirstAnnotation2", "GetFirstAnnotation"):
        try:
            ann = unwrap_com_result(getattr(drawing_model, first_method)())
        except Exception:
            ann = None
        if ann is None:
            continue
        ann = dispatch(ann)
        flag_methods(ann, "IAnnotation")
        for _ in range(limit):
            specific = annotation_specific_note(ann)
            if specific is not None:
                text = note_text(specific)
                if text:
                    texts.append(text)
            ann = next_annotation(ann)
            if ann is None:
                break
        if texts:
            break
    return texts


def set_annotation_format(ann, height_mm=3.5):
    flag_methods(ann, "IAnnotation")
    try:
        fmt = ann.GetTextFormat(0)
        fmt.CharHeight = mm(height_mm)
        ann.SetTextFormat(0, True, fmt)
    except Exception:
        pass


def set_direct_note_format(note, height_mm=3.5):
    flag_methods(note, "INote")
    try:
        fmt = note.GetTextFormat()
        fmt.CharHeight = mm(height_mm)
        note.SetTextFormat(False, fmt)
    except Exception:
        pass


def add_note(drawing_model, text, x_mm, y_mm, height_mm=3.5):
    try:
        drawing_model.ClearSelection2(True)
    except Exception:
        pass
    note = unwrap_com_result(drawing_model.InsertNote(text))
    if note is None:
        raise RuntimeError(f"Failed to add note: {text[:40]}")
    note = dispatch(note)
    flag_methods(note, "INote", "IAnnotation")
    ann = find_annotation_for_note(drawing_model, note, text)
    target = ann if ann is not None else note
    if ann is not None:
        set_annotation_format(ann, height_mm)
    else:
        set_direct_note_format(note, height_mm)
    positioned = False
    position_errors = []
    for method_name in ("SetPosition", "SetPosition2", "SetTextPoint"):
        try:
            getattr(target, method_name)(mm(x_mm), mm(y_mm), 0)
            positioned = True
            break
        except Exception as exc:
            position_errors.append(f"{method_name}: {exc}")
    if not positioned:
        raise RuntimeError(
            f"Failed to position note: {text[:40]}; "
            f"type={type(note)!r}; errors={position_errors}"
        )
    try:
        drawing_model.ClearSelection2(True)
    except Exception:
        pass
    print(f"[readback] note added at ({x_mm}, {y_mm}): {text.splitlines()[0]}")
    return note


def add_gb_annotations(drawing_model):
    add_note(drawing_model, "直齿圆柱齿轮", 25, 278, 5.0)
    add_note(drawing_model, "零件图  GB/T 4458  A3  比例 5:1  单位:mm", 25, 270, 3.0)

    main_dims = [
        ("主要尺寸", 252),
        ("外径 da = Φ22", 244),
        ("分度圆 d = Φ20", 236),
        ("齿根圆 df = Φ17.5", 228),
        ("中心孔 = Φ4", 220),
        ("齿宽 b = 8", 212),
    ]
    for text, y in main_dims:
        add_note(drawing_model, text, 25, y, 3.0)

    technical_notes = [
        ("技术要求", 151),
        ("1. 未注尺寸公差按 GB/T 1804-m。", 143),
        ("2. 未注形位公差按 GB/T 1184-K。", 135),
        ("3. 齿廓按 20° 渐开线标准直齿圆柱齿轮绘制。", 127),
        ("4. 去毛刺，锐边倒钝；齿面不得有裂纹、磕碰。", 119),
        ("5. 材料: 普通碳钢；热处理及表面处理未指定。", 111),
    ]
    for text, y in technical_notes:
        add_note(drawing_model, text, 285, y, 3.0)

    gear_table = [
        ("齿轮参数表", 253),
        ("齿数 z              20", 245),
        ("模数 m              1", 237),
        ("压力角 α            20°", 229),
        ("齿顶高系数 ha*      1", 221),
        ("顶隙系数 c*         0.25", 213),
        ("变位系数 x          0", 205),
        ("精度等级            未指定", 197),
    ]
    for text, y in gear_table:
        add_note(drawing_model, text, 285, y, 3.0)

    add_note(drawing_model, "Φ22", 103, 232, 3.5)
    add_note(drawing_model, "Φ20 分度圆", 137, 220, 3.0)
    add_note(drawing_model, "Φ17.5 齿根圆", 139, 207, 3.0)
    add_note(drawing_model, "Φ4 通孔", 143, 193, 3.5)
    add_note(drawing_model, "8", 250, 210, 3.5)
    readback("GB annotations complete", drawing_model)


def save_and_export(drawing_model):
    for directory in (DRAWINGS_DIR, EXPORTS_DIR, IMAGES_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    for path in (DRAWING_PATH, PDF_PATH, DWG_PATH, PNG_PATH):
        delete_output(path)

    outputs = [
        (DRAWING_PATH, 0),
        (PDF_PATH, 2),
        (DWG_PATH, 2),
        (PNG_PATH, 2),
    ]
    for path, options in outputs:
        result = drawing_model.SaveAs3(str(path), 0, options)
        time.sleep(0.2)
        if not path.exists():
            raise RuntimeError(f"SaveAs3 did not write {path}; result={result}")
        print(f"[readback] saved {path.name}: {path.stat().st_size} bytes")


def main():
    require_path(PART_PATH)
    require_path(DRAWING_TEMPLATE)
    require_path(SHEET_FORMAT)

    pythoncom.CoInitialize()
    try:
        app = connect_solidworks()
        cleanup_generated_artifacts(OUTPUT_DIR, [DRAWING_PATH.stem], sw_app=app)
        close_existing_output_drawing(app)
        part = open_part(app)
        drawing_model, drawing = new_gb_drawing(app)
        add_standard_views(drawing_model, drawing)
        add_gb_annotations(drawing_model)
        drawing_model.ForceRebuild3(False)
        readback("rebuilt drawing", drawing_model)
        save_and_export(drawing_model)
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()

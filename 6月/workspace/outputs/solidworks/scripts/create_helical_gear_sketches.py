import math
from pathlib import Path

import pythoncom
import win32com.client


TEMPLATE_PATH = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot"
PART_TITLE = "helical_gear_z20_mn1_beta20"


def mm(value):
    return value / 1000.0


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
    if not state["has_point"]:
        raise RuntimeError("No profile points were created.")

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


def rename_active_sketch(model, name):
    try:
        sketch = model.GetActiveSketch2()
        if sketch is not None:
            sketch.Name = name
    except Exception:
        pass


def select_plane(model, names, purpose):
    model.ClearSelection2(True)
    for name in names:
        feature = model.FeatureByName(name)
        if feature is not None and feature.Select2(False, 0):
            return

    for name in names:
        try:
            if model.Extension.SelectByID2(
                name, "PLANE", 0.0, 0.0, 0.0, False, 0, None, 0
            ):
                return
        except Exception:
            pass

    raise RuntimeError(f"Could not select {purpose}. Tried: {', '.join(names)}")


def build_gear_profile_sketch(model):
    select_plane(
        model,
        ["Front Plane", "前视基准面", "前基准面"],
        "Front Plane for gear profile sketch",
    )

    sm = model.SketchManager
    sm.InsertSketch(True)
    rename_active_sketch(model, "Gear_Profile")
    sm.AddToDB = True

    z = 20
    mn = 1.0
    alpha_n = math.radians(20.0)
    beta = math.radians(20.0)
    mt = mn / math.cos(beta)
    rp = z * mt / 2.0
    ra = rp + mn
    rf = rp - 1.25 * mn
    alpha_t = math.atan(math.tan(alpha_n) / math.cos(beta))
    rb = rp * math.cos(alpha_t)
    pitch = 2.0 * math.pi / z
    half_tooth = math.pi / (2.0 * z)
    tp = math.sqrt((rp / rb) ** 2 - 1.0)
    psi_p = tp - math.atan(tp)
    ta = math.sqrt((ra / rb) ** 2 - 1.0)
    psi_a = ta - math.atan(ta)

    flank_segments = 8
    top_segments = 3
    root_segments = 3
    state = {"has_point": False}

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


def build_sweep_path_sketch(model):
    select_plane(
        model,
        ["Right Plane", "右视基准面", "右基准面"],
        "Right Plane for helical sweep path sketch",
    )

    sm = model.SketchManager
    sm.InsertSketch(True)
    rename_active_sketch(model, "Helix_Path")
    sm.AddToDB = True
    sm.CreateLine(0.0, 0.0, 0.0, 0.0, 0.0, mm(8.0))
    sm.AddToDB = False
    sm.InsertSketch(True)


def main():
    if not Path(TEMPLATE_PATH).exists():
        raise RuntimeError(f"Part template not found: {TEMPLATE_PATH}")

    pythoncom.CoInitialize()
    try:
        sw_app = win32com.client.GetActiveObject("SldWorks.Application")
        model = sw_app.NewDocument(TEMPLATE_PATH, 0, 0, 0)
        if model is None:
            raise RuntimeError(f"Failed to create part from template: {TEMPLATE_PATH}")

        model.SetTitle2(PART_TITLE)
        build_gear_profile_sketch(model)
        build_sweep_path_sketch(model)
        model.ForceRebuild3(False)

        print("Created active part with sketches: Gear_Profile, Helix_Path")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()

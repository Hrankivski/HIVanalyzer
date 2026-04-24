import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
from core import constants


def load_default_project(path="data/default.json"):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            project = json.load(f)
    except Exception:
        return None

    settings = project.get("settings", {})
    geometry = project.get("geometry", {})
    elements = project.get("elements", [])

    if "project_settings" not in st.session_state:
        st.session_state.project_settings = {}
    st.session_state.project_settings.update(settings)

    # Save geometry to project settings for interface defaults
    if "L" in geometry:
        st.session_state.project_settings["room_l"] = geometry.get("L")
    if "W" in geometry:
        st.session_state.project_settings["room_w"] = geometry.get("W")
    if "H" in geometry:
        st.session_state.project_settings["room_h"] = geometry.get("H")
    if "L_cut" in geometry:
        st.session_state.project_settings["room_l_cut"] = geometry.get("L_cut")
    if "W_cut" in geometry:
        st.session_state.project_settings["room_w_cut"] = geometry.get("W_cut")

    if elements:
        try:
            st.session_state.elements_df = pd.DataFrame(elements)
        except Exception:
            st.session_state.elements_df = pd.DataFrame(
                columns=["Тип", "X", "Y", "Ширина", "Орієнтація"]
            )

    # Apply coordinate details into session state keys used by sliders and snap buttons
    if "elements_df" in st.session_state and not st.session_state.elements_df.empty:
        for i, row in st.session_state.elements_df.iterrows():
            st.session_state[f"x_{i}"] = float(row.get("X", 0.0))
            st.session_state[f"y_{i}"] = float(row.get("Y", 0.0))
            st.session_state[f"orient_{i}"] = row.get("Орієнтація", "Горизонтально")
            st.session_state[f"width_{i}"] = float(row.get("Ширина", 1.2))

    return project


def init_session_state():
    if "elements_df" not in st.session_state:
        st.session_state.elements_df = pd.DataFrame(
            columns=["Тип", "X", "Y", "Ширина", "Орієнтація"]
        )

    if "project_settings" not in st.session_state:
        st.session_state.project_settings = {
            "wall_material": list(constants.MATERIALS.keys())[0],
            "wall_thickness": 0.38,
            "wall_type_0": "Зовнішня",
            "wall_mat_0": "Базовий",
            "wall_type_1": "Внутрішня",
            "wall_mat_1": "Базовий",
            "wall_type_2": "Внутрішня",
            "wall_mat_2": "Базовий",
            "wall_type_3": "Внутрішня",
            "wall_mat_3": "Базовий",
            "wall_type_4": "Зовнішня",
            "wall_mat_4": "Базовий",
            "wall_type_5": "Зовнішня",
            "wall_mat_5": "Базовий",
            "window_type": "Двокамерний",
            "occupants": 10,
            "activity_level": "Офісна робота",
            "recuperator_efficiency": 85.0,
            "room_l": 8.0,
            "room_w": 6.0,
            "room_h": 2.8,
            "room_l_cut": 3.0,
            "room_w_cut": 3.0,
        }

    if "default_loaded" not in st.session_state:
        load_default_project("data/default.json")
        st.session_state.default_loaded = True


def add_element(el_type, room_l, room_w):
    idx = len(st.session_state.elements_df)
    new_row = pd.DataFrame(
        [
            {
                "Тип": el_type,
                "X": room_l / 2,
                "Y": 0.0,
                "Ширина": 1.2 if el_type == "Вікно" else 0.8,
                "Орієнтація": "Горизонтально",
            }
        ]
    )
    st.session_state.elements_df = pd.concat(
        [st.session_state.elements_df, new_row], ignore_index=True
    )
    st.session_state[f"x_{idx}"] = room_l / 2
    st.session_state[f"y_{idx}"] = 0.0
    st.session_state[f"orient_{idx}"] = "Горизонтально"
    st.session_state[f"width_{idx}"] = 1.2 if el_type == "Вікно" else 0.8


def render_blueprint(l, w, l_cut, w_cut, elements):  # noqa: E741
    fig = go.Figure()

    x_verts = [0, l, l, l - l_cut, l - l_cut, 0, 0]
    y_verts = [0, 0, w - w_cut, w - w_cut, w, w, 0]

    # Base floor area
    path_str = f"M {x_verts[0]},{y_verts[0]}"
    for i in range(1, 6):
        path_str += f" L {x_verts[i]},{y_verts[i]}"
    path_str += " Z"

    fig.add_shape(
        type="path",
        path=path_str,
        line=dict(width=0),
        fillcolor="rgba(223, 230, 233, 0.2)",
    )

    settings = st.session_state.get("project_settings", {})

    def get_line_style(wall_type, wall_mat):
        if wall_mat == "Скло":
            return dict(color="#3498db", width=4, dash="dot")
        if wall_type == "Зовнішня":
            return dict(color="#1e272e", width=6)
        return dict(color="#e15f41", width=3, dash="dash")

    wall_labels = ["Нижня", "Права", "Внутр. Верхня", "Внутр. Права", "Верхня", "Ліва"]
    for i in range(6):
        w_type = settings.get(f"wall_type_{i}", "Зовнішня")
        w_mat = settings.get(f"wall_mat_{i}", "Базовий")

        fig.add_shape(
            type="line",
            x0=x_verts[i],
            y0=y_verts[i],
            x1=x_verts[i + 1],
            y1=y_verts[i + 1],
            line=get_line_style(w_type, w_mat),
        )

        mid_x = (x_verts[i] + x_verts[i + 1]) / 2
        mid_y = (y_verts[i] + y_verts[i + 1]) / 2
        offset_x = 0
        offset_y = 0
        textangle = 0
        if y_verts[i] == y_verts[i + 1]:
            offset_y = -0.5 if i == 0 or i == 2 else 0.5
        else:
            offset_x = 0.5 if i == 1 or i == 3 else -0.5
            textangle = -90 if i == 5 else 90

        fig.add_annotation(
            x=mid_x + offset_x,
            y=mid_y + offset_y,
            text=wall_labels[i],
            showarrow=False,
            font=dict(size=14, color="gray"),
            textangle=textangle,
        )

    for i, row in elements.iterrows():
        if row["Тип"] == "Вікно":
            color = "#00a8ff"
        elif row["Тип"] == "Джерело тепла":
            color = "#e84118"
        else:
            color = "#f39c12"
        size = row["Ширина"]
        is_hor = row["Орієнтація"] == "Горизонтально"
        w_h = (size / 2) if is_hor else 0.15
        h_h = 0.15 if is_hor else (size / 2)
        fig.add_shape(
            type="rect",
            x0=row["X"] - w_h,
            y0=row["Y"] - h_h,
            x1=row["X"] + w_h,
            y1=row["Y"] + h_h,
            line=dict(color=color, width=2),
            fillcolor=color,
        )
        fig.add_annotation(
            x=row["X"],
            y=row["Y"],
            text=f"{row['Тип']} {i + 1}",
            showarrow=False,
            font=dict(size=14, color="black"),
        )
    fig.update_xaxes(
        range=[-1.0, l + 1.0],
        showgrid=True,
        gridcolor="#dcdde1",
        dtick=1.0,
        tickfont=dict(size=14),
        title_font=dict(size=16),
    )
    fig.update_yaxes(
        range=[-1.0, w + 1.0],
        showgrid=True,
        gridcolor="#dcdde1",
        dtick=1.0,
        tickfont=dict(size=14),
        scaleanchor="x",
        scaleratio=1,
    )
    fig.update_layout(
        template="plotly_white", height=600, margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig


def export_project(room_l, room_w, room_h, room_l_cut, room_w_cut):
    project = {
        "geometry": {
            "L": room_l,
            "W": room_w,
            "H": room_h,
            "L_cut": room_l_cut,
            "W_cut": room_w_cut,
        },
        "settings": st.session_state.project_settings,
        "elements": st.session_state.elements_df.to_dict(orient="records"),
    }
    return json.dumps(project, indent=4, ensure_ascii=False)

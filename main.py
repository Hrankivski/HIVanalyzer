"""
Головний модуль застосунку HIVanalyzer (Streamlit).
Забезпечує користувацький інтерфейс для конфігурації приміщення, візуалізації, 
запуску симуляцій EnergyPlus та взаємодії зі штучним інтелектом.
"""
import streamlit as st

from core import constants
from ui import designer
from ui.tabs import (
    advisor_tab,
    ai_lab_tab,
    climate_tab,
    data_gen_tab,
    geometry_tab,
    save_tab,
)

st.set_page_config(page_title="Recuperator Optimizer", layout="wide")
designer.init_session_state()

# --- SIDEBAR: ВВІД ПАРАМЕТРІВ ---
st.sidebar.header("Конфігурація системи")
with st.sidebar.expander("Шляхи EnergyPlus"):
    st.session_state.project_settings["eplus_exe"] = st.text_input(
        "Шлях до energyplus.exe",
        st.session_state.project_settings.get(
            "eplus_exe", constants.SIMULATION["eplus_exe"]
        ),
    )
    st.session_state.project_settings["weather_file"] = st.text_input(
        "Шлях до файлу погоди",
        st.session_state.project_settings.get(
            "weather_file", constants.SIMULATION["weather_file"]
        ),
    )

st.sidebar.markdown("---")
if st.sidebar.button("Завантажити налаштування з data/default.json"):
    designer.load_default_project("data/default.json")
    st.session_state["default_loaded"] = True

st.sidebar.header("Геометрія та матеріали")
room_l = st.sidebar.number_input(
    "Загальна Довжина L (м)",
    2.0,
    30.0,
    st.session_state.project_settings.get("room_l", 8.0),
    0.1,
    key="room_l",
)
room_w = st.sidebar.number_input(
    "Загальна Ширина W (м)",
    2.0,
    30.0,
    st.session_state.project_settings.get("room_w", 6.0),
    0.1,
    key="room_w",
)
room_l_cut = st.sidebar.number_input(
    "Виріз L_cut (м)",
    0.0,
    20.0,
    st.session_state.project_settings.get("room_l_cut", 3.0),
    0.1,
    key="room_l_cut",
)
room_w_cut = st.sidebar.number_input(
    "Виріз W_cut (м)",
    0.0,
    20.0,
    st.session_state.project_settings.get("room_w_cut", 3.0),
    0.1,
    key="room_w_cut",
)
room_h = st.sidebar.number_input(
    "Висота H (м)",
    2.0,
    5.0,
    st.session_state.project_settings.get("room_h", 2.8),
    0.1,
    key="room_h",
)

st.session_state.project_settings["room_l"] = room_l
st.session_state.project_settings["room_w"] = room_w
st.session_state.project_settings["room_l_cut"] = room_l_cut
st.session_state.project_settings["room_w_cut"] = room_w_cut
st.session_state.project_settings["room_h"] = room_h

with st.sidebar.expander("Характеристики конструкцій"):
    mat_options = list(constants.MATERIALS.keys())
    st.session_state.project_settings["wall_material"] = st.selectbox(
        "Матеріал стін",
        mat_options,
        index=mat_options.index(
            st.session_state.project_settings.get("wall_material", mat_options[0])
        ),
    )

    # Відображення характеристик обраного матеріалу
    sel_mat_props = constants.MATERIALS[
        st.session_state.project_settings["wall_material"]
    ]
    st.info(
        f"λ (Теплопровідність): {sel_mat_props['conductivity']} Вт/м·К\n\n"
        f"ρ (Густина): {sel_mat_props['density']} кг/м³\n\n"
        f"c (Теплоємність): {sel_mat_props['specific_heat']} Дж/кг·К"
    )

    st.session_state.project_settings["wall_thickness"] = st.number_input(
        "Товщина стін (м)", 0.1, 1.0, 0.38
    )

    st.markdown("Налаштування стін (Г-форма: 6 стін):")
    wall_labels = ["Нижня", "Права", "Внутр. Верхня", "Внутр. Права", "Верхня", "Ліва"]
    for i, label in enumerate(wall_labels):
        c1, c2 = st.columns([1, 1])
        st.session_state.project_settings[f"wall_type_{i}"] = c1.selectbox(
            f"{label}",
            ["Зовнішня", "Внутрішня"],
            index=0
            if st.session_state.project_settings.get(f"wall_type_{i}", "Зовнішня")
            == "Зовнішня"
            else 1,
            key=f"w_type_{i}",
        )
        st.session_state.project_settings[f"wall_mat_{i}"] = c2.selectbox(
            "Мат.",
            ["Базовий", "Скло"],
            index=0
            if st.session_state.project_settings.get(f"wall_mat_{i}", "Базовий")
            == "Базовий"
            else 1,
            key=f"w_mat_{i}",
        )

st.sidebar.markdown("---")
st.sidebar.header("Експлуатація приміщення")
room_occupants_default = st.session_state.project_settings.get("occupants", 10)
room_activity_default = st.session_state.project_settings.get(
    "activity_level", "Офісна робота"
)

occupants = st.sidebar.number_input(
    "Кількість людей", 0, 100, room_occupants_default, key="occupants"
)
activity_options = ["Відпочинок", "Офісна робота", "Легка праця", "Важка праця"]
activity_index = (
    activity_options.index(room_activity_default)
    if room_activity_default in activity_options
    else 1
)
activity_level = st.sidebar.selectbox(
    "Тип активності", activity_options, index=activity_index, key="activity_level"
)

st.session_state.project_settings["occupants"] = occupants
st.session_state.project_settings["activity_level"] = activity_level

schedule_options = ["Офіс (09:00-18:00)", "Житлове (24/7)", "Серверна/Склад (24/7)"]
schedule_default = st.session_state.project_settings.get(
    "schedule_type", "Офіс (09:00-18:00)"
)
sched_index = (
    schedule_options.index(schedule_default)
    if schedule_default in schedule_options
    else 0
)
schedule_type = st.sidebar.selectbox(
    "Графік роботи", schedule_options, index=sched_index, key="schedule_type"
)
st.session_state.project_settings["schedule_type"] = schedule_type

st.sidebar.markdown("---")
dev_mode = st.sidebar.checkbox(
    "🛠️ Режим розробника (Dev Mode)",
    value=False,
    help="Відображає вкладки для тренування нейромереж та генерації датасетів.",
)

infilt_options = [
    "Низька (Старий будинок з протягами)",
    "Середня (Сучасні вікна)",
    "Висока (Пасивний будинок)",
]
infilt_default = st.session_state.project_settings.get(
    "infiltration", "Середня (Сучасні вікна)"
)
infilt_idx = (
    infilt_options.index(infilt_default) if infilt_default in infilt_options else 1
)
st.session_state.project_settings["infiltration"] = st.sidebar.selectbox(
    "Якість герметизації", infilt_options, index=infilt_idx, key="infiltration_level"
)

# --- УПРАВЛІННЯ ЕЛЕМЕНТАМИ ---
st.sidebar.markdown("---")
st.sidebar.subheader("Додати об'єкти")
col_add1, col_add2, col_add3 = st.sidebar.columns(3)
if col_add1.button("Вікно"):
    designer.add_element("Вікно", room_l, room_w)
if col_add2.button("Рекуператор"):
    designer.add_element("Рекуператор", room_l, room_w)
if col_add3.button("Джерело тепла"):
    designer.add_element("Джерело тепла", room_l, room_w)

# --- ОСНОВНИЙ РОБОЧИЙ ПРОСТІР ---
if dev_mode:
    tab_options = [
        "1. Геометрія кімнати",
        "2. Ескізний ШІ-аналіз",
        "3. Точний розрахунок (E+)",
        "Збереження",
        "Генерація Даних (Dev)",
        "Навчання Нейромережі (Dev)",
    ]
else:
    tab_options = [
        "1. Геометрія кімнати",
        "2. Ескізний ШІ-аналіз",
        "3. Точний розрахунок (E+)",
        "Збереження",
    ]

selected_tab = st.radio("Навігація", tab_options, horizontal=True, label_visibility="collapsed")

if selected_tab == "1. Геометрія кімнати":
    geometry_tab.render(room_l, room_w, room_l_cut, room_w_cut)

elif selected_tab == "2. Ескізний ШІ-аналіз":
    advisor_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

elif selected_tab == "3. Точний розрахунок (E+)":
    climate_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

elif selected_tab == "Збереження":
    save_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

elif selected_tab == "Генерація Даних (Dev)":
    data_gen_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

elif selected_tab == "Навчання Нейромережі (Dev)":
    ai_lab_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

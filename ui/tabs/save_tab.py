import streamlit as st
import datetime
from ui import designer
from simulation import idf_bridge

def render(room_l, room_w, room_h, room_l_cut, room_w_cut):
    st.subheader("Управління файлом проєкту")
    json_data = designer.export_project(room_l, room_w, room_h, room_l_cut, room_w_cut)
    st.download_button(
        label="Завантажити проєкт у JSON",
        data=json_data,
        file_name="project_twin.json",
        mime="application/json",
    )

    idf_data = idf_bridge.generate_idf_structure(json_data)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="Завантажити IDF (EnergyPlus)",
        data=idf_data,
        file_name=f"simulation_{timestamp}.idf",
        mime="text/plain",
    )

    st.markdown("### Попередній перегляд маніфесту IDF")
    st.text_area("IDF Structure", idf_data, height=400)

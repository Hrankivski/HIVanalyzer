import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from core import constants
from ui import designer
from simulation import idf_bridge, simulation_engine, validator
from ai import rl_agent, ai_engine, ml_surrogate
import plotly.graph_objects as go


def render(room_l, room_w, room_h, room_l_cut, room_w_cut):
    st.subheader("Генератор синтетичних даних (Big Data)")
    st.write(
        "Тут ви можете запустити пакетну симуляцію для випадкового варіювання параметрів та збору датасету для нейромережі."
    )
    n_sims = st.number_input("Кількість симуляцій (Batch Size)", 5, 500, 50)
    
    if st.button(f"Generate Training Data (Batch {n_sims})"):
        with st.status(f"Запуск {n_sims} симуляцій у фоні...") as status:
            json_data = designer.export_project(
                room_l, room_w, room_h, room_l_cut, room_w_cut
            )
            eplus_path = st.session_state.project_settings.get(
                "eplus_exe", constants.SIMULATION["eplus_exe"]
            )
            epw_path = st.session_state.project_settings.get(
                "weather_file", constants.SIMULATION["weather_file"]
            )
    
            runner = simulation_engine.SimulationRunner(
                json_data, eplus_path, epw_path
            )
            success, count = runner.run_batch(n_sims)
    
            if success:
                status.update(
                    label=f"Успішно зібрано {count} записів!", state="complete"
                )
            else:
                status.update(label="Помилка пакетної симуляції", state="error")
    
    st.markdown("---")
    st.subheader("Аналітика Зібраних Даних (Data Quality)")
    import os
    
    if os.path.exists("data/training_dataset.csv"):
        df_ml = pd.read_csv("data/training_dataset.csv")
    
        # KPIs
        m_score, m1, m2, m3 = st.columns(4)
        if "CO2 (ppm)" in df_ml.columns:
            max_co2 = df_ml["CO2 (ppm)"].max()
            danger_pct = (df_ml["CO2 (ppm)"] > 1000).mean() * 100
    
            # Індекс Багатства Датасету
            richness_score = max(0, 100 - abs(25 - danger_pct) * 4)
            m_score.metric(
                "Індекс Багатства (0-100%)",
                f"{richness_score:.0f}%",
                help="100% означає ідеальний баланс (25% екстремальних ситуацій).",
            )
    
            m1.metric("Кількість записів", f"{len(df_ml):,}")
            m2.metric("Макс. CO2", f"{max_co2:.0f} ppm")
            m3.metric("Частка задухи (>1000ppm)", f"{danger_pct:.1f} %")
    
            # Histogram
            fig_hist = px.histogram(
                df_ml,
                x="CO2 (ppm)",
                nbins=50,
                title="Розподіл рівнів CO2 у зібраному датасеті",
                color_discrete_sequence=["#ff7f0e"],
            )
            fig_hist.add_vline(
                x=1000,
                line_dash="dash",
                line_color="red",
                annotation_text="Межа комфорту",
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    
        # Heatmap
        corr = df_ml.select_dtypes(include="number").corr()
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="RdBu_r",
            title="Матриця кореляцій",
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    
        with st.expander("Сирі дані датасету"):
            st.dataframe(df_ml.tail(100))
    else:
        st.info(
            "Датасет `data/training_dataset.csv` поки порожній. Запустіть генерацію даних."
        )
    
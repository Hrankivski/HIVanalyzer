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
    st.header("AI Advisor (Decision Support System)")
    st.write(
        "Цей модуль порівнює класичне керування (рекуператор на 100%) з інтелектуальним керуванням (AI Auto-Pilot) на проміжку 24 годин."
    )
    
    from ai import ai_engine
    
    ppo_model = ai_engine.load_ai_model()
    
    if not ppo_model:
        st.warning(
            "Штучний Інтелект ще не навчений. Будь ласка, запустіть базове тренування `train_agent.py`."
        )
    else:
        st.success("ШІ в мережі і готовий до роботи.")
    
        c1, c2 = st.columns([1, 2])
    
        with c1:
            st.subheader("Сценарій дня")
            occ = st.slider("Кількість людей", 0, 50, 10)
            room_vol = (room_l * room_w - room_l_cut * room_w_cut) * room_h
            room_config = {"occupants": occ, "volume": room_vol, "wall_thickness": 0.38}
    
            run_advisor = st.button("Прогнозувати (24 год)", type="primary")
    
        with c2:
            st.subheader("Пояснювальний ШІ (XAI)")
            xai_text_placeholder = st.empty()
            if not run_advisor:
                xai_text_placeholder.info("Очікування параметрів...")
    
        if run_advisor:
            with st.spinner("Симуляція математичної моделі..."):
                # Run Manual
                df_man, _, _, _, man_energy_pen = ai_engine.simulate_24h(
                    ppo_model, room_config, agent_controlled=False, fixed_device_idx=0
                )
    
                # Run AI
                df_ai, best_device_idx, pm_pen, co2_pen, ai_energy_pen = (
                    ai_engine.simulate_24h(
                        ppo_model, room_config, agent_controlled=True
                    )
                )
    
                import json
    
                with open("data/recuperator_db.json", "r", encoding="utf-8") as f:
                    db = json.load(f)
                best_device_name = db[best_device_idx]["name"]
    
                manual_energy_sum = df_man["energy_w"].sum()
                ai_energy_sum = df_ai["energy_w"].sum()
    
                xai_reasoning = ai_engine.generate_xai_explanation(
                    best_device_name,
                    pm_pen,
                    co2_pen,
                    ai_energy_pen,
                    manual_energy_sum,
                    ai_energy_sum,
                )
                xai_text_placeholder.success(xai_reasoning)
    
                st.subheader("Порівняльний Аналіз (Manual vs AI)")
    
                import plotly.graph_objects as go
    
                # Енергія
                fig_energy = go.Figure()
                fig_energy.add_trace(
                    go.Scatter(
                        x=df_man["hour"],
                        y=df_man["energy_w"],
                        mode="lines",
                        name="Звичайний Термостат (100%)",
                        line=dict(color="red", dash="dash"),
                    )
                )
                fig_energy.add_trace(
                    go.Scatter(
                        x=df_ai["hour"],
                        y=df_ai["energy_w"],
                        mode="lines",
                        name="AI Контролер",
                        line=dict(color="green", width=3),
                    )
                )
                fig_energy.update_layout(
                    title="Енергоспоживання (Вт)",
                    xaxis_title="Година доби",
                    yaxis_title="Споживання (Вт)",
                )
                st.plotly_chart(fig_energy, use_container_width=True)
    
                # CO2
                fig_co2 = go.Figure()
                fig_co2.add_trace(
                    go.Scatter(
                        x=df_man["hour"],
                        y=df_man["co2"],
                        mode="lines",
                        name="Звичайний Термостат",
                        line=dict(color="red", dash="dash"),
                    )
                )
                fig_co2.add_trace(
                    go.Scatter(
                        x=df_ai["hour"],
                        y=df_ai["co2"],
                        mode="lines",
                        name="AI Контролер",
                        line=dict(color="blue", width=3),
                    )
                )
                fig_co2.add_hline(
                    y=1000,
                    line_dash="dot",
                    annotation_text="Ліміт комфорту",
                    annotation_position="bottom right",
                )
                fig_co2.update_layout(
                    title="Рівень CO2 (ppm)",
                    xaxis_title="Година доби",
                    yaxis_title="Концентрація (ppm)",
                )
                st.plotly_chart(fig_co2, use_container_width=True)
    
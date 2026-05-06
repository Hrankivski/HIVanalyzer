import streamlit as st
from ai import ai_engine


def render(room_l, room_w, room_h, room_l_cut, room_w_cut):
    st.header("Інтелектуальний радник (AI Advisor)")
    st.write(
        "Цей модуль порівнює класичне керування (рекуператор на 100%) з інтелектуальним керуванням (AI Auto-Pilot) на проміжку 24 годин."
    )
    
    
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
                # Симуляція ручного керування
                df_man, _, _, _, man_energy_pen = ai_engine.simulate_24h(
                    ppo_model, room_config, agent_controlled=False, fixed_device_idx=0
                )
    
                # Симуляція інтелектуального керування
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
    
                st.subheader("Порівняльний аналіз (ручне керування vs інтелектуальний автопілот)")
    
                import plotly.graph_objects as go
    
                # Графік енергоспоживання
                fig_energy = go.Figure()
                fig_energy.add_trace(
                    go.Scatter(
                        x=df_man["hour"],
                        y=df_man["energy_w"],
                        mode="lines",
                        name="Термостат (100% потужності)",
                        line=dict(color="red", dash="dash"),
                    )
                )
                fig_energy.add_trace(
                    go.Scatter(
                        x=df_ai["hour"],
                        y=df_ai["energy_w"],
                        mode="lines",
                        name="Інтелектуальний контролер",
                        line=dict(color="green", width=3),
                    )
                )
                fig_energy.update_layout(
                    title="Енергоспоживання (Вт)",
                    xaxis_title="Година доби",
                    yaxis_title="Споживання (Вт)",
                )
                st.plotly_chart(fig_energy, use_container_width=True)
    
                # Графік динаміки CO₂
                fig_co2 = go.Figure()
                fig_co2.add_trace(
                    go.Scatter(
                        x=df_man["hour"],
                        y=df_man["co2"],
                        mode="lines",
                        name="Термостат (ручне керування)",
                        line=dict(color="red", dash="dash"),
                    )
                )
                fig_co2.add_trace(
                    go.Scatter(
                        x=df_ai["hour"],
                        y=df_ai["co2"],
                        mode="lines",
                        name="Інтелектуальний контролер",
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
                    title="Рівень CO₂ (ppm)",
                    xaxis_title="Година доби",
                    yaxis_title="Концентрація (ppm)",
                )
                st.plotly_chart(fig_co2, use_container_width=True)
    
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
    st.header("Лабораторія Штучного Інтелекту (Model-Based RL)")
    st.markdown(
        "Тут ви можете навчити Сурогатну Фізику на базі даних EnergyPlus, а потім дозволити PPO Агенту грати у цю гру мільйони разів, щоб знайти найкраще управління."
    )
    
    col_surr, col_ppo = st.columns(2)
    
    with col_surr:
        st.subheader("1. Навчання Сурогатної Моделі Світу")
        if st.button("Навчити Сурогатну Фізику (LightGBM)", type="primary"):
            with st.spinner("Навчання швидкої моделі..."):
                success, msg = ml_surrogate.train_surrogate(
                    "data/training_dataset.csv"
                )
                if success:
                    st.success("Сурогатна модель успішно навчена!")
                    c_score, c_met1, c_met2 = st.columns(3)
                    conf_score = max(
                        0, min(100, msg["surrogate_precision_r2"] * 100)
                    )
                    c_score.metric(
                        "Індекс Довіри (0-100%)",
                        f"{conf_score:.1f}%",
                        help="Наскільки відсотків модель відповідає EnergyPlus",
                    )
                    c_met1.metric(
                        "MAE (CO2)",
                        f"{msg['mae_co2']:.1f} ppm",
                        help="Середня абсолютна похибка",
                    )
                    c_met2.metric(
                        "RMSE (CO2)",
                        f"{msg['rmse_co2']:.1f} ppm",
                        help="Середньоквадратична похибка",
                    )
    
                    import plotly.graph_objects as go
    
                    fig_val = go.Figure()
                    fig_val.add_trace(
                        go.Scatter(
                            x=msg["y_test_co2"],
                            y=msg["y_pred_co2"],
                            mode="markers",
                            name="CO2 Predict vs Actual",
                            marker=dict(color="blue", opacity=0.5),
                        )
                    )
                    # Diagonal line
                    min_v = min(msg["y_test_co2"])
                    max_v = max(msg["y_test_co2"])
                    fig_val.add_trace(
                        go.Scatter(
                            x=[min_v, max_v],
                            y=[min_v, max_v],
                            mode="lines",
                            name="Ідеальний збіг",
                            line=dict(color="red", dash="dash"),
                        )
                    )
                    fig_val.update_layout(
                        title="Validation: Predicted vs Actual CO2",
                        xaxis_title="Справжній CO2 (E+)",
                        yaxis_title="Передбачений CO2 (LightGBM)",
                    )
                    st.plotly_chart(fig_val, use_container_width=True)
                else:
                    st.error(msg)
    
    with col_ppo:
        st.subheader("2. Тренування RL Агента (Мозок)")
        
        import multiprocessing
        try:
            import torch
            has_gpu = torch.cuda.is_available()
        except ImportError:
            has_gpu = False
        cores = multiprocessing.cpu_count()
        st.info(f"💻 **Hardware-Aware Оптимізація:** Знайдено **{cores} ядер CPU**. GPU: **{'Активно 🚀' if has_gpu else 'Відсутній'}**. \n\nВекторизація середовищ працюватиме у {cores} паралельних потоках на 100% потужності.")
        
        steps = st.number_input(
            "Кількість кроків (Timesteps)", 10000, 1000000, 50000, 10000
        )
        if st.button("Fine-tune PPO Агента", type="primary"):
            st_text = st.empty()
            st_progress = st.progress(0.0)
            st_chart = st.empty()
            with st.spinner(f"Агент проходить {steps} кроків..."):
                success, msg = rl_agent.train_rl_agent(
                    steps, st_progress, st_text, st_chart
                )
                if success:
                    st.success("Навчання завершено!")
                    st_progress.empty()
                    st_text.empty()
                else:
                    st.error(msg)
    
        st.markdown("---")
        if st.button("📊 Оцінити надійність Агента (Benchmark)", type="secondary"):
            from ai import ai_engine
    
            model = ai_engine.load_ai_model()
            if model:
                with st.spinner(
                    "Прогін тестового 24-годинного сценарію (Екстремальне навантаження)..."
                ):
                    room_vol = (room_l * room_w - room_l_cut * room_w_cut) * room_h
                    room_config = {
                        "occupants": 30,
                        "volume": room_vol,
                        "wall_thickness": 0.38,
                    }
                    df_ai, _, _, _, _ = ai_engine.simulate_24h(
                        model, room_config, agent_controlled=True
                    )
    
                    safe_pct = (df_ai["co2"] <= 1000).mean() * 100
                    reliability_score = max(0, min(100, safe_pct))
    
                    st.metric(
                        "Індекс Надійності Агента (0-100%)",
                        f"{reliability_score:.1f}%",
                        help="Відсоток часу, протягом якого агент зміг утримати CO2 в нормі при 30 людях у приміщенні.",
                    )
            else:
                st.error("Агент ще не навчений.")
    
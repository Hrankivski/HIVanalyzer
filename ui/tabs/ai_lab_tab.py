import streamlit as st

from ai import ai_engine, ml_surrogate, rl_agent


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
                            name="Порівняння CO₂: прогноз vs реальність",
                            marker=dict(color="blue", opacity=0.5),
                        )
                    )
                    # Діагональ ідеального збігу
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
                        title="Валідація сурогатної моделі: прогноз vs реальні значення CO₂",
                        xaxis_title="Реальне значення CO₂ (E+)",
                        yaxis_title="Прогноз CO₂ (LightGBM)",
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
        st.info(f"💻 **Апаратна оптимізація:** Знайдено **{cores} ядер CPU**. GPU: **{'Активно 🚀' if has_gpu else 'Відсутній'}**. \n\nВекторизація середовищ працюватиме у {cores} паралельних потоках на 100% потужності.")
        
        steps = st.number_input(
            "Кількість кроків (Timesteps)", 1000, 1000000, 50000, 10000
        )
        if st.button("Донавчати PPO-агента", type="primary"):
            import threading
            import time

            import pandas as pd

            # shared_state — спільний dict між daemon-потоком (пише callback)
            # та головним потоком Streamlit (читає і оновлює UI).
            # Це єдиний thread-safe спосіб показувати прогрес без WebSocket-помилок.
            shared_state = {
                "pct": 0.0,
                "num_timesteps": 0,
                "rewards": [],
                "steps": [],
            }
            _state = {"done": False, "success": False, "msg": ""}

            def _run():
                s, m = rl_agent.train_rl_agent(steps, shared_state=shared_state)
                _state.update(done=True, success=s, msg=m)

            thread = threading.Thread(target=_run, daemon=True)
            thread.start()

            status_txt = st.empty()
            prog_bar = st.progress(0.0)
            chart_placeholder = st.empty()

            while not _state["done"] and thread.is_alive():
                pct = shared_state["pct"]
                num_ts = shared_state["num_timesteps"]
                rewards = shared_state["rewards"]
                reward_steps = shared_state["steps"]

                try:
                    prog_bar.progress(min(pct, 1.0))
                    if pct >= 1.0:
                        status_txt.text(
                            f"Завершення: збір фінального буфера... ({num_ts} / {steps} кроків)"
                        )
                    else:
                        status_txt.text(
                            f"Прогрес навчання: {num_ts} / {steps} кроків ({int(pct * 100)}%)"
                        )
                    if len(rewards) >= 2:
                        df_chart = pd.DataFrame(
                            {"Середня нагорода": rewards}, index=reward_steps
                        )
                        chart_placeholder.line_chart(df_chart)
                except Exception:
                    pass  # WebSocket закритий — продовжуємо чекати
                time.sleep(1)

            thread.join(timeout=10)
            try:
                if _state["success"]:
                    ai_engine.clear_model_cache()
                    prog_bar.progress(1.0)
                    st.success(_state["msg"])
                elif _state["done"]:
                    st.error(_state["msg"])
                else:
                    st.warning("Навчання триває в фоні. Оновіть сторінку пізніше.")
            except Exception:
                pass  # Браузер відключився — модель вже збережена на диску
    
        st.markdown("---")
        if st.button("📊 Оцінити надійність агента (Бенчмарк)", type="secondary"):
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
    
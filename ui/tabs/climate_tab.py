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
    st.subheader("Клімат-контроль (Термостати)")
    c_temp1, c_temp2 = st.columns(2)
    with c_temp1:
        st.session_state.project_settings["target_temp_heat"] = st.slider(
            "Цільова темп. (Опалення) °C",
            10.0,
            25.0,
            st.session_state.project_settings.get("target_temp_heat", 20.0),
            0.5,
        )
    with c_temp2:
        st.session_state.project_settings["target_temp_cool"] = st.slider(
            "Цільова темп. (Охолодження) °C",
            18.0,
            30.0,
            st.session_state.project_settings.get("target_temp_cool", 24.0),
            0.5,
        )
    st.session_state.project_settings["hvac_power_limit"] = st.number_input(
        "Макс. потужність кондиціонера (Вт)",
        500,
        20000,
        st.session_state.project_settings.get("hvac_power_limit", 3000),
        500,
    )
    st.markdown("---")
    
    st.subheader("Параметри вентиляційної системи")
    st.session_state.project_settings["recuperator_efficiency"] = st.slider(
        "ККД теплообмінника (%)", 50.0, 98.0, 85.0
    )
    
    # Розрахунок необхідного повітря за ДБН
    required_air = (
        st.session_state.project_settings["occupants"]
        * constants.AIR_PHYSICS["fresh_air_standard"]
    )
    st.metric("Необхідний приплив повітря", f"{required_air} м³/год")
    
    st.markdown("### Розрахунок накопичення CO₂ (Математична модель)")
    # G * n
    total_co2_prod = (
        constants.AIR_PHYSICS["co2_production_active"]
        * st.session_state.project_settings["occupants"]
    )
    # Q * (Cin - Cout) for 1 hour approx, just showing the delta potential
    volume = (room_l * room_w - room_l_cut * room_w_cut) * room_h
    q_recup = st.slider(
        "Q: Потік повітря через рекуператор (м³/год)", 0.0, 500.0, required_air
    )
    c_in = st.number_input(
        "Поточна концентрація CO₂ всередині (ppm)", 400.0, 5000.0, 800.0
    )
    
    # Delta C = ( (G * n) - (Q * (Cin - Cout)*10^-3) ) / V * delta_t
    # (Simplified empirical scale for ppm)
    delta_c_ppm = (
        (total_co2_prod)
        - (q_recup * (c_in - constants.AIR_PHYSICS["outdoor_co2_ppm"]) * 0.001)
    ) / volume
    
    st.info(
        rf"**$\Delta C$ (Зміна концентрації за годину)**: {delta_c_ppm:.1f} ppm/год\n\n"
        rf"Формула: $\Delta C = \frac{{(G \cdot n) - (Q \cdot (C_{{in}} - C_{{out}}))}}{{V}} \cdot \Delta t$"
    )
    
    # Формула перерахунку температури
    eff = st.session_state.project_settings.get("recuperator_efficiency", 85.0) / 100.0
    t_in_default = constants.SIMULATION.get("default_temp_in", 20.0)
    t_out_default = constants.SIMULATION.get("default_temp_out", -5.0)
    t_sup = t_out_default + eff * (t_in_default - t_out_default)
    
    st.info(
        rf"**$T_{{sup}}$ (Температура припливного повітря після рекуперації)**: {t_sup:.1f} °C\n\n"
        rf"Формула: $T_{{sup}} = T_{{out}} + \eta \cdot (T_{{in}} - T_{{out}})$"
    )
    
    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        run_sim = st.button("Запустити розрахунок двійника")
    with col_sim2:
        run_ai = st.button("✨ Підібрати обладнання (AI)", type="primary")
    
    if run_ai:
        from ai import rl_agent
        import json
        import os
    
        st.info("Штучний Інтелект аналізує вашу кімнату. Запуск процесу адаптації...")
    
        room_vol = (room_l * room_w - room_l_cut * room_w_cut) * room_h
        wall_th = st.session_state.project_settings.get("wall_thickness", 0.38)
        occ = st.session_state.project_settings.get("occupants", 10)
    
        rc_config = {"volume": room_vol, "wall_thickness": wall_th, "occupants": occ}
    
        progress_bar = st.progress(0)
        status_text = st.empty()
    
        best_action, msg = rl_agent.finetune_and_predict(
            rc_config, timesteps=1000, st_progress=progress_bar, st_text=status_text
        )
    
        if best_action is not None:
            # We must load devices to get details
            db_path = "data/recuperator_db.json"
            if os.path.exists(db_path):
                import builtins
    
                with builtins.open(db_path, "r", encoding="utf-8") as f:
                    devices = json.load(f)
    
                device_idx, fan_idx = best_action
                best_device = devices[device_idx]
    
                # Injection into bridge settings
                st.session_state.project_settings["recuperator_max_flow_m3_h"] = (
                    best_device["max_flow_rate"]
                )
                st.session_state.project_settings["recuperator_efficiency"] = (
                    best_device["sensible_efficiency"] * 100
                )
                st.success(
                    f"**Ідеальне обладнання знайдено:** {best_device['name']} (Потік: {best_device['max_flow_rate']} м³/год, ККД: {int(best_device['sensible_efficiency'] * 100)}%).\nЗапускаємо валідацію в EnergyPlus..."
                )
                run_sim = True  # Automatically trigger the E+ simulation
            else:
                st.error("База `recuperator_db.json` не знайдена!")
        else:
            st.error(f"Помилка процесу: {msg}")
    
    if run_sim:
        with st.status("Процес симуляції...") as status:
            st.write("Генерація геометричної моделі...")
            json_data = designer.export_project(
                room_l, room_w, room_h, room_l_cut, room_w_cut
            )
            idf_data = idf_bridge.generate_idf_structure(json_data)
    
            st.write("Запуск термічного аналізу EnergyPlus...")
            eplus_path = st.session_state.project_settings.get(
                "eplus_exe", constants.SIMULATION["eplus_exe"]
            )
            epw_path = st.session_state.project_settings.get(
                "weather_file", constants.SIMULATION["weather_file"]
            )
            success, result_msg, temp_dir = simulation_engine.run_simulation(
                idf_data, eplus_exe=eplus_path, epw_path=epw_path
            )
    
            if success:
                st.write("Обробка даних...")
                df_res = simulation_engine.get_results(result_msg)
                if not df_res.empty:
                    st.success("Симуляція завершена успішно!")
    
                    st.subheader("📊 Результати симуляції")
                    col1, col2, col3 = st.columns(3)
                    avg_t_in = (
                        df_res["T_in (C)"].mean() if "T_in (C)" in df_res.columns else 0
                    )
                    max_co2 = (
                        df_res["CO2 (ppm)"].max()
                        if "CO2 (ppm)" in df_res.columns
                        else 0
                    )
                    avg_t_out = (
                        df_res["T_out (C)"].mean()
                        if "T_out (C)" in df_res.columns
                        else 0
                    )
    
                    col1.metric("Середня темп. всередині", f"{avg_t_in:.1f} °C")
                    col2.metric("Максимальний рівень CO₂", f"{max_co2:.0f} ppm")
                    col3.metric("Середня темп. надворі", f"{avg_t_out:.1f} °C")
    
                    aggregate_data = st.checkbox(
                        "Агрегація даних (згладжування графіків)", value=True
                    )
                    if aggregate_data:
                        numeric_df = df_res.select_dtypes(include="number")
                        df_plot = numeric_df.rolling(window=24, min_periods=1).mean()
                        if "Datetime" in df_res.columns:
                            df_plot["Datetime"] = df_res["Datetime"]
                    else:
                        df_plot = df_res
    
                    tab_temp, tab_co2, tab_air = st.tabs(
                        ["Температура", "CO₂", "Якість повітря"]
                    )
                    x_data = (
                        "Datetime" if "Datetime" in df_plot.columns else df_plot.index
                    )
                    x_col_name = (
                        "Datetime" if "Datetime" in df_plot.columns else "index"
                    )
                    x_label = "Дата і Час" if "Datetime" in df_plot.columns else "Шаг"
    
                    with tab_temp:
                        temp_cols = [
                            c for c in ["T_in (C)", "T_out (C)"] if c in df_plot.columns
                        ]
                        if temp_cols:
                            st.write("**За весь період (Глобальний тренд):**")
                            fig_temp_global = px.line(
                                df_plot,
                                y=temp_cols,
                                labels={
                                    "value": "Температура (°C)",
                                    "index": "Шаг",
                                    "variable": "Показник",
                                },
                                color_discrete_map={
                                    "T_in (C)": "#ff7f0e",
                                    "T_out (C)": "#1f77b4",
                                },
                            )
                            st.plotly_chart(fig_temp_global, use_container_width=True)
    
                            st.write(
                                "**Детальний перегляд (з тягарцем для масштабування):**"
                            )
                            fig_temp_zoom = px.line(
                                df_plot,
                                x=x_data,
                                y=temp_cols,
                                labels={
                                    "value": "Температура (°C)",
                                    x_col_name: x_label,
                                    "variable": "Показник",
                                },
                                color_discrete_map={
                                    "T_in (C)": "#ff7f0e",
                                    "T_out (C)": "#1f77b4",
                                },
                            )
                            fig_temp_zoom.update_xaxes(rangeslider_visible=True)
                            st.plotly_chart(fig_temp_zoom, use_container_width=True)
                        else:
                            st.warning("Дані температури відсутні")
    
                    with tab_co2:
                        if "CO2 (ppm)" in df_plot.columns:
                            st.write("**За весь період (Глобальний тренд):**")
                            fig_co2_global = px.line(
                                df_plot,
                                y="CO2 (ppm)",
                                labels={
                                    "value": "Концентрація CO₂ (ppm)",
                                    "index": "Шаг",
                                },
                                color_discrete_sequence=["#d62728"],
                            )
                            st.plotly_chart(fig_co2_global, use_container_width=True)
    
                            st.write(
                                "**Детальний перегляд (з тягарцем для масштабування):**"
                            )
                            fig_co2_zoom = px.line(
                                df_plot,
                                x=x_data,
                                y="CO2 (ppm)",
                                labels={
                                    "value": "Концентрація CO₂ (ppm)",
                                    x_col_name: x_label,
                                },
                                color_discrete_sequence=["#d62728"],
                            )
                            fig_co2_zoom.update_xaxes(rangeslider_visible=True)
                            st.plotly_chart(fig_co2_zoom, use_container_width=True)
    
                    with tab_air:
                        if "Generic Contaminant" in df_plot.columns:
                            st.write("**За весь період (Глобальний тренд):**")
                            fig_air_global = px.line(
                                df_plot,
                                y="Generic Contaminant",
                                labels={"value": "Концентрація (У.О.)", "index": "Шаг"},
                                color_discrete_sequence=["#9467bd"],
                            )
                            st.plotly_chart(fig_air_global, use_container_width=True)
    
                            st.write(
                                "**Детальний перегляд (з тягарцем для масштабування):**"
                            )
                            fig_air_zoom = px.line(
                                df_plot,
                                x=x_data,
                                y="Generic Contaminant",
                                labels={
                                    "value": "Концентрація (У.О.)",
                                    x_col_name: x_label,
                                },
                                color_discrete_sequence=["#9467bd"],
                            )
                            fig_air_zoom.update_xaxes(rangeslider_visible=True)
                            st.plotly_chart(fig_air_zoom, use_container_width=True)
                        else:
                            st.info(
                                "Дані про якість повітря (Generic Contaminants) відсутні."
                            )
    
                    st.info(
                        f"Файли симуляції (IDF, CSV, помилки) збережено в: {temp_dir}"
                    )
    
                    st.session_state["latest_df"] = df_res
                    st.session_state["latest_sim_dir"] = temp_dir
                else:
                    st.warning(
                        "Симуляція пройшла, але потрібних колонок не знайдено в eplusout.csv."
                    )
                status.update(label="Симуляція завершена", state="complete")
            else:
                st.error("Помилка симуляції EnergyPlus:")
                st.code(result_msg, language="text")
                status.update(label="Помилка симуляції", state="error")
    
    st.markdown("---")
    
    if "latest_df" in st.session_state and not st.session_state["latest_df"].empty:
        st.subheader("Перевірка реалістичності симуляції (Phase 8.1)")
        if st.button("🔍 Validate Simulation Realism"):
            with st.spinner("Аналіз фізичних законів та аномалій..."):
                val = validator.ModelValidator()
                results = val.run_all_tests(
                    st.session_state["latest_df"],
                    st.session_state.get("latest_sim_dir"),
                )
    
                # Radar Chart Data
                radar_data = []
                for r in results:
                    if r["status"] == "Pass":
                        score = 100
                    elif r["status"] == "Warning":
                        score = 50
                    else:
                        score = 0
    
                    # Shorten name for chart if needed
                    radar_data.append(dict(score=score, name=r["name"].split(" (")[0]))
    
                df_radar = pd.DataFrame(radar_data)
    
                st.markdown("### 📊 Радарна Діаграма Реалістичності")
                st.info(
                    "Ця діаграма показує загальну оцінку достовірності моделі. 100% означає, що фізичні метрики ціком реалістичні."
                )
                fig = px.line_polar(
                    df_radar, r="score", theta="name", line_close=True, range_r=[0, 100]
                )
                fig.update_traces(fill="toself", line_color="#4CAF50")
                st.plotly_chart(fig, use_container_width=True)
    
                st.markdown("### Детальний Звіт з Валідації")
                for r in results:
                    val_str = (
                        f"**Значення:** {r['value']:.2f}"
                        if isinstance(r["value"], float)
                        else f"**Значення:** {r['value']}"
                    )
    
                    if r["status"] == "Pass":
                        st.success(f"✅ **{r['name']}**\n\n{r['message']}\n\n{val_str}")
                    elif r["status"] == "Warning":
                        st.warning(f"⚠️ **{r['name']}**\n\n{r['message']}\n\n{val_str}")
                    else:
                        st.error(f"❌ **{r['name']}**\n\n{r['message']}\n\n{val_str}")
    
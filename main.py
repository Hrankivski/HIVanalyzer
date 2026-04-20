import streamlit as st
import pandas as pd
import plotly.express as px
import designer
import json
import constants
import idf_bridge
import simulation_engine
import datetime
import validator

st.set_page_config(page_title="Recuperator Optimizer", layout="wide")
designer.init_session_state()

# --- SIDEBAR: ВВІД ПАРАМЕТРІВ ---
st.sidebar.header("Конфігурація системи")
with st.sidebar.expander("Шляхи EnergyPlus"):
    st.session_state.project_settings["eplus_exe"] = st.text_input(
        "Шлях до energyplus.exe", 
        st.session_state.project_settings.get("eplus_exe", constants.SIMULATION["eplus_exe"])
    )
    st.session_state.project_settings["weather_file"] = st.text_input(
        "Шлях до файлу погоди", 
        st.session_state.project_settings.get("weather_file", constants.SIMULATION["weather_file"])
    )

st.sidebar.markdown("---")
if st.sidebar.button("Завантажити налаштування з data/default.json"):
    designer.load_default_project("data/default.json")
    st.session_state["default_loaded"] = True

st.sidebar.header("Геометрія та матеріали")
room_l = st.sidebar.number_input(
    "Загальна Довжина L (м)", 2.0, 30.0,
    st.session_state.project_settings.get("room_l", 8.0), 0.1,
    key="room_l"
)
room_w = st.sidebar.number_input(
    "Загальна Ширина W (м)", 2.0, 30.0,
    st.session_state.project_settings.get("room_w", 6.0), 0.1,
    key="room_w"
)
room_l_cut = st.sidebar.number_input(
    "Виріз L_cut (м)", 0.0, 20.0,
    st.session_state.project_settings.get("room_l_cut", 3.0), 0.1,
    key="room_l_cut"
)
room_w_cut = st.sidebar.number_input(
    "Виріз W_cut (м)", 0.0, 20.0,
    st.session_state.project_settings.get("room_w_cut", 3.0), 0.1,
    key="room_w_cut"
)
room_h = st.sidebar.number_input(
    "Висота H (м)", 2.0, 5.0,
    st.session_state.project_settings.get("room_h", 2.8), 0.1,
    key="room_h"
)

st.session_state.project_settings["room_l"] = room_l
st.session_state.project_settings["room_w"] = room_w
st.session_state.project_settings["room_l_cut"] = room_l_cut
st.session_state.project_settings["room_w_cut"] = room_w_cut
st.session_state.project_settings["room_h"] = room_h

with st.sidebar.expander("Характеристики конструкцій"):
    mat_options = list(constants.MATERIALS.keys())
    st.session_state.project_settings["wall_material"] = st.selectbox(
        "Матеріал стін", mat_options,
        index=mat_options.index(st.session_state.project_settings.get("wall_material", mat_options[0]))
    )
    
    # Display material properties
    sel_mat_props = constants.MATERIALS[st.session_state.project_settings["wall_material"]]
    st.info(f"λ (Теплопровідність): {sel_mat_props['conductivity']} Вт/м·К\n\n"
            f"ρ (Густина): {sel_mat_props['density']} кг/м³\n\n"
            f"c (Теплоємність): {sel_mat_props['specific_heat']} Дж/кг·К")
            
    st.session_state.project_settings["wall_thickness"] = st.number_input(
        "Товщина стін (м)", 0.1, 1.0, 0.38
    )
    
    st.markdown("Налаштування стін (Г-форма: 6 стін):")
    wall_labels = ["Нижня", "Права", "Внутр. Верхня", "Внутр. Права", "Верхня", "Ліва"]
    for i, label in enumerate(wall_labels):
        c1, c2 = st.columns([1, 1])
        st.session_state.project_settings[f"wall_type_{i}"] = c1.selectbox(
            f"{label}", ["Зовнішня", "Внутрішня"], 
            index=0 if st.session_state.project_settings.get(f"wall_type_{i}", "Зовнішня") == "Зовнішня" else 1, 
            key=f"w_type_{i}"
        )
        st.session_state.project_settings[f"wall_mat_{i}"] = c2.selectbox(
            f"Мат.", ["Базовий", "Скло"], 
            index=0 if st.session_state.project_settings.get(f"wall_mat_{i}", "Базовий") == "Базовий" else 1, 
            key=f"w_mat_{i}"
        )

st.sidebar.markdown("---")
st.sidebar.header("Експлуатація приміщення")
room_occupants_default = st.session_state.project_settings.get("occupants", 10)
room_activity_default = st.session_state.project_settings.get("activity_level", "Офісна робота")

occupants = st.sidebar.number_input(
    "Кількість людей", 0, 100, room_occupants_default,
    key="occupants"
)
activity_options = ["Відпочинок", "Офісна робота", "Легка праця", "Важка праця"]
activity_index = activity_options.index(room_activity_default) if room_activity_default in activity_options else 1
activity_level = st.sidebar.selectbox(
    "Тип активності", activity_options,
    index=activity_index,
    key="activity_level"
)

st.session_state.project_settings["occupants"] = occupants
st.session_state.project_settings["activity_level"] = activity_level

# --- УПРАВЛІННЯ ЕЛЕМЕНТАМИ ---
st.sidebar.markdown("---")
col_add1, col_add2, col_add3 = st.sidebar.columns(3)
if col_add1.button("Вікно"): designer.add_element("Вікно", room_l, room_w)
if col_add2.button("Рекуператор"): designer.add_element("Рекуператор", room_l, room_w)
if col_add3.button("Джерело тепла"): designer.add_element("Джерело тепла", room_l, room_w)

if not st.session_state.elements_df.empty:
    for i in range(len(st.session_state.elements_df)):
        with st.sidebar.expander(f"Об'єкт {st.session_state.elements_df.at[i, 'Тип']} {i + 1}"):
            def snap_to(idx, x_val=None, y_val=None, orient=None):
                if x_val is not None: st.session_state[f"x_{idx}"] = float(x_val)
                if y_val is not None: st.session_state[f"y_{idx}"] = float(y_val)
                if orient is not None: st.session_state[f"orient_{idx}"] = orient


            st.write("Прив'язка:")
            bc1, bc2, bc3, bc4 = st.columns(4)
            if bc1.button("Низ", key=f"b_b_{i}"): snap_to(i, y_val=0, orient="Горизонтально")
            if bc2.button("Верх", key=f"b_t_{i}"): snap_to(i, y_val=room_w, orient="Горизонтально")
            if bc3.button("Ліво", key=f"b_l_{i}"): snap_to(i, x_val=0, orient="Вертикально")
            if bc4.button("Право", key=f"b_r_{i}"): snap_to(i, x_val=room_l, orient="Вертикально")

            st.session_state.elements_df.at[i, 'Орієнтація'] = st.radio(
                "Орієнтація", ["Горизонтально", "Вертикально"],
                index=0 if st.session_state.get(f"orient_{i}", "Горизонтально") == "Горизонтально" else 1,
                key=f"orient_{i}"
            )
            current_x = st.session_state.get(f"x_{i}", float(st.session_state.elements_df.at[i, 'X']))
            current_y = st.session_state.get(f"y_{i}", float(st.session_state.elements_df.at[i, 'Y']))
            st.session_state.elements_df.at[i, 'X'] = st.slider("X (м)", 0.0, room_l, value=current_x, key=f"x_{i}")
            st.session_state.elements_df.at[i, 'Y'] = st.slider("Y (м)", 0.0, room_w, value=current_y, key=f"y_{i}")
            st.session_state.elements_df.at[i, 'Орієнтація'] = st.session_state.get(f"orient_{i}", st.session_state.elements_df.at[i, 'Орієнтація'])
            st.session_state.elements_df.at[i, 'Ширина'] = st.session_state.get(f"width_{i}", float(st.session_state.elements_df.at[i, 'Ширина']))
            if st.session_state.elements_df.at[i, 'Тип'] == "Джерело тепла":
                if 'Потужність' not in st.session_state.elements_df.columns:
                    st.session_state.elements_df['Потужність'] = pd.Series([1000.0] * len(st.session_state.elements_df))
                
                curr_pow = st.session_state.elements_df.at[i, 'Потужність']
                st.session_state.elements_df.at[i, 'Потужність'] = st.slider("Потужність (Вт)", 100.0, 5000.0, float(curr_pow) if pd.notnull(curr_pow) else 1000.0, key=f"power_{i}")
            else:
                st.session_state.elements_df.at[i, 'Ширина'] = st.slider("Ширина (м)", 0.1, 5.0, float(st.session_state.elements_df.at[i, 'Ширина']), key=f"width_{i}")

            if st.button("Видалити", key=f"del_{i}"):
                st.session_state.elements_df = st.session_state.elements_df.drop(i).reset_index(drop=True)
                st.experimental_rerun() if hasattr(st, 'experimental_rerun') else st.stop()

# --- ОСНОВНИЙ РОБОЧИЙ ПРОСТІР ---
tab1, tab2, tab3, tab4 = st.tabs(["Геометрія", "Симуляція", "Збереження", "Machine Learning"])

with tab1:
    fig = designer.render_blueprint(room_l, room_w, room_l_cut, room_w_cut, st.session_state.elements_df)
    st.plotly_chart(fig, width='stretch')

with tab2:
    st.subheader("Параметри вентиляційної системи")
    st.session_state.project_settings["recuperator_efficiency"] = st.slider(
        "ККД теплообмінника (%)", 50.0, 98.0, 85.0
    )

    # Розрахунок необхідного повітря за ДБН
    required_air = st.session_state.project_settings["occupants"] * constants.AIR_PHYSICS["fresh_air_standard"]
    st.metric("Необхідний приплив повітря", f"{required_air} м³/год")

    st.markdown("### Розрахунок накопичення CO₂ (Математична модель)")
    # G * n
    total_co2_prod = constants.AIR_PHYSICS["co2_production_active"] * st.session_state.project_settings["occupants"]
    # Q * (Cin - Cout) for 1 hour approx, just showing the delta potential
    volume = (room_l * room_w - room_l_cut * room_w_cut) * room_h
    q_recup = st.slider("Q: Потік повітря через рекуператор (м³/год)", 0.0, 500.0, required_air)
    c_in = st.number_input("Поточна концентрація CO₂ всередині (ppm)", 400.0, 5000.0, 800.0)
    
    # Delta C = ( (G * n) - (Q * (Cin - Cout)*10^-3) ) / V * delta_t
    # (Simplified empirical scale for ppm)
    delta_c_ppm = ((total_co2_prod) - (q_recup * (c_in - constants.AIR_PHYSICS["outdoor_co2_ppm"]) * 0.001)) / volume
    
    st.info(rf"**$\Delta C$ (Зміна концентрації за годину)**: {delta_c_ppm:.1f} ppm/год\n\n"
            rf"Формула: $\Delta C = \frac{{(G \cdot n) - (Q \cdot (C_{{in}} - C_{{out}}))}}{{V}} \cdot \Delta t$")

    # Формула перерахунку температури
    eff = st.session_state.project_settings.get("recuperator_efficiency", 85.0) / 100.0
    t_in_default = constants.SIMULATION.get("default_temp_in", 20.0)
    t_out_default = constants.SIMULATION.get("default_temp_out", -5.0)
    t_sup = t_out_default + eff * (t_in_default - t_out_default)
    
    st.info(rf"**$T_{{sup}}$ (Температура припливного повітря після рекуперації)**: {t_sup:.1f} °C\n\n"
            rf"Формула: $T_{{sup}} = T_{{out}} + \eta \cdot (T_{{in}} - T_{{out}})$")

    if st.button("Запустити розрахунок двійника"):
        with st.status("Процес симуляції...") as status:
            st.write("Генерація геометричної моделі...")
            json_data = designer.export_project(room_l, room_w, room_h, room_l_cut, room_w_cut)
            idf_data = idf_bridge.generate_idf_structure(json_data)
            
            st.write("Запуск термічного аналізу EnergyPlus...")
            eplus_path = st.session_state.project_settings.get("eplus_exe", constants.SIMULATION["eplus_exe"])
            epw_path = st.session_state.project_settings.get("weather_file", constants.SIMULATION["weather_file"])
            success, result_msg, temp_dir = simulation_engine.run_simulation(idf_data, eplus_exe=eplus_path, epw_path=epw_path)
            
            if success:
                st.write("Обробка даних...")
                df_res = simulation_engine.get_results(result_msg)
                if not df_res.empty:
                    st.success("Симуляція завершена успішно!")
                    
                    st.subheader("📊 Результати симуляції")
                    col1, col2, col3 = st.columns(3)
                    avg_t_in = df_res["T_in (C)"].mean() if "T_in (C)" in df_res.columns else 0
                    max_co2 = df_res["CO2 (ppm)"].max() if "CO2 (ppm)" in df_res.columns else 0
                    avg_t_out = df_res["T_out (C)"].mean() if "T_out (C)" in df_res.columns else 0
                    
                    col1.metric("Середня темп. всередині", f"{avg_t_in:.1f} °C")
                    col2.metric("Максимальний рівень CO₂", f"{max_co2:.0f} ppm")
                    col3.metric("Середня темп. надворі", f"{avg_t_out:.1f} °C")
                    
                    aggregate_data = st.checkbox("Агрегація даних (згладжування графіків)", value=True)
                    if aggregate_data:
                        numeric_df = df_res.select_dtypes(include='number')
                        df_plot = numeric_df.rolling(window=24, min_periods=1).mean()
                        if "Datetime" in df_res.columns:
                            df_plot["Datetime"] = df_res["Datetime"]
                    else:
                        df_plot = df_res

                    tab_temp, tab_co2, tab_air = st.tabs(["Температура", "CO₂", "Якість повітря"])
                    x_data = "Datetime" if "Datetime" in df_plot.columns else df_plot.index
                    x_col_name = "Datetime" if "Datetime" in df_plot.columns else "index"
                    x_label = "Дата і Час" if "Datetime" in df_plot.columns else "Шаг"

                    with tab_temp:
                        temp_cols = [c for c in ["T_in (C)", "T_out (C)"] if c in df_plot.columns]
                        if temp_cols:
                            st.write("**За весь період (Глобальний тренд):**")
                            fig_temp_global = px.line(df_plot, y=temp_cols, 
                                             labels={"value": "Температура (°C)", "index": "Шаг", "variable": "Показник"},
                                             color_discrete_map={"T_in (C)": "#ff7f0e", "T_out (C)": "#1f77b4"})
                            st.plotly_chart(fig_temp_global, use_container_width=True)
                            
                            st.write("**Детальний перегляд (з тягарцем для масштабування):**")
                            fig_temp_zoom = px.line(df_plot, x=x_data, y=temp_cols,
                                             labels={"value": "Температура (°C)", x_col_name: x_label, "variable": "Показник"},
                                             color_discrete_map={"T_in (C)": "#ff7f0e", "T_out (C)": "#1f77b4"})
                            fig_temp_zoom.update_xaxes(rangeslider_visible=True)
                            st.plotly_chart(fig_temp_zoom, use_container_width=True)
                        else:
                            st.warning("Дані температури відсутні")
                            
                    with tab_co2:
                        if "CO2 (ppm)" in df_plot.columns:
                            st.write("**За весь період (Глобальний тренд):**")
                            fig_co2_global = px.line(df_plot, y="CO2 (ppm)", 
                                            labels={"value": "Концентрація CO₂ (ppm)", "index": "Шаг"},
                                            color_discrete_sequence=["#d62728"])
                            st.plotly_chart(fig_co2_global, use_container_width=True)
                            
                            st.write("**Детальний перегляд (з тягарцем для масштабування):**")
                            fig_co2_zoom = px.line(df_plot, x=x_data, y="CO2 (ppm)",
                                            labels={"value": "Концентрація CO₂ (ppm)", x_col_name: x_label},
                                            color_discrete_sequence=["#d62728"])
                            fig_co2_zoom.update_xaxes(rangeslider_visible=True)
                            st.plotly_chart(fig_co2_zoom, use_container_width=True)

                    with tab_air:
                        if "Generic Contaminant" in df_plot.columns:
                            st.write("**За весь період (Глобальний тренд):**")
                            fig_air_global = px.line(df_plot, y="Generic Contaminant", 
                                            labels={"value": "Концентрація (У.О.)", "index": "Шаг"},
                                            color_discrete_sequence=["#9467bd"])
                            st.plotly_chart(fig_air_global, use_container_width=True)
                            
                            st.write("**Детальний перегляд (з тягарцем для масштабування):**")
                            fig_air_zoom = px.line(df_plot, x=x_data, y="Generic Contaminant",
                                            labels={"value": "Концентрація (У.О.)", x_col_name: x_label},
                                            color_discrete_sequence=["#9467bd"])
                            fig_air_zoom.update_xaxes(rangeslider_visible=True)
                            st.plotly_chart(fig_air_zoom, use_container_width=True)
                        else:
                            st.info("Дані про якість повітря (Generic Contaminants) відсутні.")


                    simulation_engine.log_simulation_data(json_data, df_res)
                    st.info(f"Дані збережено для ML в data/training_data.csv")
                    st.info(f"Файли симуляції (IDF, CSV, помилки) збережено в: {temp_dir}")
                    
                    st.session_state["latest_df"] = df_res
                    st.session_state["latest_sim_dir"] = temp_dir
                else:
                    st.warning("Симуляція пройшла, але потрібних колонок не знайдено в eplusout.csv.")
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
                results = val.run_all_tests(st.session_state["latest_df"], st.session_state.get("latest_sim_dir"))
                
                # Radar Chart Data
                radar_data = []
                for r in results:
                    if r["status"] == "Pass": score = 100
                    elif r["status"] == "Warning": score = 50
                    else: score = 0
                    
                    # Shorten name for chart if needed
                    radar_data.append(dict(score=score, name=r["name"].split(" (")[0]))
                
                df_radar = pd.DataFrame(radar_data)
                
                st.markdown("### 📊 Радарна Діаграма Реалістичності")
                st.info("Ця діаграма показує загальну оцінку достовірності моделі. 100% означає, що фізичні метрики ціком реалістичні.")
                fig = px.line_polar(df_radar, r='score', theta='name', line_close=True, range_r=[0, 100])
                fig.update_traces(fill='toself', line_color='#4CAF50')
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("### Детальний Звіт з Валідації")
                for r in results:
                    val_str = f"**Значення:** {r['value']:.2f}" if isinstance(r['value'], float) else f"**Значення:** {r['value']}"
                    
                    if r["status"] == "Pass":
                        st.success(f"✅ **{r['name']}**\n\n{r['message']}\n\n{val_str}")
                    elif r["status"] == "Warning":
                        st.warning(f"⚠️ **{r['name']}**\n\n{r['message']}\n\n{val_str}")
                    else:
                        st.error(f"❌ **{r['name']}**\n\n{r['message']}\n\n{val_str}")

with tab3:
    st.subheader("Управління файлом проєкту")
    json_data = designer.export_project(room_l, room_w, room_h, room_l_cut, room_w_cut)
    st.download_button(
        label="Завантажити проєкт у JSON",
        data=json_data,
        file_name="project_twin.json",
        mime="application/json"
    )
    
    idf_data = idf_bridge.generate_idf_structure(json_data)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="Завантажити IDF (EnergyPlus)",
        data=idf_data,
        file_name=f"simulation_{timestamp}.idf",
        mime="text/plain"
    )
    
    st.markdown("### Попередній перегляд маніфесту IDF")
    st.text_area("IDF Structure", idf_data, height=400)

with tab4:
    st.subheader("Генератор синтетичних даних (Big Data)")
    st.write("Тут ви можете запустити пакетну симуляцію для випадкового варіювання параметрів та збору датасету для нейромережі.")
    n_sims = st.number_input("Кількість симуляцій (Batch Size)", 5, 500, 50)
    
    if st.button(f"Generate Training Data (Batch {n_sims})"):
        with st.status(f"Запуск {n_sims} симуляцій у фоні...") as status:
            json_data = designer.export_project(room_l, room_w, room_h, room_l_cut, room_w_cut)
            eplus_path = st.session_state.project_settings.get("eplus_exe", constants.SIMULATION["eplus_exe"])
            epw_path = st.session_state.project_settings.get("weather_file", constants.SIMULATION["weather_file"])
            
            runner = simulation_engine.SimulationRunner(json_data, eplus_path, epw_path)
            success, count = runner.run_batch(n_sims)
            
            if success:
                status.update(label=f"Успішно зібрано {count} записів!", state="complete")
            else:
                status.update(label="Помилка пакетної симуляції", state="error")
                
    st.markdown("---")
    st.subheader("Feature Importance (Кореляційна матриця)")
    import os
    if os.path.exists("data/training_dataset.csv"):
        df_ml = pd.read_csv("data/training_dataset.csv")
        st.write(f"У датасеті зараз **{len(df_ml)}** записів.")
        
        # Lazy Loading Table
        with st.expander("Попередній перегляд датасету"):
            st.dataframe(df_ml.tail(100))
            
        # Візуалізація Heatmap
        corr = df_ml.corr()
        fig_corr = px.imshow(corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", title="Матриця кореляцій (Вплив фіч на рівень CO2 та температуру)")
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Датасет `data/training_dataset.csv` поки порожній. Запустіть генерацію даних.")
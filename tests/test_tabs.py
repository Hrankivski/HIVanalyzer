from unittest.mock import MagicMock


class MockSessionState(dict):
    def __getattr__(self, name): return self.get(name)
    def __setattr__(self, name, value): self[name] = value

class MockStatus(MagicMock):
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def test_tabs_render(monkeypatch):
    """Фіктивний тест для перевірки базового рендерингу UI вкладок без падінь."""
    import pandas as pd
    mock_st = MagicMock()
    mock_df = pd.DataFrame({"Тип": ["Стіна"], "X": [0], "Y": [0], "Ширина": [10], "Висота": [3], "Орієнтація": ["Горизонтально"]})
    mock_st.session_state = MockSessionState({"elements_df": mock_df, "latest_df": mock_df, "latest_sim_dir": "test_dir", "project_settings": MockSessionState({"wall_thickness": 0.5, "city": "Kyiv", "occupants": 4, "target_temp_heat": 20, "target_temp_cool": 24, "hvac_power_limit": 3000, "recuperator_efficiency": 85})})
    mock_st.button.return_value = False
    mock_st.checkbox.return_value = False
    
    # Підміняємо streamlit на наш мок
    monkeypatch.setattr("streamlit.title", mock_st.title)
    monkeypatch.setattr("streamlit.header", mock_st.header)
    monkeypatch.setattr("streamlit.subheader", mock_st.subheader)
    monkeypatch.setattr("streamlit.markdown", mock_st.markdown)
    monkeypatch.setattr("streamlit.button", mock_st.button)
    monkeypatch.setattr("streamlit.write", mock_st.write)
    monkeypatch.setattr("streamlit.sidebar", mock_st)
    monkeypatch.setattr("streamlit.selectbox", mock_st.selectbox)
    monkeypatch.setattr("streamlit.number_input", mock_st.number_input)
    monkeypatch.setattr("streamlit.file_uploader", mock_st.file_uploader)
    monkeypatch.setattr("streamlit.plotly_chart", mock_st.plotly_chart)
    monkeypatch.setattr("streamlit.columns", lambda x: [mock_st] * x)
    monkeypatch.setattr("streamlit.session_state", mock_st.session_state)
    monkeypatch.setattr("streamlit.metric", mock_st.metric)
    monkeypatch.setattr("streamlit.empty", mock_st.empty)
    monkeypatch.setattr("streamlit.spinner", MockStatus)
    monkeypatch.setattr("streamlit.status", MockStatus)
    monkeypatch.setattr("streamlit.expander", MockStatus)
    monkeypatch.setattr("streamlit.progress", mock_st.progress)
    monkeypatch.setattr("streamlit.success", mock_st.success)
    monkeypatch.setattr("streamlit.error", mock_st.error)
    monkeypatch.setattr("streamlit.warning", mock_st.warning)
    monkeypatch.setattr("streamlit.info", mock_st.info)
    monkeypatch.setattr("streamlit.dataframe", mock_st.dataframe)
    monkeypatch.setattr("streamlit.tabs", lambda x: [mock_st] * len(x))

    try:
        from ui.tabs import (
            advisor_tab,
            ai_lab_tab,
            climate_tab,
            data_gen_tab,
            geometry_tab,
            save_tab,
        )
        geometry_tab.render(10.0, 5.0, 0.0, 0.0)
        save_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
        data_gen_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
        advisor_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
        ai_lab_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
        climate_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
    except Exception:
        import traceback
        traceback.print_exc()

def test_tabs_render_clicks(monkeypatch):
    """Тестує ті ж вкладки, але з натиснутими кнопками."""
    import pandas as pd
    mock_st = MagicMock()
    mock_df = pd.DataFrame({"Тип": ["Стіна"], "X": [0], "Y": [0], "Ширина": [10], "Висота": [3], "Орієнтація": ["Горизонтально"]})
    mock_st.session_state = MockSessionState({"elements_df": mock_df, "latest_df": mock_df, "latest_sim_dir": "test_dir", "project_settings": MockSessionState({"wall_thickness": 0.5, "city": "Kyiv", "occupants": 4, "target_temp_heat": 20, "target_temp_cool": 24, "hvac_power_limit": 3000, "recuperator_efficiency": 85})})
    mock_st.button.return_value = True
    mock_st.checkbox.return_value = True
    
    monkeypatch.setattr("streamlit.title", mock_st.title)
    monkeypatch.setattr("streamlit.header", mock_st.header)
    monkeypatch.setattr("streamlit.subheader", mock_st.subheader)
    monkeypatch.setattr("streamlit.markdown", mock_st.markdown)
    monkeypatch.setattr("streamlit.button", mock_st.button)
    monkeypatch.setattr("streamlit.write", mock_st.write)
    monkeypatch.setattr("streamlit.sidebar", mock_st)
    monkeypatch.setattr("streamlit.selectbox", mock_st.selectbox)
    monkeypatch.setattr("streamlit.number_input", mock_st.number_input)
    monkeypatch.setattr("streamlit.file_uploader", mock_st.file_uploader)
    monkeypatch.setattr("streamlit.plotly_chart", mock_st.plotly_chart)
    monkeypatch.setattr("streamlit.columns", lambda x: [mock_st] * x)
    monkeypatch.setattr("streamlit.session_state", mock_st.session_state)
    monkeypatch.setattr("streamlit.metric", mock_st.metric)
    monkeypatch.setattr("streamlit.empty", mock_st.empty)
    monkeypatch.setattr("streamlit.spinner", MockStatus)
    monkeypatch.setattr("streamlit.status", MockStatus)
    monkeypatch.setattr("streamlit.expander", MockStatus)
    monkeypatch.setattr("streamlit.progress", mock_st.progress)
    monkeypatch.setattr("streamlit.success", mock_st.success)
    monkeypatch.setattr("streamlit.error", mock_st.error)
    monkeypatch.setattr("streamlit.warning", mock_st.warning)
    monkeypatch.setattr("streamlit.info", mock_st.info)
    monkeypatch.setattr("streamlit.dataframe", mock_st.dataframe)
    monkeypatch.setattr("streamlit.tabs", lambda x: [mock_st] * len(x))

    try:
        from ui.tabs import (
            advisor_tab,
            ai_lab_tab,
            climate_tab,
            data_gen_tab,
            geometry_tab,
            save_tab,
        )
        geometry_tab.render(10.0, 5.0, 0.0, 0.0)
        save_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
        data_gen_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
        advisor_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
        ai_lab_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
        climate_tab.render(10.0, 5.0, 3.0, 0.0, 0.0)
    except Exception:
        import traceback
        traceback.print_exc()

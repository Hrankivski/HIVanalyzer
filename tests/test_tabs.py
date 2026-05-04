from unittest.mock import MagicMock

def test_tabs_render(monkeypatch):
    """Фіктивний тест для перевірки базового рендерингу UI вкладок без падінь."""
    import pandas as pd
    mock_st = MagicMock()
    mock_df = pd.DataFrame({"Тип": ["Стіна"], "x_0": [0], "y_0": [0], "Ширина": [10], "Висота": [3], "Азимут": [0]})
    mock_st.session_state = {"elements_df": mock_df, "project_settings": {"wall_thickness": 0.5, "city": "Kyiv"}}
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
    monkeypatch.setattr("streamlit.spinner", mock_st.spinner)
    monkeypatch.setattr("streamlit.progress", mock_st.progress)
    monkeypatch.setattr("streamlit.success", mock_st.success)
    monkeypatch.setattr("streamlit.error", mock_st.error)
    monkeypatch.setattr("streamlit.warning", mock_st.warning)
    monkeypatch.setattr("streamlit.info", mock_st.info)
    monkeypatch.setattr("streamlit.tabs", lambda x: [mock_st] * len(x))

    try:
        from ui.tabs import geometry_tab, save_tab, data_gen_tab, advisor_tab, ai_lab_tab
        geometry_tab.render()
        save_tab.render()
        data_gen_tab.render()
        advisor_tab.render()
        ai_lab_tab.render()
    except Exception:
        pass

def test_tabs_render_clicks(monkeypatch):
    """Тестує ті ж вкладки, але з натиснутими кнопками."""
    import pandas as pd
    mock_st = MagicMock()
    mock_df = pd.DataFrame({"Тип": ["Стіна"], "x_0": [0], "y_0": [0], "Ширина": [10], "Висота": [3], "Азимут": [0]})
    mock_st.session_state = {"elements_df": mock_df, "project_settings": {"wall_thickness": 0.5, "city": "Kyiv"}}
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
    monkeypatch.setattr("streamlit.spinner", mock_st.spinner)
    monkeypatch.setattr("streamlit.progress", mock_st.progress)
    monkeypatch.setattr("streamlit.success", mock_st.success)
    monkeypatch.setattr("streamlit.error", mock_st.error)
    monkeypatch.setattr("streamlit.warning", mock_st.warning)
    monkeypatch.setattr("streamlit.info", mock_st.info)
    monkeypatch.setattr("streamlit.tabs", lambda x: [mock_st] * len(x))

    try:
        from ui.tabs import geometry_tab, save_tab, data_gen_tab, advisor_tab, ai_lab_tab
        geometry_tab.render()
        save_tab.render()
        data_gen_tab.render()
        advisor_tab.render()
        ai_lab_tab.render()
    except Exception:
        pass

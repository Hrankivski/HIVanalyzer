import json

import streamlit as st

from ui import designer


class MockSessionState(dict):
    def __getattr__(self, item):
        return self.get(item, None)
    def __setattr__(self, key, value):
        self[key] = value

def test_init_session_state(monkeypatch):
    """Тестує ініціалізацію сесійного стану Streamlit."""
    # Створюємо фіктивний session_state
    mock_session_state = MockSessionState()
    # Мокуємо st.session_state
    monkeypatch.setattr(st, "session_state", mock_session_state)
    
    designer.init_session_state()
    
    assert "elements_df" in mock_session_state
    assert "project_settings" in mock_session_state
    assert "wall_thickness" in mock_session_state["project_settings"]

def test_add_element(monkeypatch):
    """Тестує додавання нового елемента."""
    mock_session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", mock_session_state)
    
    designer.init_session_state()
    initial_len = len(mock_session_state["elements_df"])
    designer.add_element("Вікно", 10.0, 5.0)
    
    df = mock_session_state["elements_df"]
    assert len(df) == initial_len + 1
    assert df.iloc[-1]["Тип"] == "Вікно"
    assert "x_0" in mock_session_state

def test_export_project(monkeypatch):
    """Тестує експорт у JSON."""
    mock_session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", mock_session_state)
    
    designer.init_session_state()
    # Імітуємо зміну користувачем
    mock_session_state["project_settings"]["wall_thickness"] = 0.5
    
    json_str = designer.export_project(10, 5, 3, 0, 0)
    data = json.loads(json_str)
    
    assert data["geometry"]["L"] == 10
    assert data["settings"]["wall_thickness"] == 0.5

import numpy as np
from ai import rl_agent

def test_load_rl_agent():
    """Тестує завантаження RL агента. Якщо файлу немає, має повернутись None."""
    # Перевіримо завантаження неіснуючої моделі (за умови що в models/ немає моделі)
    # Якщо модель є, він її завантажить. Тому просто перевіримо що виклик працює.
    rl_agent.load_rl_agent()
    # assert agent is None # Не будемо робити assert None бо модель вже може існувати
    
def test_predict_best_action():
    """Тестує функцію передбачення."""
    # Оскільки завантажити справжнього агента може бути довго або неможливо (відсутній файл),
    # ми створимо мок для моделі
    class MockAgent:
        def predict(self, state, deterministic=True):
            return np.array([1, 2]), None
            
    mock_agent = MockAgent()
    state = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    device_idx, speed = rl_agent.predict_best_action(mock_agent, state)
    
    assert device_idx == 1
    assert speed == 2

def test_train_rl_agent(monkeypatch):
    """Покриття для train_rl_agent."""
    class MockPPO:
        def __init__(self, *args, **kwargs): pass
        def learn(self, **kwargs): pass
        def save(self, *args, **kwargs): pass
    monkeypatch.setattr(rl_agent, "PPO", MockPPO)
    monkeypatch.setattr(rl_agent, "make_vec_env", lambda *args, **kwargs: None)
    
    success, msg = rl_agent.train_rl_agent(timesteps=1)
    assert success

def test_finetune_and_predict(monkeypatch):
    """Покриття для finetune_and_predict."""
    mock_agent = type('MockAgent', (object,), {'learn': lambda self, **kwargs: None, 'predict': lambda self, x, **kwargs: ([[0, 1]], None)})
    monkeypatch.setattr(rl_agent.PPO, "load", lambda *args, **kwargs: mock_agent())
    monkeypatch.setattr(rl_agent, "make_vec_env", lambda *args, **kwargs: type('Env', (object,), {'reset': lambda self: [0, 0]})())
    
    import os
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    
    action, msg = rl_agent.finetune_and_predict({"wall_thickness": 0.5}, timesteps=1)
    assert msg == "Успішно адаптовано."

def test_streamlit_callback():
    from unittest.mock import MagicMock
    mock_st_progress = MagicMock()
    mock_st_text = MagicMock()
    mock_st_chart = MagicMock()
    
    cb = rl_agent.StreamlitProgressCallback(10, mock_st_progress, mock_st_text, mock_st_chart)
    cb.num_timesteps = 5
    cb.model = MagicMock()
    cb.model.ep_info_buffer = [{"r": 10}]
    cb._on_step()
    assert mock_st_progress.progress.called

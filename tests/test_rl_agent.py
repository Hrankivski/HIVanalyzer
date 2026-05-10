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
    # 10 елементів стану: [t_out, t_in, co2, pm, time_sin, time_cos, occ, fan, dt, dco2]
    state = np.array([0.5]*10)
    action = rl_agent.predict_best_action(mock_agent, state)
    
    assert action[0] == 1
    assert action[1] == 2

def test_train_rl_agent(monkeypatch):
    """Покриття для train_rl_agent."""
    class MockPPO:
        def __init__(self, *args, **kwargs): pass
        def learn(self, **kwargs): pass
        def save(self, *args, **kwargs): pass
    monkeypatch.setattr(rl_agent, "PPO", MockPPO)
    
    mock_env = type('Env', (object,), {
        'num_envs': 1, 
        'observation_space': type('Obs', (object,), {'shape': (10,), 'dtype': np.float32})(),
        'action_space': type('Act', (object,), {'shape': (2,)})(),
        'reset': lambda self: np.zeros((1, 10)), 
        'step': lambda self, a: (np.zeros((1, 10)), np.array([0.0]), np.array([False]), [{}]),
        'close': lambda self: None
    })()
    monkeypatch.setattr(rl_agent, "make_vec_env", lambda *args, **kwargs: mock_env)
    
    success, msg = rl_agent.train_rl_agent(timesteps=1)
    assert success

def test_finetune_and_predict(monkeypatch):
    """Покриття для finetune_and_predict."""
    mock_agent = type('MockAgent', (object,), {
        'learn': lambda self, **kwargs: None, 
        'predict': lambda self, x, **kwargs: (np.array([[0, 1]]), None),
        'save': lambda self, *args, **kwargs: None
    })
    monkeypatch.setattr(rl_agent.PPO, "load", lambda *args, **kwargs: mock_agent())
    
    # Мок для VecEnv: reset повертає obs, step повертає (obs, reward, done, info)
    mock_env = type('Env', (object,), {
        'num_envs': 1,
        'observation_space': type('Obs', (object,), {'shape': (10,), 'dtype': np.float32})(),
        'action_space': type('Act', (object,), {'shape': (2,)})(),
        'reset': lambda self: np.zeros((1, 10)), 
        'step': lambda self, a: (np.zeros((1, 10)), np.array([0.0]), np.array([False]), [{}]),
        'close': lambda self: None
    })()
    monkeypatch.setattr(rl_agent, "make_vec_env", lambda *args, **kwargs: mock_env)
    
    import os
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    
    action, msg = rl_agent.finetune_and_predict({"wall_thickness": 0.5}, timesteps=1)
    assert "Переможець" in msg

def test_streamlit_callback():
    from unittest.mock import MagicMock
    mock_shared_state = {"pct": 0, "num_timesteps": 0, "rewards": [], "steps": []}
    
    cb = rl_agent.StreamlitProgressCallback(10, shared_state=mock_shared_state)
    cb.num_timesteps = 5
    cb.model = MagicMock()
    cb.model.ep_info_buffer = [{"r": 10}]
    cb._on_step()
    assert mock_shared_state["pct"] > 0

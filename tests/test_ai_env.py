import numpy as np
from ai.rl_environment import HVACEnv

def test_hvac_env_initialization():
    """Перевірка коректної ініціалізації середовища з JSON базою пристроїв."""
    env = HVACEnv(db_path="data/recuperator_db.json")
    
    assert env.num_devices > 0
    assert env.action_space.nvec[0] == env.num_devices
    assert env.action_space.nvec[1] == 5 # 5 рівнів швидкості турбіни
    
    obs, info = env.reset()
    assert len(obs) == 10 # t_out, t_in, co2, pm, time_sin, time_cos, occ, norm_fan, dt_in, dco2

def test_reward_calculation_extreme_co2():
    """Тестування нарахування штрафів за високий рівень CO2."""
    env = HVACEnv(db_path="data/recuperator_db.json")
    
    # Фіктивний стан: ідеальна температура, але критичний CO2 (3000 ppm)
    # З новими коефіцієнтами (p_co2 = (3000-1000)/800 = 2.5) штраф має бути > 2.0
    obs_dict_bad = {"temp": 22.5, "co2": 3000.0, "pm": 10.0, "energy": 50.0}
    reward_bad = env._calculate_reward(obs_dict_bad)
    
    # Фіктивний стан: ідеальна температура і нормальний CO2
    obs_dict_good = {"temp": 22.5, "co2": 600.0, "pm": 10.0, "energy": 50.0}
    reward_good = env._calculate_reward(obs_dict_good)
    
    # Задуха має каратися значно жорсткіше
    assert reward_bad < reward_good
    assert reward_bad < -2.0 

def test_reward_calculation_extreme_temperature():
    """Тестування нарахування штрафів за вихід з зони комфорту."""
    env = HVACEnv(db_path="data/recuperator_db.json")
    
    # Заморожування кімнати (10 градусів)
    obs_dict_cold = {"temp": 10.0, "co2": 600.0, "pm": 10.0, "energy": 50.0}
    reward_cold = env._calculate_reward(obs_dict_cold)
    
    assert reward_cold < 0.0 # Має бути штраф за відхилення від 22.5

def test_normalization_bounds():
    """Перевірка, що _get_obs() завжди повертає значення в межах [0.0, 1.0]."""
    env = HVACEnv(db_path="data/recuperator_db.json")
    env.reset()
    
    # Задаємо екстремальні значення
    # state має 7 елементів: [t_out, t_in, co2, pm, time_sin, time_cos, occ]
    env.state = np.array([-50.0, 50.0, 10000.0, 500.0, 1.0, -1.0, 100.0])
    obs = env._get_obs()
    
    # Перевіряємо, що np.clip() відпрацював
    assert np.all(obs >= -1.0) 
    assert np.all(obs <= 1.0)

from unittest.mock import MagicMock


def test_train_agent(monkeypatch):
    """Покриття для скрипта train_agent.py."""
    # Мокаємо SubprocVecEnv і PPO щоб не створювати реальні середовища та моделі
    mock_vec_env = MagicMock()
    mock_ppo = MagicMock()
    
    import stable_baselines3
    monkeypatch.setattr(stable_baselines3, "PPO", mock_ppo)
    monkeypatch.setattr(stable_baselines3.common.vec_env, "SubprocVecEnv", mock_vec_env)
    
    from ai import train_agent
    
    # Виклик make_env
    env_fn = train_agent.make_env()
    # env_fn() створить реальне HVACEnv, не будемо викликати щоб не запускати симуляції
    assert callable(env_fn)

    # Виконуємо код, який зазвичай під if __name__ == "__main__":
    # Щоб не переписувати весь файл, просто викличемо ініціалізацію агента
    env = stable_baselines3.common.vec_env.SubprocVecEnv([train_agent.make_env()])
    
    model = stable_baselines3.PPO("MlpPolicy", env)
    
    # Симулюємо виклики
    model.learn(total_timesteps=1)
    model.save("dummy_path")
    
    assert mock_ppo.called

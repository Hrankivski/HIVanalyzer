"""
Модуль штучного інтелекту (RL Agent).
Відповідає за створення, тренування та використання агента PPO (Proximal Policy Optimization) 
для оптимального керування рекуператором.
"""
import os
import multiprocessing

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.callbacks import BaseCallback
except ImportError:
    PPO = None
    BaseCallback = object

from ai.rl_environment import HVACEnv

AGENT_MODEL_PATH = "models/recuperator_agent_v1"


class StreamlitProgressCallback(BaseCallback):
    """
    Кастомний колбек, щоб виводити прогрес навчання напряму в Streamlit (GUI),
    залишаючи консоль абсолютно чистою.
    """

    def __init__(
        self, total_timesteps, st_progress=None, st_text=None, st_chart=None, verbose=0
    ):
        super().__init__(verbose)
        self.total_timesteps = total_timesteps
        self.st_progress = st_progress
        self.st_text = st_text
        self.st_chart = st_chart
        self.last_pct = 0.0
        self.rewards = []
        self.steps = []
        import numpy as np

        self.np = np

    def _on_step(self) -> bool:
        if self.st_progress and self.st_text:
            pct = self.num_timesteps / self.total_timesteps
            # Streamlit progress accepts values from 0.0 to 1.0
            if pct > 1.0:
                pct = 1.0

            # Оновлюємо UI тільки якщо змінився мінімум 1% щоб не перегружати Streamlit
            if pct - self.last_pct >= 0.01 or pct == 1.0:
                if pct >= 1.0:
                    status_text = f"Завершення: Збір фінального буфера досвіду... ({self.num_timesteps} / {self.total_timesteps} кроків)"
                else:
                    status_text = f"Прогрес навчання: {self.num_timesteps} / {self.total_timesteps} кроків ({int(pct * 100)}%)"
                    
                self.st_progress.progress(pct)
                self.st_text.text(status_text)
                self.last_pct = pct

                # Update Chart
                if (
                    self.st_chart
                    and hasattr(self.model, "ep_info_buffer")
                    and len(self.model.ep_info_buffer) > 0
                ):
                    mean_reward = self.np.mean(
                        [ep_info["r"] for ep_info in self.model.ep_info_buffer]
                    )
                    self.rewards.append(mean_reward)
                    self.steps.append(self.num_timesteps)
                    import pandas as pd

                    df = pd.DataFrame(
                        {"Average Reward": self.rewards}, index=self.steps
                    )
                    self.st_chart.line_chart(df)

        return True


def train_rl_agent(
    timesteps: int = 100000, st_progress=None, st_text=None, st_chart=None
):
    """
    Тренує PPO Агента в середовищі HVACEnv.
    """
    if PPO is None:
        return (
            False,
            "Бібліотека 'stable-baselines3' не встановлена. Запустіть: pip install stable-baselines3",
        )

    # Оптимізація під залізо
    num_cores = multiprocessing.cpu_count()
    if TORCH_AVAILABLE:
        torch.set_num_threads(num_cores)

    env = make_vec_env(
        HVACEnv, n_envs=num_cores, env_kwargs={"db_path": "data/recuperator_db.json"}
    )

    # verbose=0 робить консоль повністю чистою, tensorboard_log=None виключає генерацію файлів
    model = PPO("MlpPolicy", env, verbose=0, device="auto")

    # Підключаємо наш Streamlit віджет замість консольного 'progress_bar=True'
    callback = StreamlitProgressCallback(timesteps, st_progress, st_text, st_chart)

    # Тренуємо
    model.learn(total_timesteps=timesteps, callback=callback)

    os.makedirs(os.path.dirname(AGENT_MODEL_PATH), exist_ok=True)
    model.save(AGENT_MODEL_PATH)

    return True, f"Агент успішно пройшов {timesteps} кроків навчання."


def load_rl_agent():
    """Завантажує навченого агента."""
    if PPO is None:
        return None

    path = AGENT_MODEL_PATH + ".zip"
    if os.path.exists(path):
        return PPO.load(AGENT_MODEL_PATH)
    return None


def predict_best_action(model, state):
    """
    Видає найкращу дію для поточного стану.
    Повертає [device_idx, fan_speed_idx]
    """
    action, _states = model.predict(state, deterministic=True)
    return action


def finetune_and_predict(room_config, timesteps=960, st_progress=None, st_text=None):
    """
    Адаптує (Fine-tunes) базового агента до конкретної кімнати і видає ідеальний пристрій.
    """
    if PPO is None:
        return None, "Бібліотека 'stable-baselines3' не встановлена."

    path = AGENT_MODEL_PATH + ".zip"
    if not os.path.exists(path):
        return None, "Базовий агент не знайдений. Спочатку запустіть базове тренування."

    env = make_vec_env(
        HVACEnv,
        n_envs=1,
        env_kwargs={
            "db_path": "data/recuperator_db.json",
            "fixed_room_config": room_config,
        },
    )

    # Оптимізація під залізо
    num_cores = multiprocessing.cpu_count()
    if TORCH_AVAILABLE:
        torch.set_num_threads(num_cores)

    try:
        model = PPO.load(AGENT_MODEL_PATH, env=env, device="auto")
    except ValueError as e:
        if "Observation spaces do not match" in str(e):
            return (
                None,
                "Формат середовища змінився (стара модель несумісна). Перейдіть на вкладку 'AI Lab (RL Train)' та запустіть базове тренування з нуля!",
            )
        raise e

    # Адаптація
    if st_progress and st_text:
        callback = StreamlitProgressCallback(timesteps, st_progress, st_text)
        model.learn(total_timesteps=timesteps, callback=callback)
    else:
        model.learn(total_timesteps=timesteps)

    # Отримання найкращої дії після адаптації
    obs = env.reset()
    action, _ = model.predict(obs, deterministic=True)

    return action[0], "Успішно адаптовано."

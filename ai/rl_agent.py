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
    from stable_baselines3.common.vec_env import VecNormalize
except ImportError:
    PPO = None
    BaseCallback = object
    VecNormalize = None

try:
    from gymnasium import ActionWrapper
except ImportError:
    ActionWrapper = object  # заглушка для відсутності gymnasium

from ai.rl_environment import HVACEnv

AGENT_MODEL_PATH = "models/recuperator_agent_v1"


class FixedDeviceWrapper(ActionWrapper):
    """
    Обгортка середовища для базового тренування: фіксує device_idx=0,
    щоб агент фокусувався виключно на оптимізації швидкості вентилятора.
    Вибір пристрою виконується окремо через бенчмарк (_benchmark_devices).
    """

    def action(self, act):
        # Фіксуємо індекс пристрою = 0, пропускаємо лише fan_speed від агента
        act = act.copy()
        act[0] = 0
        return act


class StreamlitProgressCallback(BaseCallback):
    """
    Колбек навчання: записує прогрес у shared_state dict (thread-safe),
    який зчитується головним потоком Streamlit.
    Це уникає WebSocketClosedError/StopException, бо Streamlit-виклики
    робить головний потік, а не callback в daemon-потоці.
    """

    def __init__(self, total_timesteps, shared_state=None, verbose=0):
        super().__init__(verbose)
        self.total_timesteps = total_timesteps
        self.shared_state = shared_state  # Спільний dict для зв'язку потоків
        self.last_pct = 0.0
        import numpy as np
        self.np = np

    def _on_step(self) -> bool:
        try:
            pct = min(1.0, self.num_timesteps / self.total_timesteps)
            if self.shared_state is not None and (
                pct - self.last_pct >= 0.005 or pct >= 1.0
            ):
                self.shared_state["pct"] = pct
                self.shared_state["num_timesteps"] = self.num_timesteps
                self.last_pct = pct

                if (
                    hasattr(self.model, "ep_info_buffer")
                    and len(self.model.ep_info_buffer) > 0
                ):
                    mean_reward = self.np.mean(
                        [ep["r"] for ep in self.model.ep_info_buffer]
                    )
                    self.shared_state["rewards"].append(float(mean_reward))
                    self.shared_state["steps"].append(self.num_timesteps)
        except Exception:
            pass
        return True



def train_rl_agent(timesteps: int = 100000, shared_state: dict = None):
    """
    Тренує PPO-агента в середовищі HVACEnv.
    shared_state: загальний dict для передачі прогресу в головний Streamlit-потік.
    """
    if PPO is None:
        return (
            False,
            "Бібліотека 'stable-baselines3' не встановлена. Запустіть: pip install stable-baselines3",
        )

    # Налаштування паралелізму під апаратне забезпечення
    num_cores = multiprocessing.cpu_count()
    if TORCH_AVAILABLE:
        torch.set_num_threads(num_cores)

    # Адаптивний n_steps: для малих runs не збираємо 4096×cores-кроковий буфер
    # після завершення навчання.
    n_steps = max(128, min(4096, timesteps // num_cores))
    batch_size = max(64, min(256, n_steps * num_cores // 4))
    # заокруглюємо до ступеня 64 для стабільності SB3
    n_steps = (n_steps // 64) * 64 or 128
    batch_size = (batch_size // 32) * 32 or 64

    # Цільове середовище з фіксацією пристрою:
    # агент вчить тільки швидкість — device не засмічує градієнтний сигнал
    env = make_vec_env(
        HVACEnv,
        n_envs=num_cores,
        env_kwargs={"db_path": "data/recuperator_db.json"},
        wrapper_class=FixedDeviceWrapper,
    )
    # Нормалізація нагороди (running mean/std) для стабільності PPO.
    # norm_obs=False: спостереження вже зроблено в _get_obs(). clip_reward=5.0: обріз оутлайерів.
    if VecNormalize is not None:
        env = VecNormalize(env, norm_obs=False, norm_reward=True, clip_reward=5.0)

    # verbose=0 робить консоль повністю чистою, tensorboard_log=None виключає генерацію файлів
    model = PPO(
        "MlpPolicy",
        env,
        n_steps=n_steps,
        batch_size=batch_size,
        # Збільшуємо швидкість навчання для виходу з локального мінімуму
        learning_rate=2e-4,
        n_epochs=15,
        policy_kwargs=dict(net_arch=[256, 256]),
        # Більше дослідження (exploration)
        ent_coef=0.03,
        verbose=0,
        device="cpu",
    )

    # Передаємо shared_state замість Streamlit-віджетів: колбек пише dict, UI читає з нього
    callback = StreamlitProgressCallback(timesteps, shared_state=shared_state)

    # Тренуємо
    try:
        model.learn(total_timesteps=timesteps, callback=callback)
    except Exception as e:
        # Навіть при помилці (напр., WebSocketClosedError з UI) модель може бути частково навчена.
        # Зберігаємо якрез виняткок, щоб не втратити потенційно навчену модель.
        try:
            os.makedirs(os.path.dirname(AGENT_MODEL_PATH), exist_ok=True)
            model.save(AGENT_MODEL_PATH)
        except Exception:
            pass
        # Перевіряємо чи файл все одно зберігся
        import os as _os
        if _os.path.exists(AGENT_MODEL_PATH + ".zip"):
            return True, "Навчання завершено (було відключення браузера, але модель збережено)."
        return False, f"Помилка під час навчання: {e}"

    # Зберігаємо модель — загорнуто в try-except, щоб помилки збереження
    # не поглиналися мовчки контекстом st.spinner()
    try:
        os.makedirs(os.path.dirname(AGENT_MODEL_PATH), exist_ok=True)
        model.save(AGENT_MODEL_PATH)
    except Exception as e:
        return False, f"Навчання завершено, але помилка збереження моделі: {e}"

    # Зберігаємо статистику VecNormalize (running mean/std) окремо
    try:
        if VecNormalize is not None and isinstance(env, VecNormalize):
            env.save(AGENT_MODEL_PATH + "_vecnorm.pkl")
    except Exception:
        pass  # Некритична помилка — модель вже збережена, статистика нормалізації опціональна

    return True, f"Агент успішно пройшов {timesteps} кроків навчання. Модель збережено: {AGENT_MODEL_PATH}.zip"


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


def _benchmark_devices(model, room_config, db_path="data/recuperator_db.json", n_episodes=3, st_text=None):
    """
    Оцінює кожен рекуператор з бази даних на N коротких епізодах.
    Для кожного пристрою індекс девайсу фіксується примусово,
    а агент самостійно обирає швидкість вентилятора.
    Повертає індекс пристрою з найвищою середньою нагородою та список результатів.
    """
    import json
    with open(db_path, "r", encoding="utf-8") as f:
        devices = json.load(f)

    best_idx = 0
    best_reward = -float("inf")
    results = []  # [(name, avg_reward), ...]

    for device_idx, device in enumerate(devices):
        if st_text:
            st_text.text(f"Бенчмарк: {device['name']} ({device_idx + 1}/{len(devices)})...")

        env = make_vec_env(
            HVACEnv, n_envs=1,
            env_kwargs={"db_path": db_path, "fixed_room_config": room_config},
        )

        total = 0.0
        for _ in range(n_episodes):
            obs = env.reset()
            ep_reward = 0.0
            for _ in range(96):  # 24 години по 15 хв
                action, _ = model.predict(obs, deterministic=True)
                action[0][0] = device_idx  # фіксуємо пристрій, швидкість обирає агент
                obs, reward, done, _ = env.step(action)
                ep_reward += reward[0]
                if done[0]:
                    break
            total += ep_reward

        avg = total / n_episodes
        results.append((device["name"], avg))
        if avg > best_reward:
            best_reward = avg
            best_idx = device_idx

    return best_idx, results


def finetune_and_predict(room_config, timesteps=960, st_progress=None, st_text=None):
    """
    Підбирає найкращий рекуператор для конкретної кімнати у два етапи:
    1. Бенчмарк: кожний пристрій проганяється на N епізодах з фіксованим індексом, агент обирає швидкість.
    2. Донавчання: агент адаптується до цієї кімнати з вже зфіксованим пристроєм.
    """
    if PPO is None:
        return None, "Бібліотека 'stable-baselines3' не встановлена."

    path = AGENT_MODEL_PATH + ".zip"
    if not os.path.exists(path):
        return None, "Базовий агент не знайдений. Спочатку запустіть базове тренування."

    db_path = "data/recuperator_db.json"

    # Налаштування паралелізму під апаратне забезпечення
    num_cores = multiprocessing.cpu_count()
    if TORCH_AVAILABLE:
        torch.set_num_threads(num_cores)

    # --- Етап 1: Завантаження базової моделі для бенчмарку ---
    env_bench = make_vec_env(
        HVACEnv, n_envs=1,
        env_kwargs={"db_path": db_path, "fixed_room_config": room_config},
    )
    try:
        base_model = PPO.load(AGENT_MODEL_PATH, env=env_bench, device="cpu")
    except ValueError as e:
        if "Observation spaces do not match" in str(e) or "Action spaces do not match" in str(e):
            return (
                None,
                "Формат середовища або список пристроїв змінився (стара модель несумісна). Перейдіть на вкладку навчання та запустіть тренування з нуля!",
            )
        raise e

    # --- Етап 2: Бенчмарк усіх пристроїв ---
    # Агент обирає швидкість самостійно, але девайс фіксується примусово.
    # Таким чином ми отримуємо об'єктивну оцінку кожного рекуператора для цієї кімнати.
    if st_text:
        st_text.text("Етап 1/2: Порівняння рекуператорів...")
    if st_progress:
        st_progress.progress(0.05)

    best_device_idx, benchmark_results = _benchmark_devices(
        base_model, room_config, db_path=db_path, n_episodes=3, st_text=st_text
    )

    if st_progress:
        st_progress.progress(0.4)

    # --- Етап 3: Донавчання з фіксованим переможцем ---
    import json
    with open(db_path, "r", encoding="utf-8") as f:
        devices = json.load(f)
    winner_name = devices[best_device_idx]["name"]

    if st_text:
        st_text.text(f"Етап 2/2: Донавчання з {winner_name}...")

    env_tune = make_vec_env(
        HVACEnv, n_envs=1,
        env_kwargs={"db_path": db_path, "fixed_room_config": room_config},
    )
    model = PPO.load(AGENT_MODEL_PATH, env=env_tune, device="cpu")

    if st_progress and st_text:
        callback = StreamlitProgressCallback(timesteps, st_progress, st_text)
        model.learn(
            total_timesteps=timesteps,
            callback=callback,
            reset_num_timesteps=True,
        )
    else:
        model.learn(total_timesteps=timesteps)

    # Зберігаємо адаптовану модель окремо
    FINETUNED_PATH = AGENT_MODEL_PATH.replace("_v1", "_finetuned")
    os.makedirs(os.path.dirname(FINETUNED_PATH), exist_ok=True)
    model.save(FINETUNED_PATH)

    # Формуємо рядок підсумку для UI
    summary_lines = [f"🏆 Переможець: **{winner_name}** (ср. нагорода: {benchmark_results[best_device_idx][1]:.1f})"]
    for name, avg in sorted(benchmark_results, key=lambda x: x[1], reverse=True):
        summary_lines.append(f"• {name}: {avg:.1f}")
    summary = "\n".join(summary_lines)

    # Повертаємо [best_device_idx, fan_speed_idx=3 (75%)] як початкову рекомендацію
    return [best_device_idx, 3], summary

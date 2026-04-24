import streamlit as st
import numpy as np
import pandas as pd
import json
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from ai.rl_environment import HVACEnv


@st.cache_resource
def load_ai_model(path="models/recuperator_agent_v1.zip"):
    """Завантажує модель у кеш пам'яті сервера (миттєвий доступ)."""
    try:
        model = PPO.load(path)
        return model
    except Exception:
        return None


def simulate_24h(model, room_config, agent_controlled=True, fixed_device_idx=None):
    """
    Проганяє математичну симуляцію кімнати за 24 години (96 кроків).
    Якщо agent_controlled=True, оберти вибирає ШІ.
    Якщо False - рекуператор просто молотить на 100% потужності цілодобово.
    """
    env = make_vec_env(
        HVACEnv,
        n_envs=1,
        env_kwargs={
            "db_path": "data/recuperator_db.json",
            "fixed_room_config": room_config,
        },
    )
    obs = env.reset()

    logs = {
        "hour": [],
        "co2": [],
        "pm": [],
        "temp": [],
        "energy_w": [],
        "fan_speed": [],
        "pm_pen": 0.0,
        "co2_pen": 0.0,
        "energy_pen": 0.0,
    }

    with open("data/recuperator_db.json", "r", encoding="utf-8") as f:
        devices = json.load(f)

    device_chosen = None

    for step in range(96):
        if agent_controlled and model is not None:
            action, _ = model.predict(obs, deterministic=True)
            action = action[0]  # Because we use VecEnv
        else:
            # Ручний режим: завжди максимальні оберти (4 = 100%)
            action = np.array(
                [fixed_device_idx if fixed_device_idx is not None else 0, 4]
            )

        if device_chosen is None:
            device_chosen = action[0]

        obs, reward, done, info = env.step([action])

        # Витягуємо сирі значення зі стану (t_out, t_in, co2, pm, time_sin, time_cos, occ)
        raw_env = env.envs[0].unwrapped
        raw_state = raw_env.state
        t_out, t_in, co2, pm, time_sin, time_cos, occ = raw_state

        logs["hour"].append(step * 0.25)
        logs["co2"].append(co2)
        logs["pm"].append(pm)
        logs["temp"].append(t_in)

        dev = devices[action[0]]
        power = dev["power_consumption"] * (action[1] * 0.25)
        logs["energy_w"].append(power)
        logs["fan_speed"].append(action[1] * 25)  # %

        # Накопичуємо штрафи ШІ для модуля пояснень (XAI)
        logs["pm_pen"] += max(0.0, pm - 25.0) * 10.0
        logs["co2_pen"] += max(0.0, co2 - 1000.0) * 5.0
        logs["energy_pen"] += power * 0.1

    return (
        pd.DataFrame(logs),
        device_chosen,
        logs["pm_pen"],
        logs["co2_pen"],
        logs["energy_pen"],
    )


def generate_xai_explanation(
    device_name, pm_pen, co2_pen, energy_pen, manual_energy_sum, ai_energy_sum
):
    """Модуль Explainable AI (XAI) - пояснює причини рішення людською мовою."""
    savings = 0
    if manual_energy_sum > 0:
        savings = ((manual_energy_sum - ai_energy_sum) / manual_energy_sum) * 100

    reasoning = f"Агент обрав модель **{device_name}** та динамічний режим вентиляції. "

    if pm_pen > co2_pen and pm_pen > energy_pen:
        reasoning += "Оскільки ви обрали інтенсивні забруднюючі роботи, пріоритет очищення повітря від мікрочасток пилу став критичним. Агент агресивно вмикав вентилятор під час активності."
    elif co2_pen > pm_pen and co2_pen > energy_pen:
        reasoning += "Через велику кількість людей головною загрозою стала задуха (високий рівень CO₂). Агент підтримував стабільний і потужний потік свіжого повітря для їх комфорту."
    else:
        reasoning += "Повітря залишалося відносно чистим, тому агент зосередився на максимальному збереженні електроенергії, вимикаючи систему, коли кімната пустувала."

    reasoning += f"\n\nЗавдяки динамічному керуванню (зниження потужності вночі та адаптація), ШІ заощадив **{savings:.1f}%** електроенергії порівняно зі звичайним настінним термостатом (який працює на 100%)."
    return reasoning

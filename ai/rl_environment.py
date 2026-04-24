"""
Модуль середовища Gymnasium для навчання з підкріпленням (RL).
Визначає правила, нагороди та простір станів для агента, який вчиться керувати 
HVAC-системою, використовуючи сурогатну модель фізики приміщення.
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import json
import math
import os
from ai import ml_surrogate


class HVACEnv(gym.Env):
    """
    Gymnasium Environment для RL Агента.
    Використовує сурогатну модель-світ для передбачення наступного кроку.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, db_path="data/recuperator_db.json", fixed_room_config=None):
        super(HVACEnv, self).__init__()
        self.fixed_room_config = fixed_room_config

        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                self.devices = json.load(f)
        else:
            raise FileNotFoundError(f"Database {db_path} not found!")

        self.num_devices = len(self.devices)

        # Завантажуємо сурогатну фізику
        self.surrogate_model = ml_surrogate.load_surrogate()

        # [T_out_norm, T_in_norm, CO2_norm, PM_norm, Time_sin, Time_cos, Occ_norm]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0, 0.0, -1.0, -1.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # [Індекс моделі, Турбіна (0, 25, 50, 75, 100%)]
        self.action_space = spaces.MultiDiscrete([self.num_devices, 5])

        self.max_steps = 96
        self.current_step = 0

    def _get_obs(self):
        t_out, t_in, co2, pm, time_sin, time_cos, occ = self.state

        # Min-Max Scaling to [0, 1]
        norm_t_out = np.clip((t_out + 20.0) / 60.0, 0.0, 1.0)  # [-20, 40] -> [0, 1]
        norm_t_in = np.clip((t_in - 10.0) / 30.0, 0.0, 1.0)  # [10, 40] -> [0, 1]
        norm_co2 = np.clip((co2 - 400.0) / 1600.0, 0.0, 1.0)  # [400, 2000] -> [0, 1]
        norm_pm = np.clip(pm / 100.0, 0.0, 1.0)  # [0, 100] -> [0, 1]
        norm_occ = np.clip(occ / 50.0, 0.0, 1.0)  # [0, 50] -> [0, 1]

        return np.array(
            [norm_t_out, norm_t_in, norm_co2, norm_pm, time_sin, time_cos, norm_occ],
            dtype=np.float32,
        )

    def _calculate_reward(self, obs_dict):
        # Масштабуємо штрафи, щоб вони були прийнятними для алгоритму PPO (Normalizing)
        p_poll = max(0, obs_dict["pm"] - 25.0) / 100.0
        p_co2 = max(0, obs_dict["co2"] - 1000.0) / 500.0
        p_temp = abs(obs_dict["temp"] - 22.5) / 10.0
        p_energy = obs_dict["energy"] / 1000.0

        reward = -(p_poll + p_co2 + p_temp + p_energy)
        
        # Survival Bonus (Пряник)
        if obs_dict["co2"] < 1000.0 and 20.0 <= obs_dict["temp"] <= 25.0 and obs_dict["pm"] < 25.0:
            reward += 1.0

        return reward

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0

        if self.fixed_room_config is not None:
            occ = float(self.fixed_room_config.get("occupants", 10.0))
            self._current_vol = float(self.fixed_room_config.get("volume", 144.0))
            self._current_wall = float(
                self.fixed_room_config.get("wall_thickness", 0.3)
            )
        else:
            occ = float(np.random.randint(0, 10))
            self._current_vol = 144.0
            self._current_wall = 0.3

        self.state = np.array(
            [
                np.random.uniform(-10.0, 25.0),  # T_out
                20.0,  # T_in
                500.0,  # CO2
                5.0,  # PM
                math.sin(0),  # Time_sin
                math.cos(0),  # Time_cos
                occ,  # Occ
            ],
            dtype=np.float32,
        )

        return self._get_obs(), {}

    def step(self, action):
        device_idx, fan_idx = action
        fan_speed_pct = fan_idx * 0.25

        device = self.devices[device_idx]
        eff = device["sensible_efficiency"]
        f_class = device["filter_class"]
        flow_rate = device["max_flow_rate"] * fan_speed_pct
        power_w = device["power_consumption"] * fan_speed_pct

        t_out, t_in, co2, pm, time_sin, time_cos, occ = self.state

        current_hour = (self.current_step * 0.25) % 24
        is_working = 1 if (8 <= current_hour <= 18) else 0

        # Якщо сурогатна мережа навчена, використовуємо її для T_in та CO2
        if self.surrogate_model:
            state_dict = {
                "T_out (C)": t_out,
                "T_in_lag_1": t_in,
                "CO2_lag_1": co2,
                "People_Count": occ,
                "Hour": current_hour,
                "Is_Working_Hour": is_working,
                "Volume_m3": self._current_vol,
                "Wall_Thickness": self._current_wall,
                "Soldering_Active": 0,
                "Printer_Active": 0,
                "Heater_Power": 0,
                "Recuperator_Efficiency": eff
                * fan_speed_pct
                * 100,  # передаємо відсоток активності
            }
            preds = ml_surrogate.predict_next_state(self.surrogate_model, state_dict)
            new_t_in = np.clip(preds["T_in_next"], 0.0, 45.0)
            new_co2 = np.clip(preds["CO2_next"], 400.0, 5000.0)
        else:
            # Fallback mathematical approximation якщо ми ще не навчили Random Forest
            ach = flow_rate / self._current_vol
            t_supply = t_out + eff * (t_in - t_out)
            new_t_in = t_in + (ach * (t_supply - t_in) + (occ * 0.5)) * 0.25

            source_co2 = occ * 0.02 * 1000000 / self._current_vol
            vent_co2 = ach * (co2 - 400.0)
            new_co2 = co2 + (source_co2 - vent_co2) * 0.25

        # PM Dynamics (завжди формула, бо E+ не рахував нам PM)
        source_pm = occ * 2.0
        vent_pm = (flow_rate / self._current_vol) * f_class * pm
        new_pm = np.clip(pm + (source_pm - vent_pm) * 0.25, 0.0, 1000.0)

        # REWARDS (Штрафи)
        obs_dict = {"temp": new_t_in, "co2": new_co2, "pm": new_pm, "energy": power_w}
        reward = self._calculate_reward(obs_dict)

        # Критерій зупинки (Terminal State)
        done = False
        if new_co2 > 2500.0 or new_t_in < 15.0 or new_t_in > 35.0:
            done = True
            # Suicide Bug Fix: штраф множиться на залишок кроків
            steps_left = self.max_steps - self.current_step
            reward -= 5.0 * steps_left

        self.current_step += 1
        if self.current_step >= self.max_steps:
            done = True

        time_rad = (self.current_step / self.max_steps) * 2 * math.pi
        new_time_sin = math.sin(time_rad)
        new_time_cos = math.cos(time_rad)

        self.state = np.array(
            [t_out, new_t_in, new_co2, new_pm, new_time_sin, new_time_cos, occ],
            dtype=np.float32,
        )

        # Логування метрик для диплома
        co2_score = max(0.0, 100.0 - ((new_co2 - 400.0) / 1600.0) * 100.0)
        pm_score = max(0.0, 100.0 - (new_pm / 50.0) * 100.0)
        air_quality_score = (co2_score + pm_score) / 2.0

        energy_saved_w = (
            (flow_rate / 3600.0) * 1.2 * 1005.0 * eff * max(0.0, t_in - t_out)
        )

        info = {
            "reward_total": reward,
            "energy_saved": energy_saved_w,
            "air_quality_score": air_quality_score,
            "device": device["name"],
        }

        return self._get_obs(), float(reward), done, False, info

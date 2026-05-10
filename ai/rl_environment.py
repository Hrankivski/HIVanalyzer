"""
Модуль середовища Gymnasium для навчання з підкріпленням (RL).
Визначає правила, нагороди та простір станів для агента, який вчиться керувати 
HVAC-системою, використовуючи сурогатну модель фізики приміщення.
"""
import json
import math
import os

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from ai import ml_surrogate


class HVACEnv(gym.Env):
    """
    Gymnasium-середовище для навчання з підкріпленням.
    Використовує сурогатну модель фізики приміщення для прогнозу наступного стану.
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

        # [T_out_норм, T_in_норм, CO2_норм, PM_норм, Time_sin, Time_cos, Occ_норм, Fan_норм]
        # Fan_норм — нормалізована поточна швидкість вентилятора [0..1].
        # Без цього агент не знає свого попереднього рішення і схильний до різких перемикань.
        # [T_out, T_in, CO2, PM, Time_sin, Time_cos, Occ, Fan, dTemp, dCO2]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0, 0.0, -1.0, -1.0, 0.0, 0.0, -1.0, -1.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # [Індекс пристрою, Швидкість вентилятора (0, 25, 50, 75, 100%)]
        self.action_space = spaces.MultiDiscrete([self.num_devices, 5])

        self.max_steps = 96
        self.current_step = 0

    def _get_obs(self):
        t_out, t_in, co2, pm, time_sin, time_cos, occ = self.state

        # Нормалізація основних значень
        norm_t_out = np.clip((t_out + 20.0) / 60.0, 0.0, 1.0)
        norm_t_in = np.clip((t_in - 10.0) / 30.0, 0.0, 1.0)
        norm_co2 = np.clip((co2 - 400.0) / 3100.0, 0.0, 1.0)
        norm_pm = np.clip(pm / 200.0, 0.0, 1.0)
        norm_occ = np.clip(occ / 50.0, 0.0, 1.0)
        norm_fan = np.clip(self._current_fan_speed, 0.0, 1.0)

        # Додаємо тренди (різниця з попереднім кроком)
        dt_in = np.clip((t_in - self._t_in_prev) / 5.0, -1.0, 1.0)
        dco2 = np.clip((co2 - self._co2_prev) / 500.0, -1.0, 1.0)

        return np.array(
            [norm_t_out, norm_t_in, norm_co2, norm_pm, time_sin, time_cos, norm_occ, norm_fan, dt_in, dco2],
            dtype=np.float32,
        )

    def _calculate_reward(self, obs_dict):
        co2 = obs_dict["co2"]
        temp = obs_dict["temp"]
        pm = obs_dict["pm"]
        prev_co2 = obs_dict.get("prev_co2", co2)
        prev_temp = obs_dict.get("prev_temp", temp)

        # Штрафи (зменшені коефіцієнти, щоб не пригнічувати сигнал)
        p_poll = max(0, pm - 25.0) / 150.0
        p_co2 = max(0, co2 - 1000.0) / 800.0
        p_temp = abs(temp - 22.5) / 15.0
        p_energy = obs_dict["energy"] / 4000.0
        p_switch = obs_dict.get("delta_fan", 0.0) * 0.1

        reward = -(p_poll + p_co2 + p_temp + p_energy + p_switch)

        # ПОЗИТИВНИЙ СИГНАЛ: Нагорода за покращення
        if co2 < prev_co2:
            reward += 1.5 * (prev_co2 - co2) / 500.0
        
        temp_dist_prev = abs(prev_temp - 22.5)
        temp_dist_curr = abs(temp - 22.5)
        if temp_dist_curr < temp_dist_prev:
            reward += 1.0 * (temp_dist_prev - temp_dist_curr) / 5.0

        # Цільова зона: великий бонус за перебування в комфортних межах
        if co2 < 800.0 and 21.0 <= temp <= 24.0 and pm < 20.0:
            reward += 2.0  # Агент має хотіти бути тут
        elif co2 < 1000.0 and 20.0 <= temp <= 25.0 and pm < 25.0:
            reward += 0.5  # Розширена зона комфорту

        return reward

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self._current_fan_speed = 0.0

        if self.fixed_room_config is not None:
            occ = float(self.fixed_room_config.get("occupants", 10.0))
            self._current_vol = float(self.fixed_room_config.get("volume", 144.0))
            self._current_wall = float(
                self.fixed_room_config.get("wall_thickness", 0.3)
            )
        else:
            # Реалістична рандомізація приміщень та людей
            occ = float(np.random.randint(0, 30))
            self._current_vol = float(np.random.choice([72.0, 108.0, 144.0, 180.0, 216.0]))
            self._current_wall = float(np.random.choice([0.2, 0.3, 0.38, 0.45]))

        # Рандомізація початкового стану для навчання в різних умовах
        init_co2 = float(np.random.choice([
            np.random.uniform(400, 700),    # чисте
            np.random.uniform(700, 1500),   # середня забрудненість
            np.random.uniform(1500, 3000),  # критичне забруднення
        ]))
        init_t_in = float(np.random.uniform(17.0, 28.0))
        init_pm = float(np.random.uniform(5.0, 50.0))

        # lag_2 ініціалізація
        self._t_in_prev = init_t_in
        self._co2_prev = init_co2

        self.state = np.array(
            [
                np.random.uniform(-10.0, 25.0),  # T_out
                init_t_in,   # T_in
                init_co2,    # CO2
                init_pm,     # PM
                math.sin(0), # Time_sin
                math.cos(0), # Time_cos
                occ,         # Occ
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
            current_hour = (self.current_step * 0.25) % 24
            is_working = 1 if 8 <= current_hour <= 18 else 0
            # День тижня: EnergyPlus симулює з 01.01 (четвер = 3 в Python)
            day_of_week = int(self.current_step * 0.25 / 24) % 7
            # Приблизна температура припливу через рекуперацію:
            # T_supply = T_out + eff * (T_in - T_out)
            t_supply_approx = t_out + eff * fan_speed_pct * (t_in - t_out)
            state_dict = {
                "T_out (C)": t_out,
                "T_in_lag_1": t_in,
                "T_in_lag_2": self._t_in_prev,  # 2 години тому
                "T_supply_lag_1": t_supply_approx,  # апроксимація температури припливу
                "CO2_lag_1": co2,
                "CO2_lag_2": self._co2_prev,    # 2 години тому
                "People_Count": occ,
                "Hour": current_hour,
                "DayOfWeek": day_of_week,
                "Is_Working_Hour": is_working,
                "Volume_m3": self._current_vol,
                "Wall_Thickness": self._current_wall,
                "Soldering_Active": 0,
                "Printer_Active": 0,
                "Heater_Power": 0,
                "Recuperator_Efficiency": eff * fan_speed_pct * 100,
            }
            preds = ml_surrogate.predict_next_state(self.surrogate_model, state_dict)
            new_t_in = np.clip(preds["T_in_next"], 0.0, 45.0)
            new_co2 = np.clip(preds["CO2_next"], 400.0, 5000.0)
        else:
            # Аналітичне наближення (резервний варіант, якщо сурогатна модель відсутня)
            ach = flow_rate / self._current_vol
            t_supply = t_out + eff * (t_in - t_out)
            new_t_in = t_in + (ach * (t_supply - t_in) + (occ * 0.5)) * 0.25

            source_co2 = occ * 0.02 * 1000000 / self._current_vol
            vent_co2 = ach * (co2 - 400.0)
            new_co2 = co2 + (source_co2 - vent_co2) * 0.25

        # Динаміка зависаючих твердих частинок PM (аналітична модель)
        source_pm = occ * 2.0
        vent_pm = (flow_rate / self._current_vol) * f_class * pm
        new_pm = np.clip(pm + (source_pm - vent_pm) * 0.25, 0.0, 1000.0)

        # Штраф за різкість зміни швидкості (|поточна - попередня| ∈ [0, 1])
        delta_fan = abs(fan_speed_pct - self._current_fan_speed)
        self._current_fan_speed = fan_speed_pct  # запам'ятовуємо для наступного кроку

        # Розрахунок функції нагороди (сумарний штраф за відхилення від нормативів)
        obs_dict = {
            "temp": new_t_in, 
            "co2": new_co2, 
            "pm": new_pm, 
            "energy": power_w, 
            "delta_fan": delta_fan,
            "prev_co2": co2,    # додаємо для розрахунку покращення
            "prev_temp": t_in   # додаємо для розрахунку покращення
        }
        reward = self._calculate_reward(obs_dict)

        # Критерій переходу в термінальний стан
        done = False
        # Поріг 3500 ppm (а не 2500): поріг 2500 був надто низьким і агент вчився уникати 2500,
        # а не оптимізувати до 1000. 3500 ppm — дійсно небезпечний рівень (ASHRAE межа).
        if new_co2 > 3500.0 or new_t_in < 15.0 or new_t_in > 35.0:
            done = True
            # Штраф за раннє завершення зроблено менш агресивним (3.0 замість 5.0),
            # щоб агент встигав "відчути" дельту покращення перед смертю.
            steps_left = self.max_steps - self.current_step
            reward -= 3.0 * steps_left

        self.current_step += 1
        if self.current_step >= self.max_steps:
            done = True

        time_rad = (self.current_step / self.max_steps) * 2 * math.pi
        new_time_sin = math.sin(time_rad)
        new_time_cos = math.cos(time_rad)

        # Запам'ятовуємо поточні значення для lag_2 на наступному кроці
        self._t_in_prev = t_in
        self._co2_prev = co2

        self.state = np.array(
            [t_out, new_t_in, new_co2, new_pm, new_time_sin, new_time_cos, occ],
            dtype=np.float32,
        )

        # Формування метрик якості для звітності та аналізу результатів
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

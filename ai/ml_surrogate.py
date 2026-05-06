import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os

SURROGATE_MODEL_PATH = "models/surrogate_physics.joblib"

# Вхідні ознаки: поточний стан середовища + параметри дії
FEATURES = [
    # Ознаки стану середовища
    "T_out (C)",
    "T_in_lag_1",       # Температура всередині 1 годину тому
    "T_in_lag_2",       # Температура всередині 2 години тому — теплова інерція стін
    "T_supply_lag_1",   # Температура припливу після рекуперації — прямий сигнал хвилинного обміну
    "CO2_lag_1",        # Концентрація CO₂ 1 годину тому
    "CO2_lag_2",        # Концентрація CO₂ 2 години тому — тренд накопичення/розсіювання
    "People_Count",
    "Hour",
    "DayOfWeek",        # День тижня: вихідні мають принципово інший CO₂-профіль
    "Is_Working_Hour",
    "Volume_m3",
    "Wall_Thickness",
    "Soldering_Active",
    "Printer_Active",
    "Heater_Power",
    # Ознаки дії (параметри обраного обладнання)
    "Recuperator_Efficiency",
]

# Цільові змінні (прогноз на наступний часовий крок)
TARGETS = ["T_in (C)", "CO2 (ppm)"]


def train_surrogate(dataset_path: str = "data/training_dataset.csv"):
    """
    Навчає Суррогатну Фізику (Random Forest) на базі CSV з EnergyPlus.
    Ця модель буде слугувати "Швидким Симулятором" (Світом) для RL Агента.
    """
    if not os.path.exists(dataset_path):
        return False, "Файл датасету не знайдено. Спочатку згенеруйте дані."

    df = pd.read_csv(dataset_path)

    # Перевірка наявності всіх вхідних ознак у датасеті
    for f in FEATURES:
        if f not in df.columns:
            # Коректна обробка відсутньої ознаки з інформативним повідомленням
            return False, f"Відсутня колонка у масиві даних: {f}"

    if "CO2 (ppm)" not in df.columns:
        return False, "Відсутня цільова колонка CO2 (ppm)"

    # Для спрощення, будемо навчати просто передбачати абсолютне значення CO2 на наступному кроці,
    # хоча dataset logging збирає CO2 поточного кроку.
    # Так як це Time-Series, y = df['T_in (C)'], df['CO2 (ppm)']
    # а X = df['T_in_lag_1'], df['CO2_lag_1']

    # Базова фільтрація вхідних ознак
    X = df[FEATURES]
    # Цільові змінні: температура та рівень CO₂ на наступному часовому кроці
    y = df[["T_in (C)", "CO2 (ppm)"]]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.1, random_state=42
    )

    base_model = LGBMRegressor(
        # 300 дерев забезпечують достатню виразну здатність для 16 фічей,
        # max_depth=6 обмежує заглиблення і знижує overfitting порівняно з max_depth=10.
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,          # стохастична вибірка підвибірки — регуляризація
        colsample_bytree=0.8,   # випадкове використання фічей по дереву
        verbose=-1,
        random_state=42
    )
    model = MultiOutputRegressor(base_model)
    model.fit(X_train, y_train)

    score = model.score(X_test, y_test)

    os.makedirs(os.path.dirname(SURROGATE_MODEL_PATH), exist_ok=True)
    joblib.dump(model, SURROGATE_MODEL_PATH)

    # Передбачення на тест-вибірці для побудови графіків валідації
    y_pred = model.predict(X_test)

    mae_t = mean_absolute_error(y_test["T_in (C)"], y_pred[:, 0])
    rmse_t = np.sqrt(mean_squared_error(y_test["T_in (C)"], y_pred[:, 0]))

    mae_co2 = mean_absolute_error(y_test["CO2 (ppm)"], y_pred[:, 1])
    rmse_co2 = np.sqrt(mean_squared_error(y_test["CO2 (ppm)"], y_pred[:, 1]))

    metrics = {
        "surrogate_precision_r2": score,
        "dataset_size": len(df),
        "mae_t": mae_t,
        "rmse_t": rmse_t,
        "mae_co2": mae_co2,
        "rmse_co2": rmse_co2,
        "y_test_t_in": y_test["T_in (C)"].values.tolist(),
        "y_pred_t_in": y_pred[:, 0].tolist(),
        "y_test_co2": y_test["CO2 (ppm)"].values.tolist(),
        "y_pred_co2": y_pred[:, 1].tolist(),
    }

    return True, metrics


def load_surrogate():
    """Завантажує сурогатну модель-Світ з диска."""
    if os.path.exists(SURROGATE_MODEL_PATH):
        return joblib.load(SURROGATE_MODEL_PATH)
    return None


def predict_next_state(model, state_dict: dict):
    """
    Дає швидкий прогноз (1 мс) наступного стану замість E+.
    """
    input_df = pd.DataFrame([state_dict])[FEATURES]
    preds = model.predict(input_df)[0]

    return {"T_in_next": preds[0], "CO2_next": preds[1]}

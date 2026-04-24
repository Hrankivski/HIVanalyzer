import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os

SURROGATE_MODEL_PATH = "models/surrogate_physics.joblib"

# Входи: Поточний стан + Дія
FEATURES = [
    # State features
    "T_out (C)",
    "T_in_lag_1",
    "CO2_lag_1",
    "People_Count",
    "Hour",
    "Is_Working_Hour",
    "Volume_m3",
    "Wall_Thickness",
    "Soldering_Active",
    "Printer_Active",
    "Heater_Power",
    # Action features (from equipment simulation)
    "Recuperator_Efficiency",
]

# Що модель фізики нам каже про наступний крок (15 хв наперед)
TARGETS = [
    "T_in (C)",
    "CO2_trend",  # Або безпосередньо CO2
]


def train_surrogate(dataset_path: str = "data/training_dataset.csv"):
    """
    Навчає Суррогатну Фізику (Random Forest) на базі CSV з EnergyPlus.
    Ця модель буде слугувати "Швидким Симулятором" (Світом) для RL Агента.
    """
    if not os.path.exists(dataset_path):
        return False, "Файл датасету не знайдено. Спочатку згенеруйте дані."

    df = pd.read_csv(dataset_path)

    # Validate features exist
    for f in FEATURES:
        if f not in df.columns:
            # If not there, we gracefully fail or try to impute
            return False, f"Відсутня колонка у масиві даних: {f}"

    if "CO2 (ppm)" not in df.columns:
        return False, "Відсутня цільова колонка CO2 (ppm)"

    # Для спрощення, будемо навчати просто передбачати абсолютне значення CO2 на наступному кроці,
    # хоча dataset logging збирає CO2 поточного кроку.
    # Так як це Time-Series, y = df['T_in (C)'], df['CO2 (ppm)']
    # а X = df['T_in_lag_1'], df['CO2_lag_1']

    # Базова очистка
    X = df[FEATURES]
    # Наш target
    y = df[["T_in (C)", "CO2 (ppm)"]]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.1, random_state=42
    )

    base_model = LGBMRegressor(
        n_estimators=100, max_depth=10, n_jobs=-1, random_state=42
    )
    model = MultiOutputRegressor(base_model)
    model.fit(X_train, y_train)

    score = model.score(X_test, y_test)

    os.makedirs(os.path.dirname(SURROGATE_MODEL_PATH), exist_ok=True)
    joblib.dump(model, SURROGATE_MODEL_PATH)

    # Передбачення для тест-сету (для графіків)
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

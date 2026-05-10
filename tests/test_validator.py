import pandas as pd

from simulation import validator


def test_validate_simulation_data_good_quality():
    """Тестує валідатор на 'хорошому' симуляційному датасеті."""
    # Створюємо датафрейм, що імітує правильну роботу рекуператора (CO2 падає, Температура тримається)
    df = pd.DataFrame({
        "T_in (C)": [20.0, 19.8, 19.5, 19.3],
        "T_out (C)": [-5.0, -5.0, -5.0, -5.0],
        "Heating Energy (J)": [0, 0, 0, 0],
        "Heat Recovery (J)": [1000, 1000, 1000, 1000],
        "CO2 (ppm)": [1200, 1000, 800, 600],
        "Generic Contaminant": [50.0, 40.0, 30.0, 20.0]
    })
    
    validator_obj = validator.ModelValidator()
    results = validator_obj.run_all_tests(df)
    
    # Симуляція мала б пройти валідацію
    co2_status = next(r["status"] for r in results if "CO" in r["name"])
    assert co2_status != "Fail"
    
def test_validate_simulation_data_bad_quality():
    """Тестує валідатор на даних, де є задуха."""
    df = pd.DataFrame({
        "Datetime": pd.date_range("2026-01-01", periods=4, freq="1H"),
        "T_in (C)": [20.0]*4,
        "T_out (C)": [-5.0]*4,
        "Heating Energy (J)": [0]*4,
        "Heat Recovery (J)": [0]*4,
        "CO2 (ppm)": [2000, 2100, 2200, 2300], # Постійна задуха
        "Generic Contaminant": [10.0]*4
    })
    
    validator_obj = validator.ModelValidator()
    results = validator_obj.run_all_tests(df)
    
    # Має бути визнана невалідною через постійно високий CO2
    co2_status = next(r["status"] for r in results if "CO" in r["name"])
    assert co2_status == "Fail"

import pytest
import os
import tempfile
import pandas as pd
from ai import ml_surrogate

def test_train_surrogate_with_mock_data():
    """Тестування пайплайну навчання сурогатної моделі на штучних даних."""
    # Створюємо малий фіктивний датасет
    df = pd.DataFrame({
        "Datetime": pd.date_range("2026-01-01", periods=10, freq="15min"),
        "T_out (C)": [-5.0]*10,
        "T_in (C)": [20.0]*10,
        "CO2 (ppm)": [600.0, 610.0, 620.0, 630.0, 640.0, 650.0, 660.0, 670.0, 680.0, 690.0],
        "T_in_lag_1": [20.0]*10,
        "CO2_lag_1": [590.0, 600.0, 610.0, 620.0, 630.0, 640.0, 650.0, 660.0, 670.0, 680.0],
        "People_Count": [5]*10,
        "Hour": [12]*10,
        "Is_Working_Hour": [1]*10,
        "Volume_m3": [100.0]*10,
        "Wall_Thickness": [0.3]*10,
        "Soldering_Active": [0]*10,
        "Printer_Active": [0]*10,
        "Heater_Power": [0]*10,
        "Recuperator_Efficiency": [50.0]*10
    })
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        df.to_csv(f.name, index=False)
        csv_path = f.name
        
    try:
        success, msg = ml_surrogate.train_surrogate(csv_path)
        assert success is True
        assert "mae_co2" in msg
        assert "surrogate_precision_r2" in msg
    finally:
        os.remove(csv_path)

def test_predict_next_state():
    """Тестування генерації передбачень сурогатною моделлю."""
    model = ml_surrogate.load_surrogate()
    if not model:
        pytest.skip("Model not trained yet, skipping prediction test.")
        
    state_dict = {
        "T_out (C)": -5.0,
        "T_in_lag_1": 20.0,
        "CO2_lag_1": 600.0,
        "People_Count": 5,
        "Hour": 12,
        "Is_Working_Hour": 1,
        "Volume_m3": 100.0,
        "Wall_Thickness": 0.3,
        "Soldering_Active": 0,
        "Printer_Active": 0,
        "Heater_Power": 0,
        "Recuperator_Efficiency": 50.0
    }
    
    preds = ml_surrogate.predict_next_state(model, state_dict)
    assert "T_in_next" in preds
    assert "CO2_next" in preds
    assert preds["CO2_next"] > 0

from core import constants

def test_materials_constants():
    """Перевірка наявності базових матеріалів та їх фізичних властивостей."""
    assert "Цегла" in constants.MATERIALS
    assert "Бетон" in constants.MATERIALS
    
    brick = constants.MATERIALS["Цегла"]
    assert brick["conductivity"] == 0.81
    assert brick["density"] == 1800
    assert brick["specific_heat"] == 880

def test_air_physics_constants():
    """Перевірка констант фізики повітря."""
    assert constants.AIR_PHYSICS["outdoor_co2_ppm"] == 400.0
    assert constants.AIR_PHYSICS["co2_production_active"] > 0
    assert constants.AIR_PHYSICS["fresh_air_standard"] == 30.0

def test_simulation_settings():
    """Перевірка дефолтних налаштувань симуляції."""
    assert "time_step_hours" in constants.SIMULATION
    assert constants.SIMULATION["default_temp_in"] == 20.0
    assert constants.SIMULATION["default_temp_out"] == -5.0

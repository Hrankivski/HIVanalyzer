# materials and physical constants

MATERIALS = {
    "Цегла": {
        "conductivity": 0.81,  # Вт/м·К
        "density": 1800,       # кг/м³
        "specific_heat": 880   # Дж/кг·К
    },
    "Бетон": {
        "conductivity": 1.74,
        "density": 2400,
        "specific_heat": 840
    },
    "Газоблок": {
        "conductivity": 0.15,
        "density": 600,
        "specific_heat": 840
    },
    "Сендвіч-панель": {
        "conductivity": 0.04,
        "density": 40,
        "specific_heat": 1400
    },
    "Скло": {
        "conductivity": 1.05,
        "density": 2500,
        "specific_heat": 840
    }
}

AIR_PHYSICS = {
    "outdoor_co2_ppm": 400.0,
    "co2_production_active": 30.0,  # л/год на людину
    "fresh_air_standard": 30.0      # м³/год на людину
}

SIMULATION = {
    "time_step_hours": 1.0,         # Крок розрахунку
    "default_temp_in": 20.0,        # Дефолтна температура в приміщенні
    "default_temp_out": -5.0,        # Дефолтна температура зовні
    "eplus_exe": r"C:\EnergyPlusV25-2-0\energyplus.exe", # Default Windows path
    "weather_file": r"weather\UKR_KC_Kyiv.333450_TMYx.2009-2023.epw"
}

VALIDATION_THRESHOLDS = {
    "thermal_decay_max_c_per_hour": 5.0,
    "co2_max_ppm": 1600.0,
    "co2_recovery_target": 500.0,
    "heating_correlation_min": -0.8,
    "contaminant_decay_fraction": 0.5
}

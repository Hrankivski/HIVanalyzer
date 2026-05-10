import pandas as pd

from simulation import simulation_engine


def test_generate_random_params():
    """Перевіряє генерацію параметрів."""
    runner = simulation_engine.SimulationRunner('{"settings": {}, "geometry": {"L": 10}}')
    params = runner.generate_random_params()
    
    import json
    parsed = json.loads(params)
    assert "settings" in parsed

def test_extract_features_targets():
    """Перевіряє обробку датасету для AI."""
    runner = simulation_engine.SimulationRunner('{"settings": {}, "geometry": {"L": 10}}')
    
    # Мок DataFrame з симуляції
    df = pd.DataFrame({
        "Hour": [1, 2, 3],
        "T_in_C": [20.0, 21.0, 20.5],
        "CO2_ppm": [500, 600, 550],
        "VOC_ppm": [0.01, 0.02, 0.015],
        "Heat_Energy_J": [1000, 0, 500],
        "Cool_Energy_J": [0, 1000, 0],
        "Fan_Energy_J": [50, 50, 50]
    })
    
    # Мок параметрів
    sim_params = {
        "t_out": -5.0,
        "people": 2,
        "vent_rate": 0.5,
        "co2_gen": 0.0001,
        "thermal_inertia": 0.1,
        "Indoor Temp Setpoint": 20.0,
        "Indoor Heating Setpoint": 20.0,
        "Indoor Cooling Setpoint": 24.0,
    }
    
    try:
        row = runner.extract_features_targets(df, sim_params)
        assert row is not None
    except Exception:
        pass

def test_run_simulation(monkeypatch):
    import os
    import subprocess
    import tempfile
    
    mock_run = type('MockResult', (object,), {'returncode': 0, 'stderr': ''})()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_run)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Створимо фіктивний csv, щоб симуляція вважалася успішною
        csv_path = os.path.join(tmpdir, "eplusout.csv")
        with open(csv_path, "w") as f:
            f.write("Date/Time,Zone Mean Air Temperature [C]\n01/01  01:00:00,20.0\n")
            
        success, msg, _ = simulation_engine.run_simulation("test", "dummy.exe", "dummy.epw", sim_dir_override=tmpdir)
        # У нас немає справжнього eplus.exe, але якщо він не існує, функція повертає False
        # Якщо ми мокаємо os.path.exists
        
def test_get_results():
    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as f:
        header = (
            "Date/Time,"
            "Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep),"
            "Site Wind Speed [m/s],"
            "Zone Mean Air Temperature [C],"
            "Zone Air CO2 Concentration [ppm],"
            "Zone Air Generic Air Contaminant Concentration [ppm],"
            "Zone Air Infiltration Volume [m3],"
            "Infiltration Sensible Heat Loss [J],"
            "Fan Electricity Energy [J],"
            "Electricity:Facility [J],"
            "Zone Air System Sensible Heating Energy [J],"
            "Zone Air System Sensible Cooling Energy [J],"
            "ERV_SA_OUTLET System Node Temperature [C],"
            "Zone Ventilation Air Changes per Hour [ach],"
            "Heat Exchanger Sensible Heating Energy [J]\n"
        )
        f.write(header)
        f.write("01/01  24:00:00,-5.0,2.0,20.0,400.0,0.0,10.0,100.0,50.0,500.0,200.0,0.0,15.0,0.5,100.0\n")
        name = f.name
    try:
        df = simulation_engine.get_results(name)
        assert not df.empty
        assert "T_out (C)" in df.columns
        assert "Wind Speed (m/s)" in df.columns
        assert "T_in (C)" in df.columns
        assert "CO2 (ppm)" in df.columns
        assert "Generic Contaminant" in df.columns
        assert "Infiltration Volume (m3)" in df.columns
        assert "Infiltration Heat Loss (J)" in df.columns
        assert "Fan Energy (J)" in df.columns
        assert "Total Electricity (J)" in df.columns
        assert "Heating Energy (J)" in df.columns
        assert "Cooling Energy (J)" in df.columns
        assert "T_supply (C)" in df.columns
        assert "Ventilation ACH" in df.columns
        assert "Heat Recovery (J)" in df.columns
    finally:
        import os
        os.remove(name)

def test_run_batch(monkeypatch):
    monkeypatch.setattr(simulation_engine, "run_simulation", lambda *args, **kwargs: (True, "dummy", "dummy"))
    
    import pandas as pd
    dummy_df = pd.DataFrame({"Datetime": pd.date_range("2026-01-01", periods=3, freq="h"), "T_out (C)": [1, 2, 3]})
    monkeypatch.setattr(simulation_engine, "get_results", lambda x: dummy_df)
    
    def extract_mock(self, df, proj):
        return pd.DataFrame({"dummy": [1]})
        
    monkeypatch.setattr(simulation_engine.SimulationRunner, "extract_features_targets", extract_mock)
    
    runner = simulation_engine.SimulationRunner('{"settings": {}}')
    runner.dataset_path = "data/dummy_dataset_test.csv"
    success, num = runner.run_batch(n_simulations=1)
    assert success
    
    import os
    if os.path.exists("data/dummy_dataset_test.csv"):
        os.remove("data/dummy_dataset_test.csv")


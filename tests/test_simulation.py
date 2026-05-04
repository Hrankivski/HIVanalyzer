import json
import tempfile
import os
from simulation import idf_bridge, simulation_engine

def test_idf_bridge_generate_idf():
    """Тестує, чи генерує idf_bridge валідну геометрію приміщення."""
    mock_config = {
        "geometry": {"L": 10.0, "W": 5.0, "H": 3.0, "L_cut": 0.0, "W_cut": 0.0},
        "settings": {
            "wall_thickness": 0.3,
            "wall_material": "Цегла",
            "wall_type_0": "Зовнішня",
            "wall_mat_0": "Базовий"
        }
    }
    
    json_data = json.dumps(mock_config)
    idf_str = idf_bridge.generate_idf_structure(json_data)
    
    # Перевіряємо, що згенерувався текст
    assert isinstance(idf_str, str)
    assert len(idf_str) > 0
    
    # Перевіряємо координати стін (без слова Vertex, формат: X, Y, Z,)
    assert "10.00, 0.00, 0.00," in idf_str  # Правий нижній кут X=L
    assert "10.00, 5.00, 3.00;" in idf_str  # Правий верхній кут Y=W, Z=H
    
def test_simulation_engine_get_results():
    """Тестує парсинг фіктивного eplusout.csv за допомогою pandas."""
    # Створюємо тимчасовий CSV файл
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write("Date/Time,Outdoor Air Drybulb Temperature [C],Zone Mean Air Temperature [C],Zone Air CO2 Concentration [ppm]\n")
        f.write(" 01/01  01:00:00,-5.0,20.0,450.0\n")
        f.write(" 01/01  02:00:00,-5.5,19.5,600.0\n")
        csv_path = f.name
        
    try:
        df = simulation_engine.get_results(csv_path)
        
        assert not df.empty
        assert "Datetime" in df.columns
        assert "T_out (C)" in df.columns
        assert "T_in (C)" in df.columns
        assert "CO2 (ppm)" in df.columns
        
        # Перевірка правильності розпізнавання значень
        assert df["T_in (C)"].iloc[0] == 20.0
        assert df["CO2 (ppm)"].iloc[1] == 600.0
        assert len(df) == 2
        
    finally:
        os.remove(csv_path)

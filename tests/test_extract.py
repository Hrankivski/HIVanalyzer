import os
import tempfile

from core import extract


def test_extract_results():
    """Тестує парсинг фіктивного CSV."""
    # Створюємо фіктивний Eplus CSV файл
    csv_content = """Date/Time,Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep),MainZone:Zone Mean Air Temperature [C](TimeStep),MainZone:Zone Air CO2 Concentration [ppm](TimeStep),MainZone:Zone Generic Contaminant Concentration [ppm](TimeStep),MainZone:Zone Air Temperature [C](Hourly)
01/01  00:15:00,-5.0,20.0,500.0,0.01,
01/01  00:30:00,-5.1,19.9,510.0,0.02,
01/01  00:45:00,-5.2,19.8,520.0,0.03,
01/01  01:00:00,-5.3,19.7,530.0,0.04,19.7
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(csv_content)
        csv_path = f.name
        
    try:
        df = extract.extract_results(csv_path, "mock_out.csv", "mock_out.txt")
        assert not df.empty
        assert "T_out_C" in df.columns
        assert "T_in_C" in df.columns
        assert "CO2_ppm" in df.columns
        assert "VOC_ppm" in df.columns
        assert len(df) == 4
    finally:
        os.remove(csv_path)

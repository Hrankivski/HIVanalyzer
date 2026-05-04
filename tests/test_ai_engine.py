import pandas as pd
from ai import ai_engine

def test_generate_xai_explanation():
    """Перевіряє, чи система XAI формує логічне пояснення."""
    
    device_name = "Mock Recuperator X"
    pm_pen = 0.5
    co2_pen = 0.0
    ai_energy_pen = 1.0
    
    manual_energy = 5000.0
    ai_energy = 2500.0
    
    explanation = ai_engine.generate_xai_explanation(
        device_name, pm_pen, co2_pen, ai_energy_pen, manual_energy, ai_energy
    )
    
    # Має згадуватись назва пристрою
    assert device_name in explanation
    # Має бути згадана економія енергії
    assert "економі" in explanation.lower() or "енерг" in explanation.lower()

def test_simulate_24h_fallback_math():
    """Перевіряє, що симуляція математичної моделі за 24 години (96 кроків) проходить швидко і повертає датафрейм."""
    # Викликаємо функцію з None замість моделі (Manual режим)
    df, best_idx, pm, co2, energy = ai_engine.simulate_24h(None, {"occupants": 5, "volume": 100}, agent_controlled=False)
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "hour" in df.columns
    assert len(df) == 96 # 24 години = 96 кроків по 15 хвилин

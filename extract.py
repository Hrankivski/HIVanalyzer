import pandas as pd
import os

sim_dir = r"D:\diploma\HIVanalyzer\data\sim_20260406_112736"
csv_path = r"D:\diploma\HIVanalyzer\data\sim_20260406_112736\eplusout.csv"
out_csv = r"d:\diploma\HIVanalyzer\latest_simulation_data.csv"
out_txt = r"d:\diploma\HIVanalyzer\latest_simulation_summary.txt"

try:
    df = pd.read_csv(csv_path)
    
    # Identify columns
    t_out_col = [c for c in df.columns if "Outdoor Air Drybulb" in c]
    t_in_col = [c for c in df.columns if "Zone Mean Air Temperature" in c]
    co2_col = [c for c in df.columns if "Zone Air CO2" in c]
    voc_col = [c for c in df.columns if "Generic Contaminant Concentration" in c]
    fan_col = [c for c in df.columns if "Fan Electricity Energy" in c]
    heat_col = [c for c in df.columns if "Sensible Heating Energy" in c and "System" in c]
    cool_col = [c for c in df.columns if "Sensible Cooling Energy" in c and "System" in c]
    
    rename_map = {}
    if t_out_col: rename_map[t_out_col[0]] = "T_out_C"
    if t_in_col: rename_map[t_in_col[0]] = "T_in_C"
    if co2_col: rename_map[co2_col[0]] = "CO2_ppm"
    if voc_col: rename_map[voc_col[0]] = "VOC_ppm"
    if fan_col: rename_map[fan_col[0]] = "Fan_Energy_J"
    if heat_col: rename_map[heat_col[0]] = "Heat_Energy_J"
    if cool_col: rename_map[cool_col[0]] = "Cool_Energy_J"
    
    df_clean = df[list(rename_map.keys())].copy()
    df_clean.rename(columns=rename_map, inplace=True)
    
    df_clean.to_csv(out_csv, index=True, index_label="Hour")
    
    # Text summary
    summary = "=== ОГЛЯД СИМУЛЯЦІЇ ===\n\n"
    summary += f"Годин розрахунку: {len(df_clean)}\n\n"
    
    for col in df_clean.columns:
        summary += f"Показник: {col}\n"
        summary += f"  Мін: {df_clean[col].min():.2f}\n"
        summary += f"  Макс: {df_clean[col].max():.2f}\n"
        summary += f"  Середнє: {df_clean[col].mean():.2f}\n\n"
        
    summary += "=== ДАНІ (ТІЛЬКИ КОЖЕН 24-й КРОК ДЛЯ ОГЛЯДУ) ===\n"
    summary += df_clean.iloc[::24].to_string()
    
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(summary)
        
    print(f"Дані успішно експортовано у {out_csv} та {out_txt}")

except Exception as e:
    print(f"Помилка: {e}")

import os
import subprocess
import pandas as pd
import datetime
import constants

def run_simulation(idf_content: str, eplus_exe: str = None, epw_path: str = None) -> (bool, str, str):
    """
    Runs EnergyPlus simulation in a unique directory for each run.
    Returns: (success_bool, csv_data_or_error_message, sim_dir_path)
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sim_dir = os.path.join("data", f"sim_{timestamp}")
    if not os.path.exists(sim_dir):
        os.makedirs(sim_dir)
        
    idf_path = os.path.join(sim_dir, "in.idf")
    
    with open(idf_path, "w", encoding="utf-8") as f:
        f.write(idf_content)
        
    exe_path = eplus_exe if eplus_exe else constants.SIMULATION["eplus_exe"]
    weather = epw_path if epw_path else constants.SIMULATION["weather_file"]
    
    if not os.path.exists(exe_path):
        return False, f"Вказаний шлях до EnergyPlus не знайдено:\n{exe_path}", sim_dir
        
    cmd = [
        exe_path,
        "-x",
        "-r",
        "-d", sim_dir,
    ]
    if os.path.exists(weather):
        cmd.extend(["-w", weather])
    cmd.append(idf_path)
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode != 0:
            err_path = os.path.join(sim_dir, "eplusout.err")
            err_msg = f"EnergyPlus завершився з кодом {result.returncode}.\n"
            if os.path.exists(err_path):
                with open(err_path, "r", encoding="utf-8") as ef:
                    lines = ef.readlines()
                    err_msg += "".join(lines[:10]) # Get first 10 lines of error
            else:
                err_msg += result.stderr
            return False, err_msg, sim_dir
            
        csv_path = os.path.join(sim_dir, "eplusout.csv")
        if os.path.exists(csv_path):
            return True, csv_path, sim_dir
        else:
            return False, "Симуляція пройшла, але файл eplusout.csv не знайдено.", sim_dir
            
    except Exception as e:
        return False, f"Помилка виклику процесу: {str(e)}", sim_dir

def get_results(csv_path: str) -> pd.DataFrame:
    """
    Parses the eplusout.csv file to extract specific columns.
    """
    try:
        df = pd.read_csv(csv_path)
        # We look for partial matches to be robust against E+ version naming changes
        cols_to_keep = {}
        for col in df.columns:
            if "Date/Time" in col:
                cols_to_keep[col] = "Datetime"
            elif "Outdoor Air Drybulb Temperature" in col:
                cols_to_keep[col] = "T_out (C)"
            elif "Wind Speed" in col:
                cols_to_keep[col] = "Wind Speed (m/s)"
            elif "Zone Mean Air Temperature" in col:
                cols_to_keep[col] = "T_in (C)"
            elif "Zone Air CO2 Concentration" in col:
                cols_to_keep[col] = "CO2 (ppm)"
            elif "Generic Air Contaminant" in col:
                cols_to_keep[col] = "Generic Contaminant"
            elif "Zone Air Infiltration Volume" in col or "Infiltration Standard Density Volume Flow Rate" in col:
                cols_to_keep[col] = "Infiltration Volume (m3)"
            elif "Infiltration Sensible Heat Loss" in col:
                cols_to_keep[col] = "Infiltration Heat Loss (J)"
            elif "Fan Electricity Energy" in col or ("Electric" in col and "Fan" in col):
                cols_to_keep[col] = "Fan Energy (J)"
            elif "Electricity:Facility" in col:
                cols_to_keep[col] = "Total Electricity (J)"
            elif "Sensible Heating Energy" in col and ("Ideal Loads" in col or "System" in col):
                cols_to_keep[col] = "Heating Energy (J)"
            elif "Sensible Cooling Energy" in col and ("Ideal Loads" in col or "System" in col):
                cols_to_keep[col] = "Cooling Energy (J)"
            elif "System Node Temperature" in col and "ERV_SA_OUTLET" in col.upper():
                cols_to_keep[col] = "T_supply (C)"
            elif "Ventilation Air Changes per Hour" in col:
                cols_to_keep[col] = "Ventilation ACH"
            elif "Heat Exchanger Sensible Heating Energy" in col:
                cols_to_keep[col] = "Heat Recovery (J)"

                
        if not cols_to_keep:
            return pd.DataFrame()
            
        df_filtered = df[list(cols_to_keep.keys())].copy()
        
        # Гарантуємо унікальність нових назв колонок (оскільки вентиляторів тепер два)
        seen = {}
        unique_cols_to_keep = {}
        for original_col, target_col in cols_to_keep.items():
            if target_col in seen:
                seen[target_col] += 1
                unique_cols_to_keep[original_col] = f"{target_col} {seen[target_col]}"
            else:
                seen[target_col] = 1
                unique_cols_to_keep[original_col] = target_col
                
        df_filtered.rename(columns=unique_cols_to_keep, inplace=True)
        
        # Обробка Дати/Часу для осі Х
        if "Datetime" in df_filtered.columns:
            s_dt = df_filtered["Datetime"].str.strip()
            mask_24 = s_dt.str.endswith("24:00:00")
            s_dt = s_dt.str.replace("24:00:00", "00:00:00")
            
            # Додаємо рік (2026, як у IDF RunPeriod) та парсимо
            df_filtered["Datetime"] = pd.to_datetime("2026/" + s_dt, errors='coerce', format='mixed')
            df_filtered.loc[mask_24, "Datetime"] += pd.Timedelta(days=1)
            
        return df_filtered
        
    except Exception as e:
        print(f"Помилка парсингу результатів: {e}")
        return pd.DataFrame()

def log_simulation_data(project_json: str, df_res: pd.DataFrame, file_path: str = "data/training_data.csv"):
    """
    Extracts features from the project JSON and labels from the simulation results,
    then logs them to a CSV file for Machine Learning.
    """
    if df_res.empty: return
    import json
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    data = json.loads(project_json)
    geom = data.get("geometry", {})
    sett = data.get("settings", {})
    
    # Calculate simple aggregates for the dataset
    mean_t_out = df_res["T_out (C)"].mean() if "T_out (C)" in df_res.columns else 0
    mean_t_in = df_res["T_in (C)"].mean() if "T_in (C)" in df_res.columns else 0
    final_co2 = df_res["CO2 (ppm)"].iloc[-1] if "CO2 (ppm)" in df_res.columns else 0
    
    row = {
        "Volume_m3": geom.get("L", 0) * geom.get("W", 0) * geom.get("H", 0),
        "Wall_Material": sett.get("wall_material", ""),
        "Occupants": sett.get("occupants", 0),
        "Recuperator_Eff": sett.get("recuperator_efficiency", 0),
        "Mean_T_out": mean_t_out,
        "Mean_T_in": mean_t_in,
        "Final_CO2": final_co2
    }
    
    df_log = pd.DataFrame([row])
    if not os.path.exists(file_path):
        df_log.to_csv(file_path, index=False)
    else:
        df_log.to_csv(file_path, mode='a', header=False, index=False)

import random

class SimulationRunner:
    def __init__(self, base_project_json: str, eplus_exe: str = None, epw_path: str = None):
        self.base_project_json = base_project_json
        self.eplus_exe = eplus_exe
        self.epw_path = epw_path
        self.dataset_path = "data/training_dataset.csv"
        
    def generate_random_params(self):
        import json
        data = json.loads(self.base_project_json)
        if "settings" not in data:
            data["settings"] = {}
            
        data["settings"]["wall_thickness"] = round(random.uniform(0.1, 0.4), 2)
        data["settings"]["recuperator_efficiency"] = round(random.uniform(50.0, 90.0), 1)
        data["settings"]["occupants"] = random.randint(0, 10)
        data["settings"]["heater_power"] = random.randint(0, 3000)
        
        data["settings"]["soldering_active"] = random.choice([0.0, 1.0])
        data["settings"]["printer_active"] = random.choice([0.0, 1.0])
        
        return json.dumps(data)

    def extract_features_targets(self, df_res: pd.DataFrame, proj_data: dict) -> dict:
        sett = proj_data.get("settings", {})
        
        t_out = df_res["T_out (C)"].mean() if "T_out (C)" in df_res.columns else 0
        wind = df_res["Wind Speed (m/s)"].mean() if "Wind Speed (m/s)" in df_res.columns else 0
        
        t_in = df_res["T_in (C)"].mean() if "T_in (C)" in df_res.columns else 0
        co2_max = df_res["CO2 (ppm)"].max() if "CO2 (ppm)" in df_res.columns else 0
        pm_max = df_res["Generic Contaminant"].max() if "Generic Contaminant" in df_res.columns else 0
        total_energy = df_res["Total Electricity (J)"].max() if "Total Electricity (J)" in df_res.columns else 0
        
        return {
            "T_out": t_out,
            "Wind_Speed": wind,
            "People_Count": sett.get("occupants", 0),
            "Soldering_Active": sett.get("soldering_active", 0),
            "Printer_Active": sett.get("printer_active", 0),
            "Heater_Power": sett.get("heater_power", 0),
            "Recuperator_Efficiency": sett.get("recuperator_efficiency", 0),
            "T_in": t_in,
            "CO2_Level": co2_max,
            "PM_Level": pm_max,
            "Total_Energy_Consumption": total_energy
        }

    def run_batch(self, n_simulations=50):
        import idf_bridge
        import json
        results = []
        for i in range(n_simulations):
            json_project = self.generate_random_params()
            idf_data = idf_bridge.generate_idf_structure(json_project)
            success, msg, _ = run_simulation(idf_data, self.eplus_exe, self.epw_path)
            
            if success:
                df = get_results(msg)
                if not df.empty:
                    row = self.extract_features_targets(df, json.loads(json_project))
                    results.append(row)
                    
        if results:
            df_log = pd.DataFrame(results)
            os.makedirs(os.path.dirname(self.dataset_path), exist_ok=True)
            if not os.path.exists(self.dataset_path):
                df_log.to_csv(self.dataset_path, index=False)
            else:
                df_log.to_csv(self.dataset_path, mode='a', header=False, index=False)
            return True, len(results)
        return False, 0

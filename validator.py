import pandas as pd
import constants
import json
import os

class ModelValidator:
    def __init__(self, constants_dict=constants.VALIDATION_THRESHOLDS):
        self.thresholds = constants_dict

    def test_thermal_decay(self, df):
        failed = False
        warning = False
        msg = "Теплова інерція стін у нормі (плавне остигання)."
        val = 0.0
        
        if "Datetime" in df.columns and "T_in (C)" in df.columns:
            # Analyze hours 19:00 to 20:00 (after heating setpoint drops)
            df_19 = df[df["Datetime"].dt.hour == 19].copy()
            df_20 = df[df["Datetime"].dt.hour == 20].copy()
            
            if not df_19.empty and not df_20.empty:
                # Merge to find daily temp drop between 19:00 and 20:00
                df_19["Date"] = df_19["Datetime"].dt.date
                df_20["Date"] = df_20["Datetime"].dt.date
                merged = pd.merge(df_19, df_20, on="Date", suffixes=("_19", "_20"))
                
                if not merged.empty:
                    merged["Drop"] = merged["T_in (C)_19"] - merged["T_in (C)_20"]
                    max_drop = merged["Drop"].max()
                    val = max_drop
                    
                    if max_drop > 3.0: # Shifter than 3C per hour
                        warning = True
                        msg = f"Попередження: Дуже швидке охолодження приміщення (падіння на {val:.1f}°C за годину між 19:00 і 20:00). Низька теплова інерція стін."
        
        status = "Pass"
        if failed: status = "Fail"
        elif warning: status = "Warning"
        
        return {"name": "Thermal Decay (Теплова інерція)", "status": status, "value": val, "message": msg}

    def test_co2_dynamics(self, df):
        failed = False
        warning = False
        msg = "Динаміка CO₂ в нормі."
        val = 0.0
        
        if "Datetime" in df.columns and "CO2 (ppm)" in df.columns:
            max_co2 = df["CO2 (ppm)"].max()
            val = max_co2
            co2_max_thresh = self.thresholds.get("co2_max_ppm", 1600.0)
            
            if max_co2 > co2_max_thresh:
                failed = True
                msg = f"Критично: Пік CO₂ перевищує {co2_max_thresh} ppm (досягло {val:.0f} ppm). Розгляньте збільшення вентиляції."
            else:
                df_morning = df[df["Datetime"].dt.hour == 5]
                if not df_morning.empty:
                    morning_co2 = df_morning["CO2 (ppm)"].mean()
                    target = self.thresholds.get("co2_recovery_target", 500.0)
                    if morning_co2 > target + 100: 
                        warning = True
                        msg = f"Попередження: Рівень CO₂ не відновлюється вночі належним чином (о 05:00 середній рівень {morning_co2:.0f} ppm)."
        
        status = "Pass"
        if failed: status = "Fail"
        elif warning: status = "Warning"
        
        return {"name": "CO₂ Dynamics (Пік та Відновлення)", "status": status, "value": float(val), "message": msg}

    def test_heating_correlation(self, df):
        failed = False
        msg = "Опалення працює синхронно з погодними умовами."
        val = 0.0
        
        if "Heating Energy (J)" in df.columns and "T_out (C)" in df.columns:
            if df["Heating Energy (J)"].sum() > 0:
                corr = df["Heating Energy (J)"].corr(df["T_out (C)"])
                if pd.notna(corr):
                    val = corr
                    min_corr = self.thresholds.get("heating_correlation_min", -0.5)
                    if corr > min_corr:
                        failed = True
                        msg = f"Аномалія: Кореляція енергії опалення та температури надворі ({val:.2f}) не відповідає нормі (має бути ближче до -1.0)."
        else:
            msg = "Дані про споживання енергії обігрівача відсутні."
            
        status = "Pass"
        if failed: status = "Warning"
        
        return {"name": "Heating Correlation (Адекватність Опалення)", "status": status, "value": float(val), "message": msg}

    def test_hx_efficiency(self, df):
        failed = False
        msg = "Рекуператор ефективно підігріває припливне повітря."
        val = 0.0
        
        if "T_supply (C)" in df.columns and "T_out (C)" in df.columns and "T_in (C)" in df.columns:
            # We want to measure efficiency during cold conditions
            df_cold = df[df["T_out (C)"] < 5.0].copy()
            if not df_cold.empty:
                # \eta = (T_supply - T_out) / (T_in - T_out)
                df_cold["Denominator"] = df_cold["T_in (C)"] - df_cold["T_out (C)"]
                df_valid = df_cold[df_cold["Denominator"] > 2.0] # Avoid div-by-zero
                
                if not df_valid.empty:
                    df_valid["Efficiency"] = (df_valid["T_supply (C)"] - df_valid["T_out (C)"]) / df_valid["Denominator"]
                    val = df_valid["Efficiency"].mean() * 100.0 # to percentage
                    
                    if val < 10.0:
                        failed = True
                        msg = f"Помилка: Фактичний ККД теплообмінника близький до нуля ({val:.1f}%)."
                    else:
                        msg = f"Середній ККД рекуперації: {val:.1f}%."
        else:
            msg = "Температура припливного повітря (T_supply) не логується."
            
        status = "Fail" if failed else "Pass"
        return {"name": "Heat Recovery Check (ККД)", "status": status, "value": float(val), "message": msg}

    def test_anomalies(self, df):
        failed = False
        msg = "Критичних фізичних аномалій не виявлено."
        val = 0.0 # 0 = no anomalies
        
        if "T_in (C)" in df.columns and "CO2 (ppm)" in df.columns:
            min_tin = df["T_in (C)"].min()
            min_co2 = df["CO2 (ppm)"].min()
            neg_energy = False
            for col in df.columns:
                if "Energy" in col and pd.api.types.is_numeric_dtype(df[col]):
                    if df[col].min() < -1.0:
                        neg_energy = True
                        break
            
            if min_tin < 0 or min_co2 < 290 or neg_energy:
                failed = True
                val = 1.0 # 1 = anomaly found
                msg = f"Знайдено неможливі фізичні величини: T_in={min_tin:.1f}°C, CO2={min_co2:.0f} ppm, Негативна енергія={neg_energy}."
                
        status = "Fail" if failed else "Pass"
        return {"name": "Anomalies Detection (Неможливі величини)", "status": status, "value": float(val), "message": msg}

    def test_contaminant_decay(self, df):
        failed = False
        msg = "Швидкість очищення приміщення від забруднень (Decay) достатня."
        val = 0.0 # decay ratio
        
        if "Generic Contaminant" in df.columns and "Datetime" in df.columns:
            # Soldering finishes at 16:00. Check window 16:00 to 18:00
            df_16 = df[df["Datetime"].dt.hour == 16].copy()
            df_17 = df[df["Datetime"].dt.hour == 17].copy()
            
            if not df_16.empty and not df_17.empty:
                df_16["Date"] = df_16["Datetime"].dt.date
                df_17["Date"] = df_17["Datetime"].dt.date
                merged = pd.merge(df_16, df_17, on="Date", suffixes=("_16", "_17"))
                
                # Filter for days where soldering happened
                merged = merged[merged["Generic Contaminant_16"] > 0.00001]
                
                if not merged.empty:
                    merged["Ratio"] = merged["Generic Contaminant_17"] / merged["Generic Contaminant_16"]
                    val = merged["Ratio"].mean()
                    
                    max_val = self.thresholds.get("contaminant_decay_fraction", 0.5)
                    if val > max_val: # More than threshold remained
                        failed = True
                        msg = f"Попередження: Концентрація часток не встигає впасти до {(max_val)*100:.0f}% з 16:00 до 17:00 (залишається в сер. {val*100:.1f}%). Потужність вентиляції недостатня."
                    else:
                        msg = f"Швидкість осідання допустима (залишається {val*100:.1f}% через годину)."
        else:
             msg = "Дані про Generic Contaminant відсутні в наборі."
             
        status = "Fail" if failed else "Pass"
        return {"name": "Contaminant Decay (Очищення повітря)", "status": status, "value": float(val), "message": msg}

    def test_weekend_logic(self, df):
        failed = False
        msg = "Ресурс не витрачається марно на вихідних."
        val = 0.0 
        
        if "Datetime" in df.columns and "CO2 (ppm)" in df.columns:
            df_weekend = df[df["Datetime"].dt.dayofweek >= 5]
            if not df_weekend.empty:
                val = df_weekend["CO2 (ppm)"].max()
                if val > 600:
                    failed = True
                    msg = f"Аномалія: Рівень CO₂ у вихідні дні досягає {val:.0f} ppm (графік присутності людей не дотримується)."
                    
        status = "Fail" if failed else "Pass"
        return {"name": "Weekend Logic (Внутрішні виділення)", "status": status, "value": float(val), "message": msg}

    def test_dcv(self, df):
        warning = False
        msg = "Система DCV (Demand Controlled Ventilation) працює коректно."
        val = 0.0
        
        fan_cols = [c for c in df.columns if "Fan Energy" in c]
        if "CO2 (ppm)" in df.columns and fan_cols:
            fan_energy = df[fan_cols[0]]
            if fan_energy.sum() > 0:
                corr = df["CO2 (ppm)"].corr(fan_energy)
                if pd.notna(corr):
                    val = corr
                    if corr < 0.1 and df["CO2 (ppm)"].std() > 50:
                         warning = True
                         msg = f"Попередження: Кореляція енергії вентилятора та CO₂ близька до нуля ({val:.2f}). Схоже, DCV не реагує на навантаження."
                         
        status = "Warning" if warning else "Pass"
        return {"name": "DCV Check (Енергобаланс вентиляторів)", "status": status, "value": float(val), "message": msg}

    def run_all_tests(self, df, save_dir=None):
        results = [
            self.test_thermal_decay(df),
            self.test_co2_dynamics(df),
            self.test_heating_correlation(df),
            self.test_hx_efficiency(df),
            self.test_anomalies(df),
            self.test_contaminant_decay(df),
            self.test_weekend_logic(df),
            self.test_dcv(df)
        ]
        
        if save_dir and os.path.exists(save_dir):
            try:
                log_path = os.path.join(save_dir, "validation_log.json")
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("Помилка запису validation log:", e)
                
        return results



import json
import constants
import datetime
import os

# Версія модуля: 3.0.0
# Оновлено для сумісності з EnergyPlus v25.2.0 та підтримки Г-подібної геометрії

def transliterate(text: str) -> str:
    """Конвертує кирилицю в латиницю для назв E+"""
    mapping = {
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'H', 'Ґ': 'G', 'Д': 'D', 'Е': 'E', 'Є': 'Ye',
        'Ж': 'Zh', 'З': 'Z', 'И': 'Y', 'І': 'I', 'Ї': 'Yi', 'Й': 'Y', 'К': 'K', 'Л': 'L',
        'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ю': 'Yu', 'Я': 'Ya',
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e', 'є': 'ye',
        'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l',
        'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'yu', 'я': 'ya',
        ' ': '_'
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text

def generate_idf_structure(project_json: str) -> str:
    """
    Парсить JSON проекту та повертає повну структуру IDF для EnergyPlus v25.2.0.
    Генерує файл із правильною кількістю полів (враховуючи Space Name).
    """
    data = json.loads(project_json)
    geom = data.get("geometry", {})
    settings = data.get("settings", {})
    elements = data.get("elements", [])
    
    # Параметри приміщення
    l = float(geom.get("L", 11.75))
    w = float(geom.get("W", 6.30))
    h = float(geom.get("H", 3.25))
    l_cut = float(geom.get("L_cut", 5.75))
    w_cut = float(geom.get("W_cut", 2.30))
    
    # Розрахунок об'єму для Г-подібної форми
    vol = (l * w - l_cut * w_cut) * h
    
    lines = []
    lines.append("Version, 25.2;")
    
    # ---------------- Global Objects ----------------
    lines.append("SimulationControl, No, No, No, No, Yes;")
    lines.append("Timestep, 4;")
    lines.append("ScheduleTypeLimits, Temperature, -60, 200, Continuous, Temperature;\n")
    
    outdoor_co2 = constants.AIR_PHYSICS.get("outdoor_co2_ppm", 400.0)
    lines.append(f"Schedule:Constant, OutdoorCO2Schedule, Any Number, {outdoor_co2};")
    lines.append("Schedule:Constant, OutdoorGenericContaminantSchedule, Any Number, 0.0;")
    lines.append("ZoneAirContaminantBalance,")
    lines.append("    Yes,                     !- Carbon Dioxide Concentration")
    lines.append("    OutdoorCO2Schedule,      !- Outdoor Carbon Dioxide Schedule Name")
    lines.append("    Yes,                     !- Generic Contaminant Concentration")
    lines.append("    OutdoorGenericContaminantSchedule; !- Outdoor Generic Contaminant Schedule Name\n")
    
    lines.append("Building,")
    lines.append("    Recuperator Room,        !- Name")
    lines.append("    0.0,                     !- North Axis {deg}")
    lines.append("    City,                    !- Terrain")
    lines.append("    0.04,                    !- Loads Convergence Tolerance Value")
    lines.append("    0.4,                     !- Temperature Convergence Tolerance Value {deltaC}")
    lines.append("    FullExterior,            !- Solar Distribution")
    lines.append("    25,                      !- Maximum Number of Warmup Days")
    lines.append("    6;                       !- Minimum Number of Warmup Days\n")

    lines.append("GlobalGeometryRules, LowerLeftCorner, CounterClockWise, Relative;")
    
    lines.append("Site:Location, Kyiv_UA, 50.45, 30.52, 2.0, 179.0;")
    
    lines.append("RunPeriod, Annual, 1, 1, 2026, 12, 31, 2026, Thursday, Yes, Yes, No, Yes, Yes;")
    
    lines.append("ScheduleTypeLimits, Any Number, , , Continuous;")
    lines.append("Schedule:Constant, AlwaysOn, Any Number, 1.0;")

    # ---------------- Material Definitions (No Cyrillic) ----------------
    mat_name_ua = settings.get("wall_material", "Concrete")
    # Мапінг на англійські назви для запобігання помилок кодування
    mat_mapping = {"Цегла": "Brick", "Бетон": "Concrete", "Дерево": "Wood"}
    mat_name = mat_mapping.get(mat_name_ua, "Concrete")
    
    mat_props = constants.MATERIALS.get(mat_name_ua, {"conductivity": 1.74, "density": 2400, "specific_heat": 840})
    thickness = float(settings.get("wall_thickness", 0.200))
    
    lines.append("Material,")
    lines.append(f"    {mat_name}_Mat,          !- Name")
    lines.append("    MediumRough,             !- Roughness")
    lines.append(f"    {thickness:.3f},         !- Thickness {{m}}")
    lines.append(f"    {mat_props['conductivity']:.3f}, !- Conductivity")
    lines.append(f"    {mat_props['density']:.1f},      !- Density")
    lines.append(f"    {mat_props['specific_heat']:.1f}, !- Specific Heat")
    lines.append("    0.9, 0.7, 0.7;\n")

    lines.append("Material,")
    lines.append("    Insulation_Layer,        !- Name")
    lines.append("    Rough,                   !- Roughness")
    lines.append("    0.2,                     !- Thickness {m}")
    lines.append("    0.03,                    !- Conductivity")
    lines.append("    50,                      !- Density")
    lines.append("    1200,                    !- Specific Heat")
    lines.append("    0.9, 0.7, 0.7;\n")

    lines.append("Material,")
    lines.append("    Plaster_Layer,           !- Name")
    lines.append("    MediumSmooth,            !- Roughness")
    lines.append("    0.012,                   !- Thickness {m}")
    lines.append("    0.80,                    !- Conductivity")
    lines.append("    1500,                    !- Density")
    lines.append("    840,                     !- Specific Heat")
    lines.append("    0.9, 0.7, 0.7;\n")

    lines.append("WindowMaterial:SimpleGlazingSystem,")
    lines.append("    Glass_Mat,               !- Name")
    lines.append("    2.7,                     !- U-Factor {W/m2-K}")
    lines.append("    0.7,                     !- Solar Heat Gain Coefficient")
    lines.append("    0.8;                     !- Visible Transmittance\n")
    
    # ---------------- Construction Definitions ----------------
    lines.append(f"Construction, External_Wall_Cons, Insulation_Layer, {mat_name}_Mat, Plaster_Layer;")
    lines.append("Construction, Glass_Wall_Cons, Glass_Mat;")
    lines.append("Construction, Floor_Cons, Concrete_Mat;") # Використовуємо латиницю
    lines.append("Construction, DoublePane_Cons, Glass_Mat;\n")
    
    # ---------------- Zone Definition ----------------
    lines.append("Zone,")
    lines.append("    MainZone,                !- Name")
    lines.append("    0.0, 0.0, 0.0, 0.0, 1, 1,")
    lines.append(f"    {h:.2f}, {vol:.2f};\n")
    
    # ---------------- Geometry (L-Shape Logic) ----------------
    # Координати вершин (обхід проти годинникової стрілки для стін)
    x = [0.0, l, l, l - l_cut, l - l_cut, 0.0, 0.0]
    y = [0.0, 0.0, w - w_cut, w - w_cut, w, w, 0.0]
    wall_names = ["Bottom_Wall", "Right_Wall", "Inner_Top_Wall", "Inner_Right_Wall", "Top_Wall", "Left_Wall"]
    
    for i in range(6):
        wall_name = wall_names[i]
        # Усі стіни (BuildingSurface:Detailed) повинні мати непрозору (opaque) конструкцію.
        env_str = "Outdoors" if i != 3 else "Adiabatic"
        cons_str = "External_Wall_Cons"
        
        vertices = [
            (x[i], y[i], h), 
            (x[i], y[i], 0.0), 
            (x[i+1], y[i+1], 0.0), 
            (x[i+1], y[i+1], h)
        ]
        
        lines.append("BuildingSurface:Detailed,")
        lines.append(f"    {wall_name}, Wall, {cons_str}, MainZone, , {env_str}, ,")
        lines.append(f"    {'SunExposed' if env_str == 'Outdoors' else 'NoSun'},")
        lines.append(f"    {'WindExposed' if env_str == 'Outdoors' else 'NoWind'},")
        lines.append(f"    autocalculate, 4,")
        for vi, (vx, vy, vz) in enumerate(vertices):
            term = ";" if vi == 3 else ","
            lines.append(f"    {vx:.2f}, {vy:.2f}, {vz:.2f}{term}")
        lines.append("")
        
    # Floor (6 вершин, обхід за годинниковою стрілкою)
    floor_v = [(x[i], y[i], 0.0) for i in [0, 5, 4, 3, 2, 1]]
    lines.append("BuildingSurface:Detailed, Floor_1, Floor, External_Wall_Cons, MainZone, , Outdoors, , NoSun, NoWind, autocalculate, 6,")
    for vi, (vx, vy, vz) in enumerate(floor_v):
        term = ";" if vi == 5 else ","
        lines.append(f"    {vx:.2f}, {vy:.2f}, {vz:.2f}{term}")
    lines.append("")

    # Ceiling (6 вершин, обхід проти годинникової)
    ceil_v = [(x[i], y[i], h) for i in range(6)]
    lines.append("BuildingSurface:Detailed, Ceiling_1, Roof, External_Wall_Cons, MainZone, , Outdoors, , SunExposed, WindExposed, autocalculate, 6,")
    for vi, (vx, vy, vz) in enumerate(ceil_v):
        term = ";" if vi == 5 else ","
        lines.append(f"    {vx:.2f}, {vy:.2f}, {vz:.2f}{term}")
    lines.append("")

    # ---------------- Windows (Solar Gains) Phase 7.0 ----------------
    window_count = sum(1 for el in elements if el.get("Тип") == "Вікно")
    if window_count > 0:
        lines.append("FenestrationSurface:Detailed,")
        lines.append("    Lab_Window_1,            !- Name")
        lines.append("    Window,                  !- Surface Type")
        lines.append("    DoublePane_Cons,         !- Construction Name")
        lines.append("    Right_Wall,              !- Building Surface Name")
        lines.append("    ,                        !- Outside Boundary Condition Object")
        lines.append("    0.5,                     !- View Factor to Ground")
        lines.append("    ,                        !- Frame and Divider Name")
        lines.append("    1,                       !- Multiplier")
        lines.append("    4,                       !- Number of Vertices")
        lines.append(f"    {l:.2f}, 1.0, 2.0,")
        lines.append(f"    {l:.2f}, 1.0, 1.0,")
        lines.append(f"    {l:.2f}, 2.0, 1.0,")
        lines.append(f"    {l:.2f}, 2.0, 2.0;\n")
    
    # ---------------- Internal Gains & Scheduling (Phase 9.0 Master Sync) ----------------
    occupants = int(settings.get("occupants", 4))
    
    lines.append("Schedule:Compact,")
    lines.append("    Lab_Occupancy_Sched,     !- Name")
    lines.append("    Any Number,              !- Schedule Type Limits Name")
    lines.append("    Through: 12/31,          !- Field 1")
    lines.append("    For: Weekdays,           !- Field 2")
    lines.append("    Until: 09:00, 0.0,       !- Field 3")
    lines.append("    Until: 13:00, 1.0,       !- Field 4")
    lines.append("    Until: 14:00, 0.1,       !- Field 5")
    lines.append("    Until: 18:00, 1.0,       !- Field 6")
    lines.append("    Until: 24:00, 0.0,       !- Field 7")
    lines.append("    For: AllOtherDays,       !- Field 8")
    lines.append("    Until: 24:00, 0.0;       !- Field 9\n")

    lines.append("Schedule:Compact,")
    lines.append("    Equipment_Activity_Sched,!- Name")
    lines.append("    Any Number,              !- Schedule Type Limits Name")
    lines.append("    Through: 12/31,          !- Field 1")
    lines.append("    For: Weekdays,           !- Field 2")
    lines.append("    Until: 09:15, 0.0,       !- Field 3")
    lines.append("    Until: 13:00, 1.0,       !- Field 4")
    lines.append("    Until: 14:15, 0.0,       !- Field 5")
    lines.append("    Until: 18:00, 1.0,       !- Field 6")
    lines.append("    Until: 24:00, 0.0,       !- Field 7")
    lines.append("    For: AllOtherDays,       !- Field 8")
    lines.append("    Until: 24:00, 0.0;       !- Field 9\n")


    lines.append("Schedule:Constant, Lab_Activity_Spikes, Any Number, 0.0;\n")

    lines.append("EnergyManagementSystem:GlobalVariable, Daily_RND;\n")

    lines.append("EnergyManagementSystem:Actuator,")
    lines.append("    Spike_Actuator,          !- Name")
    lines.append("    Lab_Activity_Spikes,     !- Actuated Component Unique Name")
    lines.append("    Schedule:Constant,       !- Actuated Component Type")
    lines.append("    Schedule Value;          !- Actuated Component Control Type\n")

    lines.append("EnergyManagementSystem:Program,")
    lines.append("    Random_Soldering_Logic,  !- Name")
    lines.append("    IF CurrentTime <= 0.25,")
    lines.append("      SET Daily_RND = @RandomUniform 0.0 1.0,")
    lines.append("    ENDIF,")
    lines.append("    IF Daily_RND > 0.7,")
    lines.append("      IF CurrentTime > 15.0 && CurrentTime <= 16.0,")
    lines.append("        SET Spike_Actuator = 1.0,")
    lines.append("      ELSE,")
    lines.append("        SET Spike_Actuator = 0.0,")
    lines.append("      ENDIF,")
    lines.append("    ELSE,")
    lines.append("      SET Spike_Actuator = 0.0,")
    lines.append("    ENDIF;\n")

    lines.append("EnergyManagementSystem:ProgramCallingManager,")
    lines.append("    Spike_Manager,           !- Name")
    lines.append("    BeginTimestepBeforePredictor, !- EnergyPlus Model Calling Point")
    lines.append("    Random_Soldering_Logic;  !- Program Name 1\n")

    lines.append("People,")
    lines.append("    Lab_Students,            !- Name")
    lines.append("    MainZone,                !- Zone Name")
    lines.append("    Lab_Occupancy_Sched,     !- Number of People Schedule Name")
    lines.append("    People,                  !- Number of People Calculation Method")
    lines.append(f"    {occupants},             !- Number of People")
    lines.append("    ,                        !- People per Floor Area")
    lines.append("    ,                        !- Floor Area per Person")
    lines.append("    0.3,                     !- Fraction Radiant")
    lines.append("    autocalculate,           !- Sensible Heat Fraction")
    lines.append("    ActivityLevel,           !- Activity Level Schedule Name")
    lines.append("    3.82E-8;                 !- Carbon Dioxide Generation Rate {m3/s-W}\n")
    
    lines.append("Schedule:Constant, ActivityLevel, Any Number, 120.0;\n")

    # ---------------- IT Load & Lab Equipment ----------------
    lines.append("ElectricEquipment,")
    lines.append("    Workstations,            !- Name")
    lines.append("    MainZone,                !- Zone Name")
    lines.append("    Equipment_Activity_Sched,!- Schedule Name")
    lines.append("    EquipmentLevel,          !- Design Level Calculation Method")
    lines.append("    1200.0,                  !- Design Level {W} (4x300W)")
    lines.append("    ,                        !- Watts per Zone Floor Area")
    lines.append("    ,                        !- Watts per Person")
    lines.append("    0.0,                     !- Fraction Latent")
    lines.append("    0.3,                     !- Fraction Radiant")
    lines.append("    0.2;                     !- Fraction Lost\n")

    printer_active = float(settings.get("printer_active", 1.0))
    lines.append("ElectricEquipment,")
    lines.append("    3D_Printer_Heat,         !- Name")
    lines.append("    MainZone,                !- Zone Name")
    lines.append("    Equipment_Activity_Sched,!- Schedule Name")
    lines.append("    EquipmentLevel,          !- Design Level Calculation Method")
    lines.append(f"    {500.0 * printer_active}, !- Design Level {{W}}")
    lines.append("    ,                        !- Watts per Zone Floor Area")
    lines.append("    ,                        !- Watts per Person")
    lines.append("    0.0,                     !- Fraction Latent")
    lines.append("    0.2,                     !- Fraction Radiant")
    lines.append("    0.1;                     !- Fraction Lost\n")

    lines.append("Lights,")
    lines.append("    Lab_Lights,              !- Name")
    lines.append("    MainZone,                !- Zone Name")
    lines.append("    Lab_Occupancy_Sched,     !- Schedule Name")
    lines.append("    Watts/Area,              !- Design Level Calculation Method")
    lines.append("    ,                        !- Lighting Level")
    lines.append("    10.0,                    !- Watts per Zone Floor Area")
    lines.append("    ,                        !- Watts per Person")
    lines.append("    0.0,                     !- Return Air Fraction")
    lines.append("    0.4,                     !- Fraction Radiant")
    lines.append("    0.2,                     !- Fraction Visible")
    lines.append("    1.0,                     !- Fraction Replaceable")
    lines.append("    General;                 !- End-Use Subcategory\n")

    # ---------------- Contaminants Tuning (VOC + PM -> Generic) ----------------
    soldering_active = float(settings.get("soldering_active", 1.0))
    emissions_rate = (0.0001 + (0.0009 * soldering_active)) * 10.0
    printer_emissions = (0.0002 * printer_active) * 10.0

    lines.append("ZoneContaminantSourceAndSink:Generic:Constant,")
    lines.append("    Soldering_Emissions,     !- Name")
    lines.append("    MainZone,                !- Zone Name")
    lines.append(f"    {emissions_rate:.6f},    !- Design Generation Rate {{m3/s}}")
    lines.append("    Lab_Activity_Spikes,     !- Schedule Name")
    lines.append("    0.0,                     !- Design Removal Coefficient")
    lines.append("    AlwaysOn;                !- Removal Schedule Name\n")

    lines.append("ZoneContaminantSourceAndSink:Generic:Constant,")
    lines.append("    Printer_Dust,            !- Name")
    lines.append("    MainZone,                !- Zone Name")
    lines.append(f"    {printer_emissions:.6f}, !- Design Generation Rate {{m3/s}}")
    lines.append("    Lab_Activity_Spikes,     !- Schedule Name")
    lines.append("    0.0,                     !- Design Removal Coefficient")
    lines.append("    AlwaysOn;                !- Removal Schedule Name\n")

    # ---------------- HVAC & Ventilation ----------------
    # ---------------- Demand Controlled Ventilation (EMS) ----------------
    lines.append("Schedule:Constant, ERV_DCV_Fraction, Any Number, 1.0;\n")
    
    lines.append("EnergyManagementSystem:Sensor,")
    lines.append("    Zone_CO2,                !- Name")
    lines.append("    MainZone,                !- Output:Variable or Output:Meter Index Key Name")
    lines.append("    Zone Air CO2 Concentration; !- Output:Variable or Output:Meter Name\n")
    
    lines.append("EnergyManagementSystem:Sensor,")
    lines.append("    Zone_PM,                 !- Name")
    lines.append("    MainZone,                !- Output:Variable or Output:Meter Index Key Name")
    lines.append("    Zone Air Generic Air Contaminant Concentration; !- Output:Variable or Output:Meter Name\n")

    lines.append("EnergyManagementSystem:Actuator,")
    lines.append("    Supply_Fan_Act,          !- Name")
    lines.append("    Supply_Fan,              !- Actuated Component Unique Name")
    lines.append("    Fan,                     !- Actuated Component Type")
    lines.append("    Fan Air Mass Flow Rate;  !- Actuated Component Control Type\n")

    lines.append("EnergyManagementSystem:Actuator,")
    lines.append("    Exhaust_Fan_Act,         !- Name")
    lines.append("    Exhaust_Fan,             !- Actuated Component Unique Name")
    lines.append("    Fan,                     !- Actuated Component Type")
    lines.append("    Fan Air Mass Flow Rate;  !- Actuated Component Control Type\n")

    vent_rate = (occupants * constants.AIR_PHYSICS.get("fresh_air_standard", 30.0)) / 3600.0

    lines.append("EnergyManagementSystem:Program,")
    lines.append("    DCV_Control,             !- Name")
    lines.append("    SET CO2_PPM = Zone_CO2,")
    lines.append("    IF CO2_PPM < 450,")
    lines.append("      SET Fan_CO2 = 0.1,")
    lines.append("    ELSEIF CO2_PPM > 900,")
    lines.append("      SET Fan_CO2 = 1.0,")
    lines.append("    ELSE,")
    lines.append("      SET Fan_CO2 = 0.1 + ((CO2_PPM - 450) / 450) * 0.9,")
    lines.append("    ENDIF,")
    lines.append("    SET PM_Val = Zone_PM,")
    lines.append("    IF PM_Val > 0.000005,")
    lines.append("      SET Fan_PM = 1.0,")
    lines.append("    ELSE,")
    lines.append("      SET Fan_PM = 0.1 + (PM_Val / 0.000005) * 0.9,")
    lines.append("    ENDIF,")
    lines.append("    SET Fan_Frac = @Max Fan_CO2 Fan_PM,")
    lines.append(f"    SET StdRho = 1.204,")
    lines.append(f"    SET MassFlow = Fan_Frac * {vent_rate:.5f} * StdRho,")
    lines.append("    SET Supply_Fan_Act = MassFlow,")
    lines.append("    SET Exhaust_Fan_Act = MassFlow;\n")

    lines.append("EnergyManagementSystem:ProgramCallingManager,")
    lines.append("    DCV_Manager,             !- Name")
    lines.append("    InsideHVACSystemIterationLoop, !- EnergyPlus Model Calling Point")
    lines.append("    DCV_Control;             !- Program Name 1\n")
    hx_eff = float(settings.get("recuperator_efficiency", 75))
    if hx_eff > 1.0:
        hx_eff = hx_eff / 100.0

    lines.append("DesignSpecification:OutdoorAir,")
    lines.append("    Lab_OutdoorAir_Spec,     !- Name")
    lines.append("    Sum,                     !- Outdoor Air Method")
    lines.append("    0.008,                   !- Outdoor Air Flow per Person {m3/s}")
    lines.append("    0.001;                   !- Outdoor Air Flow per Zone Floor Area {m3/s}\n")

    lines.append("ZoneHVAC:EnergyRecoveryVentilator,")
    lines.append("    Lab_Recuperator,         !- Name")
    lines.append("    AlwaysOn,                !- Availability Schedule Name")
    lines.append("    Lab_HX,                  !- Heat Exchanger Name")
    lines.append(f"    {vent_rate:.5f},         !- Supply Air Flow Rate {{m3/s}}")
    lines.append(f"    {vent_rate:.5f},         !- Exhaust Air Flow Rate {{m3/s}}")
    lines.append("    Supply_Fan,              !- Supply Air Fan Name")
    lines.append("    Exhaust_Fan;             !- Exhaust Air Fan Name\n")

    lines.append("HeatExchanger:AirToAir:SensibleAndLatent,")
    lines.append("    Lab_HX,                  !- Name")
    lines.append("    AlwaysOn,                !- Availability Schedule Name")
    lines.append(f"    {vent_rate:.5f},         !- Nominal Supply Air Flow Rate {{m3/s}}")
    lines.append(f"    {hx_eff:.2f},            !- Nominal Sensible Effectiveness at 100% Heating Air Flow")
    lines.append(f"    {hx_eff:.2f},            !- Nominal Latent Effectiveness at 100% Heating Air Flow")
    lines.append(f"    {hx_eff:.2f},            !- Nominal Sensible Effectiveness at 100% Cooling Air Flow")
    lines.append(f"    {hx_eff:.2f},            !- Nominal Latent Effectiveness at 100% Cooling Air Flow")
    lines.append("    ERV_OA_Inlet,            !- Supply Air Inlet Node Name")
    lines.append("    ERV_HX_Supply_Out,       !- Supply Air Outlet Node Name")
    lines.append("    ERV_RA_Inlet,            !- Exhaust Air Inlet Node Name")
    lines.append("    ERV_HX_Exhaust_Out;      !- Exhaust Air Outlet Node Name\n")

    lines.append("Curve:Cubic,")
    lines.append("    FanPowerCurve,           !- Name")
    lines.append("    0.0408,                  !- Coefficient1 Constant")
    lines.append("    0.088,                   !- Coefficient2 x")
    lines.append("    -0.0729,                 !- Coefficient3 x**2")
    lines.append("    0.9437,                  !- Coefficient4 x**3")
    lines.append("    0.0,                     !- Minimum Value of x")
    lines.append("    1.0;                     !- Maximum Value of x\n")

    lines.append("Fan:SystemModel,")
    lines.append("    Supply_Fan,              !- Name")
    lines.append("    AlwaysOn,                !- Availability Schedule Name")
    lines.append("    ERV_HX_Supply_Out,       !- Air Inlet Node Name")
    lines.append("    ERV_SA_Outlet,           !- Air Outlet Node Name")
    lines.append(f"    {vent_rate:.5f},         !- Design Maximum Air Flow Rate {{m3/s}}")
    lines.append("    Continuous,              !- Speed Control Method")
    lines.append("    0.001,                   !- Electric Power Minimum Flow Rate Fraction")
    lines.append("    75.0,                    !- Design Pressure Rise {Pa}")
    lines.append("    0.9,                     !- Motor Efficiency")
    lines.append("    1.0,                     !- Motor In Air Stream Fraction")
    lines.append("    autocalculate,           !- Design Electrical Power Consumption")
    lines.append("    PowerPerFlowPerPressure, !- Design Power Sizing Method")
    lines.append("    ,                        !- Electric Power Per Unit Flow Rate")
    lines.append("    1.66667,                 !- Electric Power Per Unit Flow Rate Per Unit Pressure")
    lines.append("    0.7,                     !- Fan Total Efficiency")
    lines.append("    FanPowerCurve;           !- Electric Power Function of Flow Fraction Curve Name\n")

    lines.append("Fan:SystemModel,")
    lines.append("    Exhaust_Fan,             !- Name")
    lines.append("    AlwaysOn,                !- Availability Schedule Name")
    lines.append("    ERV_HX_Exhaust_Out,      !- Air Inlet Node Name")
    lines.append("    ERV_EA_Outlet,           !- Air Outlet Node Name")
    lines.append(f"    {vent_rate:.5f},         !- Design Maximum Air Flow Rate {{m3/s}}")
    lines.append("    Continuous,              !- Speed Control Method")
    lines.append("    0.1,                     !- Electric Power Minimum Flow Rate Fraction")
    lines.append("    75.0,                    !- Design Pressure Rise {Pa}")
    lines.append("    0.9,                     !- Motor Efficiency")
    lines.append("    1.0,                     !- Motor In Air Stream Fraction")
    lines.append("    autocalculate,           !- Design Electrical Power Consumption")
    lines.append("    PowerPerFlowPerPressure, !- Design Power Sizing Method")
    lines.append("    ,                        !- Electric Power Per Unit Flow Rate")
    lines.append("    1.66667,                 !- Electric Power Per Unit Flow Rate Per Unit Pressure")
    lines.append("    0.7,                     !- Fan Total Efficiency")
    lines.append("    FanPowerCurve;           !- Electric Power Function of Flow Fraction Curve Name\n")

    lines.append("OutdoorAir:Node, ERV_OA_Inlet;\n")

    lines.append("ZoneInfiltration:DesignFlowRate,")
    lines.append("    Lab_Infiltration,        !- Name")
    lines.append("    MainZone,                !- Zone Name")
    lines.append("    AlwaysOn,                !- Schedule Name")
    lines.append("    Flow/Zone,               !- Design Flow Rate Calculation Method")
    lines.append("    0.015,                   !- Design Flow Rate {m3/s}")
    lines.append("    ,                        !- Flow per Zone Floor Area")
    lines.append("    ,                        !- Flow per Exterior Surface Area")
    lines.append("    ,                        !- Air Changes per Hour")
    lines.append("    0.2,                     !- Constant Term Coefficient")
    lines.append("    0.0,                     !- Temperature Term Coefficient")
    lines.append("    0.0,                     !- Velocity Term Coefficient")
    lines.append("    0.032;                   !- Velocity Squared Term Coefficient\n")

    # ---------------- Thermostats and Heaters ----------------
    lines.append("Schedule:Compact, HVACAvailability, Any Number, Through: 12/31, For: AllDays, Until: 24:00, 1.0;")
    lines.append("Schedule:Compact, ZoneControl_DualSetpoint, Any Number, Through: 12/31, For: AllDays, Until: 24:00, 4;\n")
    
    lines.append("Schedule:Compact,")
    lines.append("    Heating_Setpoint_Sched,  !- Name")
    lines.append("    Any Number,              !- Schedule Type Limits Name")
    lines.append("    Through: 12/31,          !- Field 1")
    lines.append("    For: AllDays,            !- Field 2")
    lines.append("    Until: 24:00, 20.0;      !- Field 3\n")
    
    lines.append("ZoneControl:Thermostat,")
    lines.append("    MainZone_Thermostat,     !- Name")
    lines.append("    MainZone,                !- Zone Name")
    lines.append("    ZoneControl_DualSetpoint,!- Control Type Schedule Name")
    lines.append("    ThermostatSetpoint:DualSetpoint, !- Control 1 Object Type")
    lines.append("    Lab_Temperature_Setpoints; !- Control 1 Name\n")

    lines.append("Schedule:Compact,")
    lines.append("    Cooling_Setpoint_Sched,  !- Name")
    lines.append("    Any Number,              !- Schedule Type Limits Name")
    lines.append("    Through: 12/31,          !- Field 1")
    lines.append("    For: AllDays,            !- Field 2")
    lines.append("    Until: 24:00, 24.0;      !- Field 3\n")

    lines.append("ThermostatSetpoint:DualSetpoint,")
    lines.append("    Lab_Temperature_Setpoints, !- Name")
    lines.append("    Heating_Setpoint_Sched,  !- Heating Setpoint Temperature Schedule Name")
    lines.append("    Cooling_Setpoint_Sched;  !- Cooling Setpoint Temperature Schedule Name\n")

    lines.append("ZoneHVAC:IdealLoadsAirSystem,")
    lines.append("    Lab_AC_System,           !- Name")
    lines.append("    HVACAvailability,        !- Availability Schedule Name")
    lines.append("    Ideal_Loads_Inlet,       !- Zone Supply Air Node Name")
    lines.append("    Zone_Return_Node,        !- Zone Exhaust Air Node Name")
    lines.append("    ,                        !- System Inlet Air Node Name")
    lines.append("    50,                      !- Maximum Heating Supply Air Temperature {C}")
    lines.append("    13,                      !- Minimum Cooling Supply Air Temperature {C}")
    lines.append("    0.015,                   !- Maximum Heating Supply Air Humidity Ratio {kgWater/kgDryAir}")
    lines.append("    0.009,                   !- Minimum Cooling Supply Air Humidity Ratio {kgWater/kgDryAir}")
    lines.append("    NoLimit,                 !- Heating Limit")
    lines.append("    autocalculate,           !- Maximum Heating Air Flow Rate {m3/s}")
    lines.append("    ,                        !- Maximum Sensible Heating Capacity {W}")
    lines.append("    NoLimit,                 !- Cooling Limit")
    lines.append("    autocalculate,           !- Maximum Cooling Air Flow Rate {m3/s}")
    lines.append("    ,                        !- Maximum Total Cooling Capacity {W}")
    lines.append("    HVACAvailability,        !- Heating Availability Schedule Name")
    lines.append("    HVACAvailability,        !- Cooling Availability Schedule Name")
    lines.append("    ConstantSupplyHumidityRatio, !- Dehumidification Control Type")
    lines.append("    0.7,                     !- Cooling Sensible Heat Ratio {dimensionless}")
    lines.append("    ConstantSupplyHumidityRatio; !- Humidification Control Type\n")

    lines.append("ZoneHVAC:EquipmentConnections,")
    lines.append("    MainZone,                !- Zone Name")
    lines.append("    Zone_Equipment,          !- Zone Conditioning Equipment List Name")
    lines.append("    Zone_Inlet_Nodes,        !- Zone Air Inlet Node or NodeList Name")
    lines.append("    Zone_Exhaust_Nodes,      !- Zone Air Exhaust Node or NodeList Name")
    lines.append("    Zone_Node,               !- Zone Air Node Name")
    lines.append("    Zone_Return_Node;        !- Zone Return Air Node Name\n")

    lines.append("ZoneHVAC:EquipmentList,")
    lines.append("    Zone_Equipment,          !- Name")
    lines.append("    SequentialLoad,          !- Load Distribution Scheme")
    lines.append("    ZoneHVAC:EnergyRecoveryVentilator, !- Equipment 1 Object Type")
    lines.append("    Lab_Recuperator,         !- Equipment 1 Name")
    lines.append("    1,                       !- Equipment 1 Cooling Sequence")
    lines.append("    1,                       !- Equipment 1 Heating or No-Load Sequence")
    lines.append("    ,                        !- Equipment 1 Sequential Cooling Fraction Schedule Name")
    lines.append("    ,                        !- Equipment 1 Sequential Heating Fraction Schedule Name")
    lines.append("    ZoneHVAC:IdealLoadsAirSystem, !- Equipment 2 Object Type")
    lines.append("    Lab_AC_System,           !- Equipment 2 Name")
    lines.append("    2,                       !- Equipment 2 Cooling Sequence")
    lines.append("    2,                       !- Equipment 2 Heating or No-Load Sequence")
    lines.append("    ,                        !- Equipment 2 Sequential Cooling Fraction Schedule Name")
    lines.append("    ;                        !- Equipment 2 Sequential Heating Fraction Schedule Name\n")

    lines.append("NodeList, Zone_Inlet_Nodes, ERV_SA_Outlet, Ideal_Loads_Inlet;")
    lines.append("NodeList, Zone_Exhaust_Nodes, ERV_RA_Inlet;\n")
    # ---------------- Outputs ----------------
    lines.append("\nOutput:VariableDictionary, Regular;")
    lines.append("Output:Diagnostics, DisplayUnusedObjects, DisplayAdvancedReportVariables;")
    lines.append("\nOutput:Variable, *, Site Outdoor Air Drybulb Temperature, Hourly;")
    lines.append("Output:Variable, *, Site Wind Speed, Hourly;")
    lines.append("Output:Variable, *, Zone Mean Air Temperature, Hourly;")
    lines.append("Output:Variable, *, Zone Air CO2 Concentration, Hourly;")
    lines.append("Output:Variable, *, Zone Air Generic Air Contaminant Concentration, Hourly;")
    lines.append("Output:Variable, *, Zone Infiltration Standard Density Volume Flow Rate, Hourly;")
    lines.append("Output:Variable, *, Heat Exchanger Sensible Heating Energy, Hourly;")
    lines.append("Output:Variable, *, Fan Electricity Energy, Hourly;")
    lines.append("Output:Variable, *, Zone Air System Sensible Heating Energy, Hourly;")
    lines.append("Output:Variable, *, Zone Air System Sensible Cooling Energy, Hourly;")
    lines.append("Output:Variable, ERV_SA_Outlet, System Node Temperature, Hourly;")
    lines.append("Output:Meter, Electricity:Facility, Hourly;")
    lines.append("OutputControl:Table:Style, Comma;")
    
    return "\n".join(lines)

def save_simulation_idf(project_json: str, directory: str = "simulations"):
    """
    Генерує IDF та зберігає його у файл з унікальним іменем simulation(timestamp).idf
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"simulation_{timestamp}.idf"
    filepath = os.path.join(directory, filename)
    
    idf_content = generate_idf_structure(project_json)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(idf_content)
        
    return filepath
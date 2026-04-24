import sys

file_path = "d:/diploma/HIVanalyzer/main.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 1. Add import statements near the top
import_idx = 0
for i, line in enumerate(lines):
    if line.startswith("import streamlit as st"):
        import_idx = i + 1
        break

lines.insert(import_idx, "from ui.tabs import geometry_tab, climate_tab, advisor_tab, save_tab, data_gen_tab, ai_lab_tab\n")

# 2. Find where the tabs section starts
tab_start_idx = 0
for i, line in enumerate(lines):
    if line.startswith("with tab1:"):
        tab_start_idx = i
        break

new_lines = lines[:tab_start_idx]

new_code = """with tab1:
    geometry_tab.render(room_l, room_w, room_l_cut, room_w_cut)

with tab2:
    climate_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

with tab_DigitalDual:
    advisor_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

with tab3:
    save_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

if dev_mode:
    with tab4:
        data_gen_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)

    with tabAI_Lab:
        ai_lab_tab.render(room_l, room_w, room_h, room_l_cut, room_w_cut)
"""

new_lines.append(new_code)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Updated main.py successfully.")

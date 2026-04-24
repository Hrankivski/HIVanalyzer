import re
import os

with open("d:/diploma/HIVanalyzer/main.py", "r", encoding="utf-8") as f:
    content = f.read()

def extract_block(source, start_marker):
    lines = source.split('\n')
    in_block = False
    block_lines = []
    base_indent = 0
    for line in lines:
        if line.startswith(start_marker):
            in_block = True
            base_indent = len(line) - len(line.lstrip())
            continue
        if in_block:
            current_indent = len(line) - len(line.lstrip())
            if line.strip() != "" and current_indent <= base_indent:
                break
            block_lines.append(line[base_indent+4:] if len(line) >= base_indent+4 else line.strip())
            
    return "\n".join(block_lines)

climate = extract_block(content, "with tab2:")
advisor = extract_block(content, "with tab_DigitalDual:")
data_gen = extract_block(content, "    with tab4:")
ai_lab = extract_block(content, "    with tabAI_Lab:")

def write_tab(filename, code, extra_imports=""):
    header = '''import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from core import constants
from ui import designer
from simulation import idf_bridge, simulation_engine, validator
from ai import rl_agent, ai_engine, ml_surrogate
import plotly.graph_objects as go
''' + extra_imports + '''

def render(room_l, room_w, room_h, room_l_cut, room_w_cut):
'''
    indented_code = "\n".join("    " + line for line in code.split("\n"))
    with open(f"d:/diploma/HIVanalyzer/ui/tabs/{filename}", "w", encoding="utf-8") as f:
        f.write(header + indented_code)

write_tab("climate_tab.py", climate)
write_tab("advisor_tab.py", advisor)
write_tab("data_gen_tab.py", data_gen)
write_tab("ai_lab_tab.py", ai_lab)
print("Extracted successfully.")

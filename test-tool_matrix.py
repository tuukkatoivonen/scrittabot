#!/usr/bin/env python3

import json
import time

import tool_matrix

CONFIG_FILE = 'config.json'

with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

tools_matrix = tool_matrix.ToolSetMatrix(config)

while True:
    matrix_events = tools_matrix.get_events()
    if matrix_events:
        print(matrix_events)
    time.sleep(1)



#!/bin/bash
source venv/bin/activate
python integrated_bot.py &
PYTHON_PID=$!
sleep 3
kill $PYTHON_PID 2>/dev/null

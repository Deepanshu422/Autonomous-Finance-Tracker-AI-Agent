#!/bin/bash

API_PORT=${PORT:-7860}

# 1. Start FastAPI in the background on port 7860 (Hugging Face default)
uvicorn app.main:app --host 0.0.0.0 --port $API_PORT &

# 2. Start the Node.js WhatsApp bridge in the background
cd whatsapp-bridge && node bridge.js &

# 3. Wait for any background process to exit
wait -n
exit $?

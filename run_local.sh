#!/bin/bash

# Sprawdź czy venv istnieje
if [ ! -d ".venv" ]; then
    echo "📦 Tworzenie wirtualnego środowiska..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi

echo "🔌 Aktywacja środowiska i instalacja zależności..."
source .venv/bin/activate

echo "🚀 Uruchamianie CdA Kalkulator..."
echo "   Otwórz: http://127.0.0.1:8501/"
streamlit run app.py \
  --server.port=8501 \
  --server.headless=false \
  --server.baseUrlPath=""

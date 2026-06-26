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
streamlit run app.py

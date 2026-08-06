#!/bin/bash

echo "=== DevJourney ==="
echo ""

if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Instalando dependencias..."
pip install -r requirements.txt -q 2>&1

echo ""
echo "Iniciando servidor em http://localhost:8000"
echo "Pressione Ctrl+C para parar"
echo ""

python main.py

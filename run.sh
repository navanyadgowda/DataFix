#!/usr/bin/env bash
# =====================================================================
#        DataFix - Autonomous Data Quality and Repair Engine
# =====================================================================

set -e

echo "====================================================================="
echo "       DataFix - Autonomous Data Quality and Repair Engine"
echo "====================================================================="
echo ""

# Check python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

# Setup virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating Python virtual environment in ./venv ..."
    python3 -m venv venv
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

echo "[INFO] Installing / updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "====================================================================="
echo "[INFO] Launching DataFix Dashboard on http://localhost:8501 ..."
echo "====================================================================="
echo ""
streamlit run app.py

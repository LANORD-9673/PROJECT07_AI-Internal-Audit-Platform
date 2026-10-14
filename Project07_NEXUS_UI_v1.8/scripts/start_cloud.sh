#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port "${PORT:-8501}"

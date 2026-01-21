#!/bin/bash

# Quick script to run the News Radar Dashboard

cd "$(dirname "$0")"

echo "📁 Starting News Radar Dashboard..."
echo "📁 Directory: $(pwd)"
echo ""

# Activate virtual environment
source venv/bin/activate

# Run Streamlit
streamlit run news_dashboard.py

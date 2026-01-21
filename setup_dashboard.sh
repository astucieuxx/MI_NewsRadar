#!/bin/bash

# Setup script for News Radar Dashboard
# This will activate the virtual environment and install Streamlit

cd "$(dirname "$0")"

echo "📁 Current directory: $(pwd)"
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if we're in the venv
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Install Streamlit
echo ""
echo "📦 Installing Streamlit..."
pip install streamlit

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the dashboard, use:"
echo "  source venv/bin/activate"
echo "  streamlit run news_dashboard.py"
echo ""
echo "Or run this script again and it will start the dashboard automatically."

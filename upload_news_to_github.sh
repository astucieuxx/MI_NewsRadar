#!/bin/bash

# Script to run pipelines locally and upload results to GitHub
# This allows the LLM to run locally (where it works) and share results via GitHub

cd "$(dirname "$0")"

echo "📰 Running News Pipelines Locally..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Run CCaaS pipeline
echo "🔄 Running CCaaS pipeline..."
python3 ccaas_news_pipeline.py

# Run ES pipeline
echo "🔄 Running ES pipeline..."
python3 es_news_pipeline.py

echo ""
echo "✅ Pipelines completed!"
echo ""

# Get today's date for CSV files
TODAY=$(date +%Y-%m-%d)
CCaaS_FILE="ccaas_news_${TODAY}.csv"
ES_FILE="es_news_${TODAY}.csv"

# Check if files were created
if [ ! -f "$CCaaS_FILE" ]; then
    echo "⚠️ Warning: $CCaaS_FILE not found"
fi

if [ ! -f "$ES_FILE" ]; then
    echo "⚠️ Warning: $ES_FILE not found"
fi

# Add CSV files to git (temporarily allow them)
echo "📤 Uploading results to GitHub..."
git add "$CCaaS_FILE" "$ES_FILE" 2>/dev/null || true

# Commit and push
if git diff --staged --quiet; then
    echo "ℹ️ No changes to commit (CSVs may already be up to date)"
else
    git commit -m "Update news data for ${TODAY}" || echo "⚠️ Nothing to commit"
    git push || echo "⚠️ Push failed - you may need to push manually"
    echo "✅ Results uploaded to GitHub!"
fi

echo ""
echo "🎉 Done! Your colleagues can now see the latest news in Streamlit Cloud."

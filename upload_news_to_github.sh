#!/bin/bash

# Script to run pipelines locally and upload results to GitHub
# This allows the LLM to run locally (where it works) and share results via GitHub

cd "$(dirname "$0")"

echo "📰 Running News Pipelines Locally..."
echo ""

# Use venv Python directly (no need to activate)
VENV_PYTHON="./venv/bin/python3"

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Error: Virtual environment not found at venv/bin/python3"
    echo "   Please make sure you're in the correct directory and venv is set up."
    exit 1
fi

# Run CCaaS pipeline
echo "🔄 Running CCaaS pipeline..."
$VENV_PYTHON ccaas_news_pipeline.py

# Run ES pipeline
echo "🔄 Running ES pipeline..."
$VENV_PYTHON es_news_pipeline.py

# Run CX AI pipeline
echo "🔄 Running CX AI pipeline..."
$VENV_PYTHON cx_ai_news_pipeline.py

echo ""
echo "✅ Pipelines completed!"
echo ""

# Get today's date for CSV files
TODAY=$(date +%Y-%m-%d)
CCaaS_FILE="ccaas_news_${TODAY}.csv"
ES_FILE="es_news_${TODAY}.csv"
CX_AI_FILE="cx_ai_news_${TODAY}.csv"

# Check if files were created
FILES_TO_ADD=()
if [ -f "$CCaaS_FILE" ]; then
    FILES_TO_ADD+=("$CCaaS_FILE")
    echo "✅ Found: $CCaaS_FILE"
else
    echo "⚠️ Warning: $CCaaS_FILE not found"
fi

if [ -f "$ES_FILE" ]; then
    FILES_TO_ADD+=("$ES_FILE")
    echo "✅ Found: $ES_FILE"
else
    echo "⚠️ Warning: $ES_FILE not found"
fi

if [ -f "$CX_AI_FILE" ]; then
    FILES_TO_ADD+=("$CX_AI_FILE")
    echo "✅ Found: $CX_AI_FILE"
else
    echo "⚠️ Warning: $CX_AI_FILE not found"
fi

# Only proceed if at least one file was created
if [ ${#FILES_TO_ADD[@]} -eq 0 ]; then
    echo "❌ Error: No CSV files were generated. Please check the pipeline logs above."
    exit 1
fi

# Add CSV files to git
echo ""
echo "📤 Uploading results to GitHub..."
git add "${FILES_TO_ADD[@]}" 2>/dev/null || true

# Commit and push
if git diff --staged --quiet; then
    echo "ℹ️ No changes to commit (CSVs may already be up to date)"
else
    git commit -m "Update news data for ${TODAY}" || echo "⚠️ Commit failed"
    if git push; then
        echo "✅ Results uploaded to GitHub!"
    else
        echo "⚠️ Push failed - you may need to push manually with: git push"
    fi
fi

echo ""
echo "🎉 Done! Your colleagues can now see the latest news in Streamlit Cloud."

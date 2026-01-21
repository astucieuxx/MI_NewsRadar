#!/bin/bash

# Daily News Pipeline Runner
# This script runs both news pipelines daily
# Set this up as a cron job to run automatically every morning

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Get current date for logging
DATE=$(date +"%Y-%m-%d %H:%M:%S")
echo "[$DATE] Starting daily news pipeline..."

# Run CCaaS pipeline
echo "[$DATE] Running CCaaS pipeline..."
python ccaas_news_pipeline.py

# Run ES pipeline
echo "[$DATE] Running ES pipeline..."
python es_news_pipeline.py

echo "[$DATE] Daily news pipeline completed."

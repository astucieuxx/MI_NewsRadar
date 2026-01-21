# News Radar Dashboard

A Streamlit dashboard for monitoring and analyzing industry news related to CCaaS/CX and Employee Service/ITSM, powered by automated web scraping and AI analysis.

## Features

- 📰 **Automated News Scraping**: Scrapes news from multiple industry sources
- 🤖 **AI-Powered Analysis**: Uses Zendesk AI Gateway to analyze articles for relevance, engagement, and key insights
- 📊 **Interactive Dashboard**: Beautiful, modern interface for reviewing news ranked by priority
- 📋 **Slack Integration**: Generate ready-to-copy Slack posts for each article
- 🔄 **Daily Updates**: Run pipelines directly from the dashboard to get fresh news

## Setup

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/astucieuxx/MI_NewsRadar.git
   cd MI_NewsRadar
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API Key**
   - Open `ccaas_news_pipeline.py` and `es_news_pipeline.py`
   - Update `ZENDESK_AI_KEY` with your actual API key

5. **Run the dashboard**
   ```bash
   streamlit run news_dashboard.py
   ```

### Streamlit Cloud Deployment

1. **Push to GitHub** (already done if you're reading this)

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Sign in with your GitHub account
   - Click "New app"
   - Select repository: `astucieuxx/MI_NewsRadar`
   - Main file path: `news_dashboard.py`
   - Click "Deploy!"

3. **Configure Secrets (Optional)**
   - If you want to use environment variables for the API key instead of hardcoding it:
   - Go to your app settings → Secrets
   - Add: `ZENDESK_AI_KEY = "your-key-here"`

4. **Using the Dashboard**
   - Click "🔄 Run Pipelines & Refresh" in the sidebar to fetch fresh news
   - The pipelines will run on Streamlit Cloud's servers
   - Generated CSV files are stored temporarily on the server
   - Select a date to view news from that day

## How It Works

1. **News Scraping**: The pipelines scrape articles from configured news sources
2. **Filtering**: Articles are filtered by date (last 24-96 hours) and relevance
3. **AI Analysis**: Each article is analyzed by the LLM for:
   - Summary
   - Engagement level (HIGH/MEDIUM/LOW)
   - Hook (key insight)
4. **Dashboard Display**: News is displayed ranked by engagement, with filters and search

## File Structure

```
MI_NewsRadar/
├── news_dashboard.py          # Main Streamlit dashboard
├── ccaas_news_pipeline.py      # CCaaS/CX news pipeline
├── es_news_pipeline.py         # Employee Service/ITSM news pipeline
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## Notes

- CSV files are generated daily and stored locally (not committed to Git)
- The dashboard automatically loads the most recent available date
- Pipelines may take 5-10 minutes to run, depending on the number of articles
- The dashboard is optimized for Zendesk's brand colors and design

## Author

Benjamin Miranda (Market Intelligence Lead)

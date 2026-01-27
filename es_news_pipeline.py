import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import json
import datetime
import pandas as pd
from dateutil import parser as dateparser
from urllib.parse import urlparse
import os
import warnings
import time
import random

# ============================
# BASIC CONFIG
# ============================

# 👉 Put your real Zendesk AI key here
ZENDESK_AI_KEY = "R9TzTDs4w8NCzKw5U5AzSKDZEVC"

# If your gateway URL or model name differs, change them here
ZENDESK_AI_URL = "https://ai-gateway.zende.sk/v1/chat/completions"
ZENDESK_MODEL = "gpt-4"  # or the model your gateway exposes, e.g. "gpt-4.1-mini"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    )
}

# ES news sources (updated list)
SOURCES = {
    "CXToday": "https://www.cxtoday.com/latest-news/",
    "JoshBersin": "https://joshbersin.com/category/hr-technology/",
    "CIO": "https://www.cio.com/news/",
    "HRExecutive": "https://hrexecutive.com/category/hr-technology/",
    "TechTargetNews": "https://www.techtarget.com/news/",
    "ITSMTools": "https://itsm.tools/itsm/",
}

# Keep dated articles from the last N hours
# (undated ones are still kept and then filtered by ES relevance)
MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "48"))  # default 48

# Limit number of articles per source per run (safety for very long pages)
MAX_ARTICLES_PER_SOURCE = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "25"))

# Optional: skip undated articles to speed up runs
SKIP_UNDATED = os.getenv("SKIP_UNDATED", "false").lower() in ("1", "true", "yes")

# Be nice to news sites and your gateway
REQUEST_TIMEOUT = 15
LLM_TIMEOUT = 40
LLM_SLEEP_MIN = 0.8
LLM_SLEEP_MAX = 1.8

# Silence XML warning noise from BeautifulSoup
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


# ============================
# ES VENDOR & KEYWORD FILTERS
# ============================

ES_VENDORS = [
    # Core ITSM / ESM
    "servicenow", "atlassian", "bmc", "bmc helix", "aisera",
    "moveworks", "freshworks", "freshservice", "manageengine",
    "sysaid", "halo", "haloitsm", "symphonyai", "zendesk",

    # HRSM Vendors
    "ukg", "wtw", "ivanti", "infor", "neocase", "leena ai",
    "dovetail", "salesforce",

    # ITOM / Observability
    "cisco", "dynatrace", "broadcom",

    # Enterprise ES-adjacent platforms
    "microsoft", "sap", "oracle",
]

ES_KEYWORDS = [
    "itsm", "itom", "esm", "employee service", "employee experience",
    "employee workflow", "employee portal", "ticketing",
    "hr service", "hrsm", "hr case management", "hr technology",
    "service desk", "it service management", "it operations management",
    "workflow automation", "delivery automation", "process automation",
    "it asset management", "itam", "service catalog",
]


# ============================
# DATE PARSING HELPERS
# ============================

def extract_published_date_from_jsonld(soup):
    """Look for <script type='application/ld+json'> and parse datePublished/dateModified."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            text = script.string
            if not text:
                continue
            data = json.loads(text)
        except Exception:
            continue

        candidates = []
        if isinstance(data, dict):
            candidates = [data]
        elif isinstance(data, list):
            candidates = data

        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            for key in ["datePublished", "dateModified", "uploadDate"]:
                if key in obj and obj[key]:
                    try:
                        return dateparser.parse(obj[key])
                    except Exception:
                        continue
    return None


def extract_published_date(soup):
    """
    Try to extract a publication date from the article HTML.
    Returns datetime (maybe tz-aware) or None.
    """

    # 0) JSON-LD first (often the cleanest)
    dt = extract_published_date_from_jsonld(soup)
    if dt:
        return dt

    # 1) <time> element
    time_tag = soup.find("time")
    if time_tag:
        if time_tag.has_attr("datetime"):
            text = time_tag["datetime"]
        else:
            text = time_tag.get_text(strip=True)
        try:
            return dateparser.parse(text)
        except Exception:
            pass

    # 2) Meta tags
    meta_candidates = [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"property": "og:updated_time"}),
        ("meta", {"name": "pubdate"}),
        ("meta", {"name": "publish-date"}),
        ("meta", {"name": "date"}),
        ("meta", {"itemprop": "datePublished"}),
    ]

    for tag_name, attrs in meta_candidates:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            text = tag["content"]
            try:
                return dateparser.parse(text)
            except Exception:
                continue

    # 3) Fallback: span/div with "date" in the class name
    def looks_like_date(tag):
        if tag.name not in ["span", "div"]:
            return False
        classes = tag.get("class") or []
        return any("date" in c.lower() for c in classes)

    date_like = soup.find(looks_like_date)
    if date_like:
        text = date_like.get_text(strip=True)
        try:
            return dateparser.parse(text)
        except Exception:
            pass

    return None


# ============================
# SCRAPING FUNCTIONS
# ============================

def same_domain(url, base_url):
    """Keep only links from the same domain to reduce noise."""
    try:
        return urlparse(url).netloc == urlparse(base_url).netloc
    except Exception:
        return False


def extract_articles(source_name, url):
    """
    Extract article URLs + content from a source homepage/category.
    - Filters out obvious navigation / home links based on path depth.
    - Does NOT require dates (but will try to parse them).
    """
    print(f"Scraping {source_name} -> {url}")

    try:
        html = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT).text
    except Exception as e:
        print(f"Error scraping {source_name}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    urls = []

    # Collect candidate links
    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Basic filtering
        if not href.startswith("http"):
            continue
        if any(bad in href for bad in ["linkedin", "twitter", "facebook", "youtube"]):
            continue
        if not same_domain(href, url):
            continue

        path = urlparse(href).path
        segments = [s for s in path.split("/") if s]
        # Require at least two segments to avoid home and broad category pages
        if len(segments) < 2:
            continue
        
        # Filter out category pages explicitly
        if '/category/' in href.lower() or '/tag/' in href.lower():
            continue
        
        # Filter out URLs that end with just category name (e.g., /hr-technology/)
        if len(segments) == 1 and any(cat in href.lower() for cat in ['category', 'tag', 'author', 'archive']):
            continue

        if href not in urls:
            urls.append(href)

    articles = []
    processed_count = 0

    for article_url in urls:
        if processed_count >= MAX_ARTICLES_PER_SOURCE:
            break

        try:
            art_html = requests.get(
                article_url, headers=HEADERS, timeout=REQUEST_TIMEOUT
            ).text
            art_soup = BeautifulSoup(art_html, "html.parser")

            title_tag = art_soup.find("h1") or art_soup.find("h2")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            
            # Skip if title is just a category name (too generic)
            generic_titles = ['hr technology', 'hr tech', 'itsm', 'employee service', 
                            'category', 'tags', 'archives', 'authors']
            if title.lower() in generic_titles or len(title) < 20:
                continue
            
            paragraphs = art_soup.find_all("p")
            if not paragraphs:
                continue

            snippet = " ".join(
                [p.get_text(strip=True) for p in paragraphs[:4]]
            )[:700]

            published_dt = extract_published_date(art_soup)

            articles.append({
                "source": source_name,
                "title": title,
                "url": article_url,
                "snippet": snippet,
                "published_dt": published_dt,  # may be None
            })
            processed_count += 1

        except Exception:
            continue

    return articles


# ============================
# ES RELEVANCE FILTER
# ============================

def detect_es_vendors_and_keywords(article):
    """
    Return (set_of_vendor_hits, set_of_keyword_hits) based on title+snippet.
    """
    text = f"{article['title']} {article['snippet']}".lower()

    vendor_hits = {v for v in ES_VENDORS if v in text}
    keyword_hits = {k for k in ES_KEYWORDS if k in text}

    return vendor_hits, keyword_hits


def is_es_relevant(article):
    """
    An article is ES-related if:
    - it mentions at least one ES vendor, OR
    - it includes at least one ES keyword.
    """
    vendors, keywords = detect_es_vendors_and_keywords(article)
    return bool(vendors or keywords)


# ============================
# LLM ANALYSIS
# ============================

def parse_json_from_text(text):
    """Best-effort extraction of a JSON object from model output."""
    text = text.strip()
    # First try direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to cut from first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


def analyze_with_llm(article):
    """
    Call Zendesk AI Gateway to get:
    - 3-sentence summary
    - engagement flag: HIGH / MEDIUM / LOW
    - 12-word Slack hook
    """

    prompt = f"""
You are a B2B market intelligence analyst at Zendesk.

Analyze this Employee Service (ES) related article. ES includes ITSM, ITOM,
ESM, HR service management, employee experience, and workflow automation.

ARTICLE TITLE: {article['title']}
ARTICLE URL: {article['url']}
SNIPPET: {article['snippet']}

Follow these steps:

1) Write a concise 2–3 sentence summary focused on ES implications:
   - What is new or changing?
   - Why does it matter for ITSM / ITOM / HRSM / ESM / EX buyers?

2) Assign an engagement level (HIGH, MEDIUM, LOW) with these rules:

   HIGH (always) when:
     - Gartner / Forrester / IDC / ISG / Everest / Omdia / Valoir / Deloitte,
       KPMG, etc. publish MQs, Waves, MarketScapes, Buyers Guides for ITSM,
       ESM, HRSM, EX, or AI for ITSM.
     - Major ES wins or deployments (e.g., global 10k+ employee orgs,
       >$10M ACV, or multi-region rollouts).
     - Strategic M&A or investments impacting core ES vendors
       (ServiceNow, Atlassian, BMC, Moveworks, Aisera, Freshworks, etc.).
     - Significant product shifts in agentic AI, workflow automation,
       or copilots that change ITSM/ESM/HRSM roadmaps.
     - Deep ecosystem partnerships (e.g., ServiceNow + hyperscalers / telcos).

   MEDIUM when:
     - Smaller acquisitions or partnerships in ES / EX space.
     - Feature updates to ITSM / HRSM / ESM products that add interesting,
       but incremental, automation / AI / analytics.
     - Vendor earnings with clear ES/ITSM impact (ARR, adoption, seat growth).

   LOW when:
     - Pure marketing fluff or minor updates.
     - Limited strategic angle for ES, ITSM, HRSM, or EX buyers.

3) Write a SHORT Slack hook (MAX 12 words) that is punchy and specific.
   It should make a CC / ES GTM team want to click.

4) Determine if this article is specifically about AI in Customer Service / Contact Center:
   - Mentions AI/ML/LLM features in CS platforms (Zendesk, Salesforce, ServiceNow, HubSpot, Freshworks, Intercom, Gorgias, etc.)
   - Covers AI agents, chatbots, copilots, or autonomous resolution in CS/CCaaS
   - Discusses AI partnerships, acquisitions, or features in CCaaS/CS platforms
   - Focuses on AI infrastructure (OpenAI, AWS, Azure, Google Cloud, etc.) specifically for CS use cases
   - Mentions vendors from the AI CS ecosystem: Genesys, NICE, Five9, RingCentral, 8x8, Twilio, Vonage, Sierra, Ada, Crescendo, Forethought, PolyAI, ASAPP, Kore.ai, Yellow.ai, Cognigy, Capacity, Replicant, Parloa, Cresta, Uniphore, Observe.AI, Gong, Assembled, Calabrio, etc.
   
   Set "is_ai_cs_relevant": true if the article is primarily about AI in CS/CCaaS context.
   Set "is_ai_cs_relevant": false if AI is mentioned but not CS-focused, or if it's general AI news without CS context.

Return ONLY a valid JSON object with EXACTLY these keys:
  "summary"   -> string
  "engagement" -> "HIGH" or "MEDIUM" or "LOW"
  "hook"      -> string
  "is_ai_cs_relevant" -> true or false
"""

    body = {
        "model": ZENDESK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 350,
        "temperature": 0.2,
    }

    try:
        response = requests.post(
            ZENDESK_AI_URL,
            headers={
                "Authorization": f"Bearer {ZENDESK_AI_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps(body),
            timeout=LLM_TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        print("LLM network error on:", article["url"], "| Error:", e)
        return {"summary": "", "engagement": "LOW", "hook": "", "is_ai_cs_relevant": False}

    if response.status_code == 401:
        print("⚠️ LLM 401 Unauthorized – check ZENDESK_AI_KEY and model name.")
        return {"summary": "", "engagement": "LOW", "hook": "", "is_ai_cs_relevant": False}

    if response.status_code != 200:
        print("LLM HTTP error on:", article["url"])
        print("Status:", response.status_code, "| Body:", response.text[:200])
        return {"summary": "", "engagement": "LOW", "hook": "", "is_ai_cs_relevant": False}

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            # Some gateways return "content" as a list of parts
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        else:
            text = content

        parsed = parse_json_from_text(text)
        if not parsed:
            raise ValueError("Could not parse JSON from model output.")

        # Normalize engagement just in case
        engagement = str(parsed.get("engagement", "LOW")).upper()
        if engagement not in {"HIGH", "MEDIUM", "LOW"}:
            engagement = "LOW"

        # Ensure is_ai_cs_relevant is present, default to False if missing
        is_ai_cs_relevant = parsed.get("is_ai_cs_relevant", False)
        # Handle string "true"/"false" or boolean
        if isinstance(is_ai_cs_relevant, str):
            is_ai_cs_relevant = is_ai_cs_relevant.lower() in ("true", "1", "yes")
        elif not isinstance(is_ai_cs_relevant, bool):
            is_ai_cs_relevant = False

        return {
            "summary": parsed.get("summary", "").strip(),
            "engagement": engagement,
            "hook": parsed.get("hook", "").strip(),
            "is_ai_cs_relevant": is_ai_cs_relevant,
        }

    except Exception as e:
        print("LLM parse error on:", article["url"], "| Error:", e)
        print("Raw response snippet:", response.text[:200])
        return {"summary": "", "engagement": "LOW", "hook": "", "is_ai_cs_relevant": False}


# ============================
# MAIN PIPELINE
# ============================

def run_pipeline():
    all_articles = []

    # 1) Scrape each source
    for name, url in SOURCES.items():
        articles = extract_articles(name, url)
        all_articles.extend(articles)

    if not all_articles:
        print("No articles found at all.")
        return []

    now = datetime.datetime.now(datetime.timezone.utc)

    dated_recent = []
    nodate_articles = []

    for art in all_articles:
        pub_dt = art["published_dt"]

        if pub_dt is None:
            if not SKIP_UNDATED:
                nodate_articles.append(art)
            continue

        # Normalise to UTC and compute age
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=datetime.timezone.utc)
        else:
            pub_dt = pub_dt.astimezone(datetime.timezone.utc)

        age_hours = (now - pub_dt).total_seconds() / 3600

        if 0 <= age_hours <= MAX_AGE_HOURS:
            art["published_dt"] = pub_dt
            dated_recent.append(art)

    combined = dated_recent + nodate_articles

    if not combined:
        print("No recent (or undated) articles after time filtering.")
        return []

    # 2) Deduplicate by URL
    df = pd.DataFrame(combined).drop_duplicates(subset="url")

    # 3) Filter for ES relevance
    es_rows = []
    for _, row in df.iterrows():
        art = {
            "source": row["source"],
            "title": row["title"],
            "url": row["url"],
            "snippet": row["snippet"],
            "published_dt": row["published_dt"],
        }
        if is_es_relevant(art):
            es_rows.append(art)

    if not es_rows:
        print("No ES-relevant articles found.")
        return []

    print(f"Found {len(es_rows)} ES-relevant candidate articles. Sending to LLM...")

    processed_rows = []

    for art in es_rows:
        vendors_hit, keywords_hit = detect_es_vendors_and_keywords(art)

        # Call LLM
        ai = analyze_with_llm(art)

        pub_dt = art["published_dt"]
        published_str = (
            pub_dt.isoformat() if isinstance(pub_dt, datetime.datetime) else ""
        )

        processed_rows.append({
            "date_scraped": datetime.date.today().isoformat(),
            "source": art["source"],
            "title": art["title"],
            "url": art["url"],
            "published": published_str,
            "vendors_hit": ", ".join(sorted(vendors_hit)),
            "keywords_hit": ", ".join(sorted(keywords_hit)),
            "summary": ai.get("summary", ""),
            "engagement": ai.get("engagement", "LOW"),
            "hook": ai.get("hook", ""),
            "is_ai_cs_relevant": ai.get("is_ai_cs_relevant", False),
        })

        # Gentle pacing for the gateway
        time.sleep(random.uniform(LLM_SLEEP_MIN, LLM_SLEEP_MAX))

    out_df = pd.DataFrame(processed_rows)
    filename = f"es_news_{datetime.date.today().isoformat()}.csv"
    out_df.to_csv(filename, index=False, encoding="utf-8")
    print(f"Saved {len(processed_rows)} rows to {filename}")

    return processed_rows


# ============================
# RUN SCRIPT
# ============================

if __name__ == "__main__":
    print("Running ES News Pipeline (multi-source, ES-filtered)...")
    rows = run_pipeline()
    print("Done.")

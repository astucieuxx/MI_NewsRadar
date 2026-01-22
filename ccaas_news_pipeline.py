import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import json
import datetime
import pandas as pd
from dateutil import parser as dateparser
from urllib.parse import urlparse
import warnings
import time

# Silence XML/HTML parsing warning noise
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ============================
# CONFIGURATION
# ============================

ZENDESK_AI_KEY = "R9TzTDs4w8NCzKw5U5AzSKDZEVC"  # <-- PUT YOUR REAL KEY HERE
ZENDESK_AI_URL = "https://ai-gateway.zende.sk/v1/chat/completions"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Key CCaaS / CX news sources
SOURCES = {
    "CXToday": "https://www.cxtoday.com/contact-center/",
    "TechTarget": "https://www.techtarget.com/searchcustomerexperience/",
    "NoJitter": "https://www.nojitter.com/contact-centers/ccaas",
}

# Keep dated articles from the last N hours
# (undated articles are always kept)
MAX_AGE_HOURS = 48  # <-- changed to 48 hours for today only

# Limit how many articles we scrape per source (avoid going crazy)
MAX_ARTICLES_PER_SOURCE = 20


# ============================
# DATE PARSING HELPERS
# ============================

def extract_published_date_from_jsonld(soup):
    """
    Look for <script type="application/ld+json"> and parse datePublished/dateModified.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            text = script.string
            if not text:
                continue
            data = json.loads(text)
        except Exception:
            continue

        # JSON-LD can be dict or list[dict]
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

    # 0) JSON-LD first (often the best)
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

    # If all fails, we return None (and will still keep the article)
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
    Extract article URLs + content from a source homepage.
    - filters out home/category pages based on path depth
    - DOES NOT require dates anymore (we still try to parse them)
    """
    print(f"Scraping {source_name} -> {url}")

    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
    except Exception as e:
        print(f"Error scraping {source_name}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    urls = []

    # Collect candidate links
    for a in soup.find_all("a", href=True):
        href = a["href"]

        # 1) Basic filtering
        if not href.startswith("http"):
            continue
        if any(bad in href for bad in ["linkedin", "twitter", "facebook", "youtube"]):
            continue
        if not same_domain(href, url):
            continue

        # 2) Filter out home/category pages:
        #    keep URLs where the path has at least 2 segments,
        #    e.g. /contact-center/some-article-slug
        path = urlparse(href).path
        segments = [s for s in path.split("/") if s]
        if len(segments) < 2:
            continue
        
        # 3) Filter out common category/page types that aren't articles
        category_keywords = ['guides', 'definitions', 'opinions', 'podcasts', 
                           'quizzes', 'techaccelerators', 'tutorials', 'videos',
                           'news', 'blog', 'category', 'tag', 'author', 'archive']
        if any(keyword in href.lower() for keyword in category_keywords):
            continue
        
        # 4) Filter out contributor/author pages
        if '/contributor/' in href.lower():
            continue
        
        # 5) Filter out single-segment category pages (e.g., /HR, /CreatorWorkflows)
        # These are usually category landing pages, not articles
        if len(segments) == 1:
            continue
        
        # 6) Filter out URLs that look like category pages (short segments, no article-like structure)
        # Articles usually have longer, more descriptive slugs
        last_segment = segments[-1] if segments else ""
        if len(last_segment) < 10 or last_segment.isupper():  # Short or all caps = likely category
            continue

        if href not in urls:
            urls.append(href)

    articles = []
    processed_count = 0

    for article_url in urls:
        if processed_count >= MAX_ARTICLES_PER_SOURCE:
            break

        try:
            art_html = requests.get(article_url, headers=HEADERS, timeout=10).text
            art_soup = BeautifulSoup(art_html, "html.parser")

            title_tag = art_soup.find("h1") or art_soup.find("h2")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            
            # Skip if title looks like a category/author page
            if len(title) < 20 or title.lower() in ['home', 'categories', 'authors', 'about']:
                continue
            
            paragraphs = art_soup.find_all("p")
            if not paragraphs:
                continue

            snippet = " ".join([p.get_text(strip=True) for p in paragraphs[:3]])[:500]
            
            # Skip if snippet is too short (likely not a real article)
            if len(snippet) < 100:
                continue

            published_dt = extract_published_date(art_soup)

            articles.append({
                "source": source_name,
                "title": title,
                "url": article_url,
                "snippet": snippet,
                "published_dt": published_dt,  # may be None
            })
            processed_count += 1
            print(f"   ✅ Found article: {title[:60]}")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"   ⚠️ Skipping (403 Forbidden): {article_url}")
            continue
        except Exception as e:
            print(f"   ⚠️ Error scraping {article_url}: {type(e).__name__}")
            continue

    return articles


# ============================
# LLM ANALYSIS
# ============================

def analyze_with_llm(article):
    prompt = f"""
You are a contact center / CCaaS market analyst.

Analyze the following article for relevance to the Contact Center / CCaaS / CX space:

TITLE: {article['title']}
URL: {article['url']}
SNIPPET: {article['snippet']}

1. Write a 3-sentence summary.

2. Assign an engagement level (HIGH, MEDIUM, LOW) using these rules:

HIGH (always):
  * Any CCaaS related analyst report or recognition (Gartner MQ, Market Guide, IDC MarketScape,
    Forrester Wave, ISG Guide, Everest Peak Matrix, Omdia, Frost & Sullivan,
    Valoir, Deloitte, KPMG, etc.)
  * Major CCaaS wins (>5k seats or >$10M ACV).
  * CCaaS related AI agentic orchestration, agent-to-agent automation, voice AI breakthroughs.
  * Hyperscaler shifts (AWS, Azure, Google, Oracle).
  * M&A > $500M.
  * CCaaS related Strategic ecosystem partnerships.
  * Major CCaaS market size / forecast reports that reset expectations.

MEDIUM:
  * CCaaS related M&A < $500M
  * CCaaS related AI features without a clear strategic shift
  * CCaaS related Telco or CRM integrations
  * Earnings / ARR updates with AI or CCaaS relevance

LOW:
  * CCaaS Small vendor updates
  * No clear competitive or strategic angle
  * Generic marketing content or product fluff

3. Write a 12-word Slack hook that is punchy, urgent, and interesting.

4. Determine if this article is specifically about AI in Customer Service / Contact Center:
   - Mentions AI/ML/LLM features in CS platforms (Zendesk, Salesforce, ServiceNow, HubSpot, Freshworks, Intercom, Gorgias, etc.)
   - Covers AI agents, chatbots, copilots, or autonomous resolution in CS/CCaaS
   - Discusses AI partnerships, acquisitions, or features in CCaaS/CS platforms
   - Focuses on AI infrastructure (OpenAI, AWS, Azure, Google Cloud, etc.) specifically for CS use cases
   - Mentions vendors from the AI CS ecosystem: Genesys, NICE, Five9, RingCentral, 8x8, Twilio, Vonage, Sierra, Ada, Crescendo, Forethought, PolyAI, ASAPP, Kore.ai, Yellow.ai, Cognigy, Capacity, Replicant, Parloa, Cresta, Uniphore, Observe.AI, Gong, Assembled, Calabrio, etc.
   
   Set "is_ai_cs_relevant": true if the article is primarily about AI in CS/CCaaS context.
   Set "is_ai_cs_relevant": false if AI is mentioned but not CS-focused, or if it's general AI news without CS context.

Respond ONLY with valid JSON, no surrounding text, in this exact shape:

{{
  "summary": "...",
  "engagement": "HIGH|MEDIUM|LOW",
  "hook": "...",
  "is_ai_cs_relevant": true|false
}}
"""

    body = {
        "model": "gpt-4",  # or whatever model your Gateway is wired to
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 350,
        "temperature": 0.3,
        # IMPORTANT: no response_format here, since your model doesn't support it
    }

    try:
        print(f"   🔄 Calling LLM API: {ZENDESK_AI_URL}")
        print(f"   🔑 Using API key: {ZENDESK_AI_KEY[:10]}...{ZENDESK_AI_KEY[-4:] if len(ZENDESK_AI_KEY) > 14 else '***'}")
        
        response = requests.post(
            ZENDESK_AI_URL,
            headers={
                "Authorization": f"Bearer {ZENDESK_AI_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps(body),
            timeout=45,
        )
        
        print(f"   📡 Response status: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ LLM network error on: {article['url']}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        return {"summary": "", "engagement": "LOW", "hook": "", "is_ai_cs_relevant": False}

    if response.status_code == 401:
        print("⚠️ LLM 401 Unauthorized – check ZENDESK_AI_KEY and model name.")
        print(f"   Response body: {response.text[:500]}")
        return {"summary": "", "engagement": "LOW", "hook": "", "is_ai_cs_relevant": False}

    if response.status_code != 200:
        print(f"❌ LLM API error on: {article['url']}")
        print(f"   Status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        print(f"   Response body: {response.text[:500]}")
        
        if response.status_code == 403:
            print("   ⚠️ 403 Forbidden - Possible causes:")
            print("      - API key expired or invalid")
            print("      - IP address blocked (Streamlit Cloud IP may be restricted)")
            print("      - Rate limit exceeded")
            print("      - Gateway access restrictions")
        elif response.status_code == 429:
            print("   ⚠️ 429 Rate Limited - Too many requests, waiting...")
            time.sleep(5)  # Wait before retrying
        elif response.status_code == 401:
            print("   ⚠️ 401 Unauthorized - Check ZENDESK_AI_KEY")
        
        return {"summary": "", "engagement": "LOW", "hook": ""}

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Some gateways can return structured content; normalize to plain string
        if isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        else:
            text = content

        # Try direct JSON parse
        try:
            result = json.loads(text)
            # Validate that we got the expected fields
            if "engagement" in result and "summary" in result:
                # Ensure is_ai_cs_relevant is present, default to False if missing
                if "is_ai_cs_relevant" not in result:
                    result["is_ai_cs_relevant"] = False
                else:
                    # Handle string "true"/"false" or boolean
                    is_ai_cs_relevant = result.get("is_ai_cs_relevant", False)
                    if isinstance(is_ai_cs_relevant, str):
                        result["is_ai_cs_relevant"] = is_ai_cs_relevant.lower() in ("true", "1", "yes")
                    elif not isinstance(is_ai_cs_relevant, bool):
                        result["is_ai_cs_relevant"] = False
                print(f"   ✅ LLM returned: engagement={result.get('engagement')}, summary_length={len(result.get('summary', ''))}, is_ai_cs_relevant={result.get('is_ai_cs_relevant', False)}")
                return result
            else:
                print(f"   ⚠️ LLM returned incomplete JSON: {list(result.keys())}")
        except json.JSONDecodeError:
            # Sometimes the model may add extra text; try to extract the JSON substring
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    result = json.loads(text[start: end + 1])
                    if "engagement" in result and "summary" in result:
                        # Ensure is_ai_cs_relevant is present, default to False if missing
                        if "is_ai_cs_relevant" not in result:
                            result["is_ai_cs_relevant"] = False
                        else:
                            # Handle string "true"/"false" or boolean
                            is_ai_cs_relevant = result.get("is_ai_cs_relevant", False)
                            if isinstance(is_ai_cs_relevant, str):
                                result["is_ai_cs_relevant"] = is_ai_cs_relevant.lower() in ("true", "1", "yes")
                            elif not isinstance(is_ai_cs_relevant, bool):
                                result["is_ai_cs_relevant"] = False
                        print(f"   ✅ LLM returned (extracted): engagement={result.get('engagement')}, summary_length={len(result.get('summary', ''))}, is_ai_cs_relevant={result.get('is_ai_cs_relevant', False)}")
                        return result
                    else:
                        print(f"   ⚠️ LLM returned incomplete JSON (extracted): {list(result.keys())}")
                except Exception as e:
                    print(f"   ❌ Failed to parse extracted JSON: {e}")

        # If parsing totally fails, fall back to safe defaults
        print(f"❌ LLM parse error on: {article['url']}")
        print(f"   Raw content snippet: {text[:500]}")
        print("   ⚠️ LLM did not return valid JSON. Using default LOW engagement.")
        return {"summary": "", "engagement": "LOW", "hook": "", "is_ai_cs_relevant": False}

    except Exception as e:
        print("LLM unexpected error on:", article["url"], "| Error:", e)
        return {"summary": "", "engagement": "LOW", "hook": "", "is_ai_cs_relevant": False}


# ============================
# MAIN PIPELINE
# ============================

def run_pipeline():
    all_articles = []

    # Scrape each source
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
            # Keep undated articles (e.g., some NoJitter stories)
            nodate_articles.append(art)
            continue

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
        print("No recent (or undated) articles after filtering.")
        return []

    # Deduplicate by URL
    df = pd.DataFrame(combined).drop_duplicates(subset="url")
    
    print(f"Found {len(df)} unique articles after deduplication. Sending to LLM...")

    processed_rows = []

    for idx, (_, row) in enumerate(df.iterrows(), 1):
        print(f"\n[{idx}/{len(df)}] Processing: {row['title'][:60]}...")
        print(f"   URL: {row['url']}")
        ai = analyze_with_llm(row)
        
        # Log detailed results
        engagement = ai.get("engagement", "LOW")
        has_summary = bool(ai.get("summary", "").strip())
        has_hook = bool(ai.get("hook", "").strip())
        
        if not has_summary and not has_hook:
            print(f"   ⚠️ LLM returned EMPTY values - likely failed!")
        else:
            print(f"   ✅ LLM analysis: engagement={engagement}, summary={has_summary}, hook={has_hook}")

        pub_dt = row["published_dt"]
        published_str = (
            pub_dt.isoformat() if isinstance(pub_dt, datetime.datetime) else ""
        )

        processed_rows.append({
            "date_scraped": datetime.date.today().isoformat(),
            "source": row["source"],
            "title": row["title"],
            "url": row["url"],
            "published": published_str,
            "summary": ai.get("summary", ""),
            "engagement": ai.get("engagement", "LOW"),
            "hook": ai.get("hook", ""),
            "is_ai_cs_relevant": ai.get("is_ai_cs_relevant", False),
        })

    out_df = pd.DataFrame(processed_rows)
    filename = f"ccaas_news_{datetime.date.today().isoformat()}.csv"
    out_df.to_csv(filename, index=False, encoding="utf-8")
    print(f"Saved {len(processed_rows)} rows to {filename}")

    return processed_rows


# ============================
# RUN SCRIPT
# ============================

if __name__ == "__main__":
    print("Running CCaaS News Pipeline (multi-source, last N hours + undated)...")
    rows = run_pipeline()
    print("Done.")

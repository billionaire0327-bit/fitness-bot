import os
import requests
import feedparser
import re

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def clean_text(html_text):
    if not html_text:
        return ""
    text = re.sub(r'<.*?>', '', html_text)
    text = text.replace('\n', ' ').strip()
    return text

def safe_translate(text):
    if not text:
        return "제목 정보 없음"
    
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "ko",
            "dt": "t",
            "q": text[:400]
        }
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            result = res.json()
            translated = "".join([item[0] for item in result[0] if item[0]])
            if "Error" not in translated:
                return translated
    except Exception:
        pass
        
    return text[:100]

def fetch_hypertrophy_data():
    # 차단 위험이 낮고 안정한 글로벌 근력/운동 연구 RSS 피드
    rss_urls = [
        "https://journals.plos.org/plosone/feed/atom?term=resistance+training",
        "https://www.biomedcentral.com/journals/journalofexerciserehabilitation/rss",
        "https://www.sciencedaily.com/rss/top/sports.xml"
    ]
    
    entries = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for url in rss_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                if feed.entries:
                    entries.extend(feed.entries)
                    if len(entries) >= 5:
                        break
        except Exception as e:
            print(f"피드 에러 ({url}): {e}")

    return entries[:5]

def build_summary_html(articles, owner, repo):
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>오늘의 헬스 & 근성장 과학 요약</title>
    <style>
        body {{ font-family: 'Apple SD Gothic Neo', sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; background-color: #f8f9fa; color: #333; }}
        h1 {{ color: #0d6efd; border-bottom: 2px solid #0d6efd; padding-bottom: 10px; }}
        .card {{ background: #fff; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .card h2 {{ color: #212529; font-size: 1.25rem; margin-top: 0; }}
        .summary {{ background: #e7f1ff; border-left: 4px solid #0d6efd; padding: 12px; margin: 15px 0; font-weight: 500; }}
        .orig-link {{ color: #6c757d; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <h1>🏋️ 오늘의 헬스 & 근성장 과학 요약 보고서</h1>
"""
    for i, item in enumerate(articles, 1):
        html_content += f"""
    <div class="card" id="article-{i}">
        <h2>주제 {i}. {item['title']}</h2>
        <div class="summary">
            💡 <b>핵심 요약:</b><br>{item['summary']}
        </div>
        <p><b>원문 제목:</b> {item['orig_title']}</p>
        <a class="orig-link" href="{item['link']}" target="_blank">🔗 원문 연구 자료 보기</a>
    </div>
"""
    html_content += "</body></html>"
    
    with open("summary.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def main():
    entries = fetch_hypertrophy_data()
    if not entries:
        send_telegram_message("⚠️ 수집할 수 있는 최신 연구 데이터가 없습니다. 잠시 후 다시 시도해 주세요.")
        return

    articles = []
    for entry in entries:
        title = entry.get('title', '')
        summary_raw = entry.get('summary', entry.get('description', ''))
        cleaned = clean_text(summary_raw)
        
        ko_title = safe_translate(title)
        ko_summary = safe_translate(cleaned) if cleaned else "상세 요약 본문이 제공되지 않는 논문입니다."
        
        articles.append({
            'title': ko_title,
            'orig_title': title,
            'summary': ko_summary,
            'link': entry.get('link', '')
        })

    if GITHUB_REPOSITORY and '/' in GITHUB_REPOSITORY:
        owner, repo = GITHUB_REPOSITORY.split('/')
    else:
        owner, repo = "username", "fitness-bot"

    build_summary_html(articles, owner, repo)

    pages_base_url = f"https://{owner}.github.io/{repo}/summary.html"
    
    msg = ["🏋️ **[오늘의 헬스 & 근성장 핵심 주제 3~5선]**\n"]
    msg.append("제목을 클릭하시면 **한글 요약 페이지**로 이동합니다!\n")

    for i, item in enumerate(articles, 1):
        page_link = f"{pages_base_url}#article-{i}"
        msg.append(f"{i}. [{item['title']}]({page_link})")

    send_telegram_message("\n".join(msg))

if __name__ == "__main__":
    main()

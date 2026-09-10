import os
import requests
import feedparser
import re
from deep_translator import GoogleTranslator

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY") # 예: username/fitness-bot

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
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
        return ""
    try:
        truncated = text[:500]
        return GoogleTranslator(source='auto', target='ko').translate(truncated)
    except Exception:
        return text[:200]

def fetch_hypertrophy_data():
    # 헬스, 근성장, 근력 증진에 특화된 해외 전문 RSS 피드
    rss_urls = [
        "https://www.sciencedaily.com/rss/fitness.xml",
        "https://www.strongerbyscience.com/feed/"
    ]
    
    entries = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for url in rss_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(res.content)
            if feed.entries:
                entries.extend(feed.entries)
        except Exception as e:
            print(f"피드 로딩 실패: {e}")

    # 근육, 근력, 훈련 관련 키워드가 포함된 주제 위주 필터링
    keywords = ['muscle', 'strength', 'hypertrophy', 'training', 'protein', 'exercise', 'weight']
    filtered = []
    for entry in entries:
        title_lower = entry.get('title', '').lower()
        if any(kw in title_lower for kw in keywords):
            filtered.append(entry)
            
    # 필터링 결과가 적으면 일반 피드 목록 사용
    target_entries = filtered if len(filtered) >= 3 else entries
    return target_entries[:5] # 3~5개 주제 선정

def build_summary_html(articles, repo_owner, repo_name):
    # GitHub Pages로 띄울 예쁜 웹 요약 보고서 HTML 생성
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>오늘의 헬스 & 근성장 과학 요약</title>
    <style>
        body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; background-color: #f4f7f6; color: #333; }}
        h1 {{ color: #1a365d; border-bottom: 3px solid #2b6cb0; padding-bottom: 10px; }}
        .card {{ background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .card h2 {{ color: #2b6cb0; font-size: 1.3rem; margin-top: 0; }}
        .tag {{ display: inline-block; background: #e2e8f0; color: #4a5568; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; margin-bottom: 10px; }}
        .summary {{ background: #ebf8ff; border-left: 4px solid #3182ce; padding: 12px; margin: 15px 0; font-weight: 500; }}
        .orig-link {{ display: inline-block; margin-top: 10px; color: #718096; font-size: 0.85rem; text-decoration: none; }}
        .orig-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>🏋️ 오늘의 헬스 & 근성장 과학 요약 보고서</h1>
    <p>해외 최신 논문 및 스포츠 과학 아티클을 인공지능이 쉽게 요약한 내용입니다.</p>
"""
    for i, item in enumerate(articles, 1):
        html_content += f"""
    <div class="card" id="article-{i}">
        <span class="tag">주제 {i}</span>
        <h2>{item['title']}</h2>
        <div class="summary">
            💡 <b>핵심 쉬운 요약:</b><br>{item['summary']}
        </div>
        <p><b>원문 제목:</b> {item['orig_title']}</p>
        <a class="orig-link" href="{item['link']}" target="_blank">🔗 출처 연구 논문/원문 보러가기</a>
    </div>
"""
    html_content += """
</body>
</html>
"""
    with open("summary.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def main():
    entries = fetch_hypertrophy_data()
    if not entries:
        send_telegram_message("⚠️ 오늘은 수집된 헬스 소식이 없습니다.")
        return

    articles = []
    for entry in entries:
        title = entry.get('title', '')
        summary_raw = entry.get('summary', entry.get('description', ''))
        cleaned = clean_text(summary_raw)
        
        ko_title = safe_translate(title)
        ko_summary = safe_translate(cleaned) if cleaned else "상세 요약 본문이 제공되지 않는 아티클입니다."
        
        articles.append({
            'title': ko_title,
            'orig_title': title,
            'summary': ko_summary,
            'link': entry.get('link', '')
        })

    # GitHub 저장소 정보 파싱 (예: billionaire0327-bit/fitness-bot)
    if GITHUB_REPOSITORY and '/' in GITHUB_REPOSITORY:
        owner, repo = GITHUB_REPOSITORY.split('/')
    else:
        owner, repo = "username", "fitness-bot"

    # HTML 요약 페이지 파일 생성
    build_summary_html(articles, owner, repo)

    # 텔레그램 전송용 텍스트 작성
    pages_base_url = f"https://{owner}.github.io/{repo}/summary.html"
    
    msg = ["🏋️ **[오늘의 헬스 & 근성장 핵심 주제 3~5선]**\n"]
    msg.append("제목을 클릭하시면 **제가 한글로 직접 요약한 상세 보기 페이지**로 이동합니다!\n")

    for i, item in enumerate(articles, 1):
        # 텔레그램 제목 클릭 시 만든 요약 웹페이지의 해당 위치(#article-i)로 바로 이동
        page_link = f"{pages_base_url}#article-{i}"
        msg.append(f"{i}. [{item['title']}]({page_link})")

    send_telegram_message("\n".join(msg))

if __name__ == "__main__":
    main()

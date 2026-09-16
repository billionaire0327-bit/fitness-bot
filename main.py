import os
import requests
import feedparser
import re
import random
from deep_translator import GoogleTranslator

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
        translated = GoogleTranslator(source='auto', target='ko').translate(text[:400])
        return translated
    except Exception:
        return text[:100]

def make_youtube_style_title(ko_title):
    # 유튜버 영상 제목 느낌으로 흥미롭게 가공하는 패턴
    styles = [
        f"🚨 헬스인 필독! {ko_title}",
        f"🔥 근성장 정체기라면? {ko_title}",
        f"💡 논문으로 밝혀진 사실: {ko_title}",
        f"🏋️ 득근을 위한 필수 상식! {ko_title}",
        f"😱 트레이너들이 안 알려주는 {ko_title}"
    ]
    return random.choice(styles)

def fetch_gym_research_data():
    # 진짜 Gym/헬스/근성장 관련 검증된 출처들
    rss_urls = [
        "https://www.strongerbyscience.com/feed/",
        "https://bmcsportsscimedrehabil.biomedcentral.com/articles/rss",
        "https://journals.plos.org/plosone/feed/atom?term=resistance+exercise"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 헬스(Gym) 관련 엄격한 키워드 검사
    gym_keywords = ['muscle', 'strength', 'hypertrophy', 'resistance', 'protein', 'weight', 'squat', 'bench', 'lifting', 'exercise']
    
    gym_entries = []
    
    for url in rss_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries:
                    title_summary = (entry.get('title', '') + " " + entry.get('summary', '')).lower()
                    
                    # 일반 의학/건강 기사 차단 키워드
                    if any(bad in title_summary for bad in ['disease', 'cancer', 'surgery', 'patient', 'hospital', 'correction']):
                        continue
                        
                    # 헬스 키워드가 포함된 글만 필터링
                    if any(kw in title_summary for kw in gym_keywords):
                        gym_entries.append(entry)
                        if len(gym_entries) >= 5:
                            break
        except Exception as e:
            print(f"피드 로드 실패: {e}")
            
    return gym_entries[:5]

def build_summary_html(articles, owner, repo):
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏋️ 오늘의 헬스 & 근성장 과학 요약</title>
    <style>
        body {{ font-family: 'Apple SD Gothic Neo', sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; background-color: #121212; color: #e0e0e0; }}
        h1 {{ color: #ff4757; border-bottom: 2px solid #ff4757; padding-bottom: 10px; }}
        .card {{ background: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #333; }}
        .card h2 {{ color: #ffa502; font-size: 1.25rem; margin-top: 0; }}
        .summary {{ background: #2f3542; border-left: 4px solid #ff4757; padding: 12px; margin: 15px 0; font-weight: 500; color: #ffffff; }}
        .orig-link {{ color: #70a1ff; font-size: 0.9rem; text-decoration: none; }}
        .orig-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>🏋️ 오늘의 헬스 & 근성장 과학 보고서</h1>
"""
    for i, item in enumerate(articles, 1):
        html_content += f"""
    <div class="card" id="article-{i}">
        <h2>{item['yt_title']}</h2>
        <div class="summary">
            💡 <b>핵심 요약:</b><br>{item['summary']}
        </div>
        <p><b>원문 제목:</b> {item['orig_title']}</p>
        <a class="orig-link" href="{item['link']}" target="_blank">🔗 출처 논문/연구 원문 보기</a>
    </div>
"""
    html_content += "</body></html>"
    
    with open("summary.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def main():
    entries = fetch_gym_research_data()
    if not entries:
        send_telegram_message("⚠️ 수집된 헬스 논문 데이터가 없습니다.")
        return

    articles = []
    for entry in entries:
        title = entry.get('title', '')
        summary_raw = entry.get('summary', entry.get('description', ''))
        cleaned = clean_text(summary_raw)
        
        ko_title = safe_translate(title)
        yt_style_title = make_youtube_style_title(ko_title)
        ko_summary = safe_translate(cleaned) if cleaned else "상세 요약 본문이 제공되지 않는 논문입니다."
        
        articles.append({
            'yt_title': yt_style_title,
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
    
    msg = ["🏋️ **[오늘의 헬스 & 근성장 핵심 연구 3~5선]**\n"]
    msg.append("👇 제목을 누르면 **쉬운 한글 요약본**으로 바로 이동합니다!\n")

    for i, item in enumerate(articles, 1):
        page_link = f"{pages_base_url}#article-{i}"
        msg.append(f"{i}. [{item['yt_title']}]({page_link})")

    send_telegram_message("\n".join(msg))

if __name__ == "__main__":
    main()

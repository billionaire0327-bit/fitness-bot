import os
import requests
import feedparser
import re
from deep_translator import GoogleTranslator

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
        return ""
    try:
        truncated = text[:300]
        return GoogleTranslator(source='auto', target='ko').translate(truncated)
    except Exception:
        return text[:100]

def fetch_rss_content(url):
    # 크롤링 차단을 방지하기 위한 브라우저 흉내 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return feedparser.parse(response.content)
    except Exception as e:
        print(f"피드 로드 실패 ({url}): {e}")
        return None

def fetch_fitness_research():
    # 검증된 글로벌 학술/운동 과학 피드 목록
    rss_urls = [
        "https://www.biomedcentral.com/journals/journalofexerciserehabilitation/rss", # BMC 운동 재활 저널
        "https://www.sciencedaily.com/rss/top/sports.xml",                           # ScienceDaily 스포츠 과학
        "https://journals.plos.org/plosone/feed/atom?term=strength+training"          # PLOS ONE 근력 운동 연구
    ]
    
    entries = []
    for url in rss_urls:
        feed = fetch_rss_content(url)
        if feed and feed.entries:
            entries = feed.entries
            break

    if not entries:
        return "⚠️ 모든 학술 피드 수집에 실패했습니다. 잠시 후 다시 시도해주세요."

    messages = ["🔬 **[과학 기반 헬스/근성장 최신 연구 요약]**\n"]

    count = 0
    for entry in entries:
        if count >= 3:
            break

        title = entry.get('title', '제목 없음')
        link = entry.get('link', '')
        
        summary_raw = entry.get('summary', entry.get('description', ''))
        cleaned_summary = clean_text(summary_raw)

        ko_title = safe_translate(title)
        ko_summary = safe_translate(cleaned_summary) if cleaned_summary else "요약 본문이 제공되지 않는 논문입니다."

        card = (
            f"📌 **{count+1}. {ko_title}**\n\n"
            f"💡 **쉬운 요약:** {ko_summary}...\n\n"
            f"🔗 [원문/논문 보기]({link})"
        )
        messages.append(card)
        count += 1

    return "\n\n-------------------\n\n".join(messages)

if __name__ == "__main__":
    content = fetch_fitness_research()
    send_telegram_message(content)

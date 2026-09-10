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

def clean_html(raw_html):
    # HTML 태그 제거
    clean_text = re.sub(r'<.*?>', '', raw_html)
    return clean_text.strip()

def translate_and_summarize(text):
    try:
        translated = GoogleTranslator(source='auto', target='ko').translate(text)
        return translated
    except Exception:
        return text

def fetch_paper_data():
    # PubMed 최신 근력 운동(Strength Training) 관련 논문 RSS
    rss_url = "https://pubmed.ncbi.nlm.nih.gov/rss/search/1wX3-m6E4C_pP9z5N-qXQ/?limit=15"
    feed = feedparser.parse(rss_url)
    
    # 만약 위 RSS에 데이터가 없을 경우 대체할 과학 기반 헬스 아티클 RSS
    if not feed.entries:
        rss_url = "https://www.sciencedaily.com/rss/fitness.xml"
        feed = feedparser.parse(rss_url)

    messages = ["🔬 **[과학 기반 헬스/근성장 최신 논문 요약]**\n"]
    
    # 최신 3개 논문/아티클 가공
    for i, entry in enumerate(feed.entries[:3], 1):
        title = entry.title
        link = entry.link
        
        # 초록(Abstract) 또는 요약문 가져오기
        raw_summary = entry.get('summary', entry.get('description', ''))
        clean_summary = clean_html(raw_summary)[:250] # 너무 길지 않게 자르기
        
        # 한글 번역
        ko_title = translate_and_summarize(title)
        ko_summary = translate_and_summarize(clean_summary) if clean_summary else "요약 내용 없음"
        
        message_block = (
            f"📌 **{i}. {ko_title}**\n\n"
            f"💡 **쉬운 요약:** {ko_summary}...\n"
            f"🔗 [논문/원문 보기]({link})\n"
        )
        messages.append(message_block)
        
    return "\n-------------------\n".join(messages)

if __name__ == "__main__":
    content = fetch_paper_data()
    send_telegram_message(content)

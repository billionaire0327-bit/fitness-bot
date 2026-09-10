import os
import requests
import feedparser
from deep_translator import GoogleTranslator

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    requests.post(url, json=payload)

def translate_to_ko(text):
    try:
        # 영어 제목을 자연스러운 한국어로 번역
        return GoogleTranslator(source='auto', target='ko').translate(text)
    except Exception:
        return text  # 번역 실패 시 원문 유지

def fetch_fitness_data():
    rss_url = "https://www.reddit.com/r/Fitness/hot/.rss"
    feed = feedparser.parse(rss_url)
    
    messages = ["🏋️ **오늘의 해외 운동 소식 (한글 번역)**\n"]
    
    for entry in feed.entries[:5]:
        original_title = entry.title
        translated_title = translate_to_ko(original_title)
        link = entry.link
        
        # 번역된 제목과 원본 링크 전송
        messages.append(f"• [{translated_title}]({link})\n  _(원문: {original_title})_")
        
    return "\n\n".join(messages)

if __name__ == "__main__":
    content = fetch_fitness_data()
    send_telegram_message(content)

import os
import requests
import feedparser

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
    response = requests.post(url, json=payload)
    print("전송 결과:", response.json())

def fetch_fitness_data():
    # 레딧 r/Fitness 커뮤니티 인기 게시글 수집
    rss_url = "https://www.reddit.com/r/Fitness/hot/.rss"
    feed = feedparser.parse(rss_url)
    
    messages = ["🏋️ **오늘의 해외 운동 소식**\n"]
    
    for entry in feed.entries[:5]:
        title = entry.title
        link = entry.link
        messages.append(f"• [{title}]({link})")
        
    return "\n".join(messages)

if __name__ == "__main__":
    content = fetch_fitness_data()
    send_telegram_message(content)

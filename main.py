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
    # HTML 태그 및 특수문자 정리
    text = re.sub(r'<.*?>', '', html_text)
    text = text.replace('\n', ' ').strip()
    return text

def safe_translate(text):
    if not text:
        return ""
    try:
        # 너무 긴 텍스트는 자른 후 번역
        truncated = text[:300]
        return GoogleTranslator(source='auto', target='ko').translate(truncated)
    except Exception as e:
        print(f"번역 오류 발생: {e}")
        return text[:100]

def fetch_fitness_research():
    # 1순위: ScienceDaily 운동 과학 연구 RSS
    # 2순위: PubMed 근력 운동 검색 RSS
    rss_urls = [
        "https://www.sciencedaily.com/rss/fitness.xml",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1wX3-m6E4C_pP9z5N-qXQ/?limit=10"
    ]
    
    entries = []
    for url in rss_urls:
        feed = feedparser.parse(url)
        if feed.entries:
            entries = feed.entries
            break

    if not entries:
        return "⚠️ 최신 운동 연구 자료를 불러오는데 실패했습니다. 피드 주소를 확인해주세요."

    messages = ["🔬 **[과학 기반 헬스/근성장 최신 연구 요약]**\n"]

    count = 0
    for entry in entries:
        if count >= 3:  # 상위 3개만 가져오기
            break

        title = entry.get('title', '제목 없음')
        link = entry.get('link', '')
        
        # 요약 본문 가져오기 (summary 또는 description)
        summary_raw = entry.get('summary', entry.get('description', ''))
        cleaned_summary = clean_text(summary_raw)

        # 한국어 번역
        ko_title = safe_translate(title)
        ko_summary = safe_translate(cleaned_summary) if cleaned_summary else "요약 본문이 제공되지 않는 논문입니다."

        card = (
            f"📌 **{count+1}. {ko_title}**\n"
            f"💡 **쉬운 요약:** {ko_summary}...\n"
            f"🔗 [원문/논문 보기]({link})"
        )
        messages.append(card)
        count += 1

    return "\n\n-------------------\n\n".join(messages)

if __name__ == "__main__":
    content = fetch_fitness_research()
    send_telegram_message(content)

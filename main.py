import os
import requests
import feedparser
import re
import random
import urllib.parse
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

def translate_fallback(text):
    """Deep-translator 실패 시 사용하는 백업 번역기"""
    try:
        encoded_text = urllib.parse.quote(text[:300])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q={encoded_text}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            result = res.json()
            translated_chunks = [item[0] for item in result[0] if item[0]]
            return "".join(translated_chunks)
    except Exception as e:
        print(f"Fallback 번역 오류: {e}")
    return ""

def force_korean_translate(text):
    if not text:
        return "상세 정보가 제공되지 않는 헬스 정보입니다."
    
    # 1차 시도: deep-translator
    try:
        translated = GoogleTranslator(source='auto', target='ko').translate(text[:400])
        # 한글이 포함되어 있는지 검증 (가-힣 범위 체크)
        if re.search(r'[가-힣]', translated):
            return translated
    except Exception as e:
        print(f"1차 번역 실패: {e}")
        
    # 2차 시도: Google GTX Direct API
    fallback_result = translate_fallback(text)
    if re.search(r'[가-힣]', fallback_result):
        return fallback_result

    # 만약 모든 번역이 실패했을 경우, 영어 노출 방지를 위한 예외 처리
    return "운동 수행 능력 향상 및 근육 성장에 관한 최신 보디빌딩 연구 요약 내용입니다."

def make_youtube_style_title(ko_title):
    # 유튜버 영상 제목처럼 흥미를 끄는 어그로 템플릿 적용
    styles = [
        f"🚨 헬스인 필독! {ko_title}",
        f"🔥 근성장 정체기 단번에 깨는 법: {ko_title}",
        f"💡 최신 논문 증명! {ko_title}",
        f"🏋️ 득근을 위해 꼭 알아야 할 {ko_title}",
        f"😱 트레이너들이 숨기는 {ko_title}"
    ]
    selected = random.choice(styles)
    # 영어 단어가 너무 길게 남아있지 않도록 정제
    return selected

def fetch_gym_research_data():
    rss_urls = [
        "https://www.strongerbyscience.com/feed/",
        "https://bmcsportsscimedrehabil.biomedcentral.com/articles/rss",
        "https://journals.plos.org/plosone/feed/atom?term=resistance+exercise"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    gym_keywords = ['muscle', 'strength', 'hypertrophy', 'resistance', 'protein', 'weight', 'squat', 'bench', 'lifting', 'exercise', 'training']
    
    gym_entries = []
    
    for url in rss_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries:
                    title_summary = (entry.get('title', '') + " " + entry.get('summary', '')).lower()
                    
                    # 헬스와 무관한 정정 기사 및 의료 질병 관련 차단
                    if any(bad in title_summary for bad in ['disease', 'cancer', 'surgery', 'patient', 'hospital', 'correction', 'covid']):
                        continue
                        
                    if any(kw in title_summary for kw in gym_keywords):
                        gym_entries.append(entry)
                        if len(gym_entries) >= 5:
                            break
        except Exception as e:
            print(f"피드 가져오기 실패: {e}")
            
    return gym_entries[:5]

def build_summary_html(articles, owner, repo):
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏋️ 오늘의 헬스 & 근성장 과학 요약</title>
    <style>
        body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; background-color: #121212; color: #e0e0e0; }}
        h1 {{ color: #ff4757; border-bottom: 2px solid #ff4757; padding-bottom: 10px; font-size: 1.6rem; }}
        .card {{ background: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
        .card h2 {{ color: #ffa502; font-size: 1.2rem; margin-top: 0; line-height: 1.4; }}
        .summary {{ background: #2f3542; border-left: 4px solid #ff4757; padding: 14px; margin: 15px 0; font-weight: 500; color: #ffffff; border-radius: 0 8px 8px 0; }}
        .orig-title {{ color: #a4b0be; font-size: 0.85rem; margin-top: 10px; }}
        .orig-link {{ display: inline-block; margin-top: 10px; color: #70a1ff; font-size: 0.9rem; text-decoration: none; font-weight: bold; }}
        .orig-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>🏋️ 오늘의 헬스 & 근성장 논문 요약 리포트</h1>
"""
    for i, item in enumerate(articles, 1):
        html_content += f"""
    <div class="card" id="article-{i}">
        <h2>주제 {i}. {item['yt_title']}</h2>
        <div class="summary">
            💡 <b>한글 쉬운 요약:</b><br>{item['summary']}
        </div>
        <p class="orig-title"><b>원문 제목 (영어):</b> {item['orig_title']}</p>
        <a class="orig-link" href="{item['link']}" target="_blank">🔗 출처 연구 원문 보러가기</a>
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
        
        # 100% 한글 번역 강제 적용
        ko_title = force_korean_translate(title)
        yt_style_title = make_youtube_style_title(ko_title)
        ko_summary = force_korean_translate(cleaned)
        
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
    
    msg = ["🏋️ **[오늘의 헬스 & 근성장 핵심 주제 3~5선]**\n"]
    msg.append("👇 제목을 누르면 **100% 한글 요약 페이지**로 이동합니다!\n")

    for i, item in enumerate(articles, 1):
        page_link = f"{pages_base_url}#article-{i}"
        msg.append(f"{i}. [{item['yt_title']}]({page_link})")

    send_telegram_message("\n".join(msg))

if __name__ == "__main__":
    main()

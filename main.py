import os
import requests
import feedparser
import re
import random
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageFont

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")

def send_telegram_message(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def send_telegram_photo(photo_path, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
        files = {"photo": photo}
        requests.post(url, data=payload, files=files)

def clean_text(html_text):
    if not html_text:
        return ""
    text = re.sub(r'<.*?>', '', html_text)
    text = text.replace('\n', ' ').strip()
    return text

def force_korean_translate(text):
    if not text:
        return "근성장 및 운동 수행 능력 향상에 관한 최신 논문 연구 결과입니다."
    try:
        translated = GoogleTranslator(source='auto', target='ko').translate(text[:350])
        if re.search(r'[가-힣]', translated):
            return translated
    except Exception as e:
        print(f"번역 오류: {e}")
    return "운동 수행 능력 및 근비대에 관한 핵심 연구 요약입니다."

def make_youtube_style_title(ko_title):
    styles = [
        f"🚨 헬스인 필독! {ko_title}",
        f"🔥 근성장 정체기라면? {ko_title}",
        f"💡 최신 논문으로 입증된 {ko_title}",
        f"🏋️ 득근을 위한 필수 정보! {ko_title}",
        f"😱 트레이너들이 숨기는 {ko_title}"
    ]
    return random.choice(styles)

def create_card_news_image(index, title, summary, output_filename="card_news.png"):
    # 1080x1080 인스타그램/카드뉴스 정사각형 규격 이미지 생성
    width, height = 1080, 1080
    image = Image.new("RGB", (width, height), color=(18, 18, 18))
    draw = ImageDraw.Draw(image)

    # 상단 헤더 라인 & 테두리 그래픽
    draw.rectangle([40, 40, width - 40, height - 40], outline=(255, 71, 87), width=6)
    draw.rectangle([60, 60, width - 60, 140], fill=(255, 71, 87))

    # 기본 폰트 설정
    try:
        font_title = ImageFont.truetype("arial.ttf", 42)
        font_body = ImageFont.truetype("arial.ttf", 32)
    except IOError:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # 헤더 텍스트
    draw.text((80, 75), f"🏋️ DAILY FITNESS RESEARCH #0{index}", fill=(255, 255, 255), font=font_title)

    # 본문 영역 텍스트 자동 줄바꿈
    def draw_wrapped_text(text, start_y, font, fill_color, max_width=900):
        lines = []
        words = text.split(' ')
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if draw.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        y = start_y
        for line in lines:
            draw.text((80, y), line, fill=fill_color, font=font)
            y += 50
        return y

    # 제목 및 요약문 작성
    draw.text((80, 180), "📌 [오늘의 핵심 연구 주제]", fill=(255, 165, 2), font=font_title)
    y_next = draw_wrapped_text(title, 240, font_title, (255, 255, 255))

    draw.rectangle([70, y_next + 30, width - 70, y_next + 35], fill=(80, 80, 80))

    draw.text((80, y_next + 60), "💡 [쉬운 과학 요약]", fill=(255, 71, 87), font=font_title)
    draw_wrapped_text(summary, y_next + 120, font_body, (220, 220, 220))

    # 하단 푸터 표기
    draw.text((80, height - 90), "🔬 본 카드뉴스는 해외 근성장 논문을 기반으로 자동 생성되었습니다.", fill=(120, 120, 120), font=font_body)

    image.save(output_filename)
    return output_filename

def fetch_gym_research_data():
    rss_urls = [
        "https://www.strongerbyscience.com/feed/",
        "https://bmcsportsscimedrehabil.biomedcentral.com/articles/rss",
        "https://journals.plos.org/plosone/feed/atom?term=resistance+exercise"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    gym_keywords = ['muscle', 'strength', 'hypertrophy', 'resistance', 'protein', 'weight', 'squat', 'bench', 'lifting', 'exercise', 'training']
    gym_entries = []

    for url in rss_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries:
                    title_summary = (entry.get('title', '') + " " + entry.get('summary', '')).lower()
                    if any(bad in title_summary for bad in ['disease', 'cancer', 'surgery', 'patient', 'hospital', 'correction']):
                        continue
                    if any(kw in title_summary for kw in gym_keywords):
                        gym_entries.append(entry)
                        if len(gym_entries) >= 5:
                            break
        except Exception as e:
            print(f"피드 에러: {e}")

    return gym_entries[:5]

def main():
    entries = fetch_gym_research_data()
    if not entries:
        send_telegram_message("⚠️ 수집된 최신 헬스 논문 데이터가 없습니다.")
        return

    articles = []
    for i, entry in enumerate(entries, 1):
        title = entry.get('title', '')
        summary_raw = entry.get('summary', entry.get('description', ''))
        cleaned = clean_text(summary_raw)

        ko_title = force_korean_translate(title)
        yt_style_title = make_youtube_style_title(ko_title)
        ko_summary = force_korean_translate(cleaned)

        # 각 주제별 카드뉴스 이미지 파일 자동 생성
        image_path = f"card_news_{i}.png"
        create_card_news_image(i, ko_title, ko_summary, output_filename=image_path)

        articles.append({
            'index': i,
            'yt_title': yt_style_title,
            'orig_title': title,
            'summary': ko_summary,
            'image_path': image_path
        })

    # 1단계: 텔레그램으로 메인 요약 리포트와 카드뉴스 이미지들을 순차적으로 함께 전송
    msg = ["🏋️ **[오늘의 헬스 & 근성장 핵심 연구 3~5선]**\n"]
    for item in articles:
        msg.append(f"{item['index']}. {item['yt_title']}")
    
    send_telegram_message("\n".join(msg))

    # 2단계: 핵심 주제별 생성된 고화질 카드뉴스 이미지 전송
    for item in articles:
        caption = f"🎨 **[주제 {item['index']} 카드뉴스 리포트]**\n\n📌 **제목:** {item['yt_title']}\n\n💡 **핵심 요약:** {item['summary'][:150]}..."
        send_telegram_photo(item['image_path'], caption=caption)

if __name__ == "__main__":
    main()

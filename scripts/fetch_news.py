import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path


SEARCH_WORDS = [
    "AI",
    "OpenAI",
    "NVIDIA",
    "生成AI",
    "人工知能",
    "半導体",
]

MAX_NEWS = 20

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "news.json"


def remove_html(text: str) -> str:
    """HTMLタグを削除して読みやすくする。"""
    text = re.sub(r"<[^>]+>", "", text or "")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    return " ".join(text.split())


def create_rss_url() -> str:
    """Google News RSSの検索URLを作る。"""
    query = " OR ".join(SEARCH_WORDS)
    encoded_query = urllib.parse.quote(query)

    return (
        "https://news.google.com/rss/search"
        f"?q={encoded_query}"
        "&hl=ja"
        "&gl=JP"
        "&ceid=JP:ja"
    )


def parse_date(date_text: str) -> tuple[str, str]:
    """
    RSSの日付を表示用と並び替え用に変換する。
    戻り値: (表示用日付, ISO形式)
    """
    try:
        date = parsedate_to_datetime(date_text)

        return (
            date.astimezone().strftime("%Y/%m/%d %H:%M"),
            date.isoformat(),
        )
    except (TypeError, ValueError):
        return ("日時不明", "")


def guess_company(title: str) -> str:
    """タイトルから企業・分野タグを推測する。"""
    company_keywords = {
        "OpenAI": ["OpenAI", "ChatGPT"],
        "NVIDIA": ["NVIDIA", "エヌビディア"],
        "Google": ["Google", "Gemini", "DeepMind"],
        "Microsoft": ["Microsoft", "マイクロソフト", "Copilot"],
        "Anthropic": ["Anthropic", "Claude"],
        "Meta": ["Meta", "Llama"],
        "半導体": ["半導体", "GPU", "TSMC", "メモリ"],
    }

    for company, keywords in company_keywords.items():
        if any(keyword.lower() in title.lower() for keyword in keywords):
            return company

    return "AI"


def calculate_importance(title: str) -> str:
    """重要そうな単語を含むニュースをhighにする。"""
    important_words = [
        "発表",
        "新モデル",
        "決算",
        "提携",
        "買収",
        "規制",
        "投資",
        "半導体",
        "GPU",
        "ChatGPT",
        "Gemini",
        "Claude",
    ]

    score = sum(
        word.lower() in title.lower()
        for word in important_words
    )

    return "high" if score >= 1 else "normal"


def fetch_news() -> list[dict]:
    rss_url = create_rss_url()

    request = urllib.request.Request(
        rss_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 Ark-Terminal-News-Bot/1.0"
            )
        },
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    items = root.findall("./channel/item")

    news_list = []
    used_titles = set()

    for item in items:
        title = remove_html(item.findtext("title", ""))
        link = item.findtext("link", "")
        description = remove_html(
            item.findtext("description", "")
        )
        pub_date = item.findtext("pubDate", "")
        source_element = item.find("source")

        source = (
            source_element.text
            if source_element is not None
            else "Google News"
        )

        if not title or title in used_titles:
            continue

        used_titles.add(title)

        display_date, iso_date = parse_date(pub_date)

        news_list.append(
            {
                "company": guess_company(title),
                "category": "company",
                "importance": calculate_importance(title),
                "date": display_date,
                "publishedAt": iso_date,
                "title": title,
                "summary": description[:220],
                "impact": "AIによる投資分析は次の段階で追加予定です。",
                "source": source,
                "url": link,
            }
        )

        if len(news_list) >= MAX_NEWS:
            break

    return news_list


def main() -> None:
    try:
        news = fetch_news()

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with OUTPUT_PATH.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                news,
                file,
                ensure_ascii=False,
                indent=2,
            )

        print(f"{len(news)}件のニュースを保存しました。")

    except Exception as error:
        print(f"ニュース取得に失敗しました: {error}")
        raise


if __name__ == "__main__":
    main()
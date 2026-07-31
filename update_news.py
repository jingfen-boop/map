from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo


OUTPUT_FILE = Path("typhoon-news.html")

# Google 新聞繁體中文搜尋條件
SEARCH_KEYWORDS = '日本 颱風 OR 日本颱風 OR 颱風日本 OR 日本暴風雨'

RSS_URL = (
    "https://news.google.com/rss/search?"
    + urllib.parse.urlencode(
        {
            "q": SEARCH_KEYWORDS,
            "hl": "zh-TW",
            "gl": "TW",
            "ceid": "TW:zh-Hant",
        }
    )
)

MAX_ARTICLES = 12


def clean_text(value: str | None) -> str:
    """移除 HTML 標籤並整理空白。"""
    if not value:
        return ""

    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return " ".join(value.split())


def split_title_and_source(title: str) -> tuple[str, str]:
    """
    Google News 標題通常是：
    新聞標題 - 媒體名稱
    """
    if " - " in title:
        article_title, source = title.rsplit(" - ", 1)
        return article_title.strip(), source.strip()

    return title.strip(), ""


def format_date(date_text: str | None) -> str:
    if not date_text:
        return ""

    try:
        published = parsedate_to_datetime(date_text)

        if published.tzinfo is None:
            published = published.replace(tzinfo=ZoneInfo("UTC"))

        taipei_time = published.astimezone(ZoneInfo("Asia/Taipei"))
        return taipei_time.strftime("%m/%d %H:%M")
    except (TypeError, ValueError):
        return clean_text(date_text)


def fetch_articles() -> list[dict[str, str]]:
    request = urllib.request.Request(
        RSS_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 TyphoonNewsDashboard/1.0 "
                "(GitHub Pages RSS Reader)"
            )
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    articles: list[dict[str, str]] = []

    for item in root.findall(".//item")[:MAX_ARTICLES]:
        raw_title = clean_text(item.findtext("title"))
        title, source_from_title = split_title_and_source(raw_title)

        source_node = item.find("source")
        source = (
            clean_text(source_node.text)
            if source_node is not None
            else source_from_title
        )

        link = clean_text(item.findtext("link"))
        pub_date = format_date(item.findtext("pubDate"))

        if not title or not link:
            continue

        articles.append(
            {
                "title": title,
                "source": source or "新聞來源",
                "link": link,
                "date": pub_date,
            }
        )

    return articles


def make_article_html(article: dict[str, str]) -> str:
    title = html.escape(article["title"])
    source = html.escape(article["source"])
    date = html.escape(article["date"])
    link = html.escape(article["link"], quote=True)

    return f"""
    <article class="news-card">
      <div class="news-meta">
        <span class="source">{source}</span>
        <time>{date}</time>
      </div>

      <h2>
        <a href="{link}" target="_blank" rel="noopener noreferrer">
          {title}
        </a>
      </h2>

      <a class="read-more"
         href="{link}"
         target="_blank"
         rel="noopener noreferrer">
        閱讀原文 →
      </a>
    </article>
    """


def build_page(articles: list[dict[str, str]]) -> str:
    updated = datetime.now(ZoneInfo("Asia/Taipei")).strftime(
        "%Y/%m/%d %H:%M"
    )

    if articles:
        article_section = "\n".join(
            make_article_html(article) for article in articles
        )
    else:
        article_section = """
        <div class="empty">
          目前沒有取得相關新聞，請稍後重新整理。
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport"
        content="width=device-width, initial-scale=1.0">

  <meta http-equiv="refresh" content="1800">

  <title>日本颱風中文新聞</title>

  <style>
    :root {{
      --navy: #173b67;
      --blue: #2e73b8;
      --pale-blue: #eef7ff;
      --border: #dce8f2;
      --text: #263442;
      --muted: #687888;
      --white: #ffffff;
      --warning: #fff8e8;
    }}

    * {{
      box-sizing: border-box;
    }}

    html {{
      scroll-behavior: smooth;
    }}

    body {{
      margin: 0;
      background: #f7fafc;
      color: var(--text);
      font-family:
        "Noto Sans TC",
        "Microsoft JhengHei",
        Arial,
        sans-serif;
    }}

    .page {{
      width: min(100%, 920px);
      margin: 0 auto;
      padding: 20px 14px 30px;
    }}

    .header {{
      padding: 22px;
      margin-bottom: 16px;
      color: var(--white);
      background:
        linear-gradient(135deg, #173b67, #4288c8);
      border-radius: 18px;
    }}

    .header h1 {{
      margin: 0 0 8px;
      font-size: clamp(24px, 5vw, 34px);
    }}

    .header p {{
      margin: 0;
      line-height: 1.7;
      opacity: 0.95;
    }}

    .status {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 16px;
      align-items: center;
      padding: 12px 15px;
      margin-bottom: 14px;
      background: var(--warning);
      border: 1px solid #f1dfb4;
      border-radius: 12px;
      font-size: 14px;
      color: #725b2d;
    }}

    .status strong {{
      color: #554218;
    }}

    .news-list {{
      display: grid;
      gap: 12px;
    }}

    .news-card {{
      padding: 17px 18px;
      background: var(--white);
      border: 1px solid var(--border);
      border-radius: 14px;
    }}

    .news-card:hover {{
      border-color: #a8c9e6;
    }}

    .news-meta {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 9px;
      font-size: 13px;
      color: var(--muted);
    }}

    .source {{
      padding: 3px 9px;
      color: var(--navy);
      background: var(--pale-blue);
      border-radius: 999px;
      font-weight: 700;
    }}

    .news-card h2 {{
      margin: 0 0 12px;
      font-size: clamp(17px, 3.8vw, 21px);
      line-height: 1.55;
    }}

    .news-card h2 a {{
      color: var(--text);
      text-decoration: none;
    }}

    .news-card h2 a:hover {{
      color: var(--blue);
      text-decoration: underline;
    }}

    .read-more {{
      display: inline-block;
      color: var(--blue);
      font-size: 14px;
      font-weight: 700;
      text-decoration: none;
    }}

    .empty {{
      padding: 28px;
      text-align: center;
      background: var(--white);
      border: 1px solid var(--border);
      border-radius: 14px;
    }}

    .footer {{
      margin-top: 17px;
      padding: 14px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
      text-align: center;
    }}

    @media (max-width: 520px) {{
      .page {{
        padding: 10px 8px 20px;
      }}

      .header {{
        padding: 18px 16px;
        border-radius: 13px;
      }}

      .news-card {{
        padding: 15px;
      }}

      .news-meta {{
        align-items: flex-start;
        flex-direction: column;
        gap: 6px;
      }}
    }}
  </style>
</head>

<body>
  <main class="page">
    <header class="header">
      <h1>🌀 日本颱風中文新聞</h1>
      <p>
        自動彙整與日本颱風、暴風雨及旅遊影響相關的中文新聞。
      </p>
    </header>

    <section class="status">
      <strong>最近更新：</strong>
      <span>{updated}（台灣時間）</span>
      <span>｜約每 30 分鐘檢查一次</span>
    </section>

    <section class="news-list">
      {article_section}
    </section>

    <footer class="footer">
      新聞內容與標題著作權屬原發布媒體所有。
      本頁僅顯示標題、來源、時間與原文連結。
      颱風警報及旅行決策仍應以日本氣象廳、
      航空公司與交通機構的正式公告為準。
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    try:
        articles = fetch_articles()
        page = build_page(articles)
        OUTPUT_FILE.write_text(page, encoding="utf-8")
        print(f"已更新 {len(articles)} 則新聞。")

    except Exception as error:
        print(f"更新失敗：{error}")

        # 第一次執行失敗時仍建立一個可顯示的頁面
        if not OUTPUT_FILE.exists():
            fallback_page = build_page([])
            OUTPUT_FILE.write_text(fallback_page, encoding="utf-8")

        raise


if __name__ == "__main__":
    main()

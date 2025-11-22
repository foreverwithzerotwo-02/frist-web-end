# news/tasks.py
import time
from datetime import datetime, timedelta
import feedparser
from email.utils import parsedate_to_datetime
from django.utils import timezone
from bs4 import BeautifulSoup
from .models import News
import requests
import xml.etree.ElementTree as ET


RSS_FEEDS = {
    # "36氪": "https://36kr.com/feed",
    # "少数派": "https://sspai.com/feed",
    "China Daily（科技）": "https://www.ifanr.com/feed",
}


def _parse_published(entry):
    try:
        if getattr(entry, "published_parsed", None):
            dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
    except Exception:
        pass

    for key in ("published", "updated"):
        val = entry.get(key)
        if val:
            try:
                dt = parsedate_to_datetime(val)
                if dt.tzinfo is None:
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                return dt
            except Exception:
                continue
    return None


def _clean_summary(summary_html):
    """清理 HTML 标签并去掉末尾 '查看全文'"""
    soup = BeautifulSoup(summary_html, "html.parser")
    text = soup.get_text().strip()
    if text.endswith("查看全文"):
        text = text[:-4].strip()
    return text


def _get_feed_images(url):
    """解析原始 XML，返回 {link: image_url}"""
    resp = requests.get(url)
    resp.encoding = "utf-8"
    root = ET.fromstring(resp.content)
    ns = {"default": "http://purl.org/rss/1.0/"}  # 这里可以不用加，先简单处理

    images_map = {}
    for item in root.findall(".//item"):
        link_el = item.find("link")
        image_el = item.find("image")
        if link_el is not None and image_el is not None:
            link = link_el.text.strip()
            image = image_el.text.strip()
            images_map[link] = image
    return images_map


def _extract_image(entry):
    # feedparser 没有 image，就手动从 summary / content 里提取
    html = entry.get("summary", "") or entry.get("description", "")
    soup = BeautifulSoup(html, "html.parser")
    img = soup.find("img")
    return img["src"] if img else None


def extract_summary_from_content(encoded_html, max_length=300):
    """
    从 content:encoded 中抽取前几个段落文本，生成摘要
    """
    soup = BeautifulSoup(encoded_html, "html.parser")
    texts = []

    # 遍历段落 <p> 标签
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            texts.append(text)
        # 达到最大长度就停止
        if sum(len(t) for t in texts) >= max_length:
            break

    summary = " ".join(texts)
    if len(summary) > max_length:
        summary = summary[:max_length] + "…"
    return summary


def fetch_news_once():
    MAX_ITEMS = 20  # 一次最多抓取n条

    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        images_map = _get_feed_images(url)  # 多一步：解析原始 XML

        for entry in feed.entries[:MAX_ITEMS]:
            link = entry.get("link")
            if not link:
                continue

            # 先看 feedparser 有没有解析到
            image = entry.get("image")

            # 如果没有，就从 XML 里查
            if not image:
                image = images_map.get(link)

            # 再兜底：去 summary 里找 <img>
            if not image:
                image = _extract_image(entry)

            title = entry.get("title", "")[:255]
            content_html = entry.get("content", [{}])[0].get("value", "")
            if content_html:
                summary = extract_summary_from_content(content_html)
            else:
                # fallback
                summary_html = entry.get("description", "")
                summary = _clean_summary(summary_html)
            published = _parse_published(entry)

            obj, created = News.objects.get_or_create(
                link=link,
                defaults={
                    "title": title,
                    "summary": summary,
                    "source": source,
                    "published": published,
                    "image_url": image,
                }
            )
            if not created:
                changed = False
                if obj.title != title:
                    obj.title = title
                    changed = True
                if summary and obj.summary != summary:
                    obj.summary = summary
                    changed = True
                if published and obj.published != published:
                    obj.published = published
                    changed = True
                if changed:
                    obj.save()


def delete_old_news(days=30):
    """删除超过 days 天的新闻"""
    threshold = timezone.now() - timedelta(days=days)
    deleted_count, _ = News.objects.filter(created_at__lt=threshold).delete()
    print(f"Deleted {deleted_count} old news")


def fetch_news_and_clean():
    """抓取 + 清理组合函数"""
    fetch_news_once()
    delete_old_news(days=30)

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from hermers.title_clean import clean_news_title

USER_AGENT = "Hermers/0.1 (+https://github.com/pengczeczec-hub/penghermers)"


@dataclass
class ArticleExtract:
    title: str
    paragraphs: list[str]


def fetch_article(url: str, *, timeout: float = 25.0) -> ArticleExtract:
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    title = (soup.title.string if soup.title else "").strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    title = clean_news_title(title)

    paragraphs: list[str] = []
    for p in soup.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text()).strip()
        if len(text) >= 40:
            paragraphs.append(text)
        if len(paragraphs) >= 10:
            break

    if not paragraphs:
        body = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        if body:
            paragraphs = [body[:1200]]

    return ArticleExtract(title=title or url, paragraphs=paragraphs)

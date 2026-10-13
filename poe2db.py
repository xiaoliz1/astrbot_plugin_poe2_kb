"""Poe2DB URL validation, page parsing, and text chunking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote, unquote, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup


BASE_URL = "https://poe2db.tw"
LOCALE_NAMES = {"cn": "简体中文", "tw": "繁體中文"}
REMOVE_SELECTORS = (
    "script",
    "style",
    "noscript",
    "iframe",
    "nav",
    "footer",
    ".navbar",
    ".cookie",
    "#consent-box",
    "#head_toolbar",
    "#topbanner970",
)


@dataclass(frozen=True)
class ParsedPage:
    locale: str
    slug: str
    title: str
    url: str
    chunks: list[str]
    links: list[str]

    @property
    def doc_name(self) -> str:
        safe_slug = re.sub(r"[^\w\-\u4e00-\u9fff]+", "_", self.slug).strip("_")
        return f"poe2db-{safe_slug or 'home'}"[:120]


def normalize_locale(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("_", "-")
    aliases = {
        "cn": "cn",
        "zh-cn": "cn",
        "zh-hans": "cn",
        "简体": "cn",
        "简体中文": "cn",
        "tw": "tw",
        "zh-tw": "tw",
        "zh-hant": "tw",
        "繁体": "tw",
        "繁體": "tw",
        "繁体中文": "tw",
        "繁體中文": "tw",
    }
    locale = aliases.get(normalized)
    if not locale:
        raise ValueError("语言请填写 cn（简体）或 tw（繁体）。")
    return locale


def _validate_page_url(url: str, locale: str) -> str:
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() != "poe2db.tw":
        raise ValueError("只允许抓取 poe2db.tw 域名。")
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("页面地址必须使用 HTTP 或 HTTPS。")
    segments = [unquote(part) for part in parsed.path.split("/") if part]
    if not segments or segments[0] != locale or len(segments) > 2:
        raise ValueError(f"页面必须位于 Poe2DB 的 /{locale}/ 路径下。")
    if any(
        part in {".", ".."} or "/" in part or "\\" in part
        for part in segments
    ):
        raise ValueError("页面路径包含不支持的斜杠或目录跳转。")
    if len(segments) == 2 and segments[1].lower().endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf", ".zip")
    ):
        raise ValueError("图片、压缩包和附件不能作为知识库页面。")
    clean_path = parsed.path or f"/{locale}/"
    if clean_path.rstrip("/") == f"/{locale}":
        clean_path = f"/{locale}/"
    return urlunparse(("https", "poe2db.tw", clean_path, "", "", ""))


def normalize_entry(value: str | None, locale: str) -> str:
    locale = normalize_locale(locale)
    raw = (value or "").strip()
    if not raw or raw == "/":
        return f"{BASE_URL}/{locale}/"

    if raw.startswith(("https://", "http://")):
        return _validate_page_url(raw, locale)

    path = unquote(raw).strip("/")
    if path in {"cn", "tw"}:
        if path != locale:
            raise ValueError(f"所选语言为 {locale}，入口页却指定了 /{path}/。")
        return f"{BASE_URL}/{locale}/"
    if path.startswith(("cn/", "tw/")):
        path_locale, _, slug = path.partition("/")
        if path_locale != locale:
            raise ValueError(f"所选语言为 {locale}，入口页却指定了 /{path_locale}/。")
        path = slug
    if not path or "/" in path:
        raise ValueError("入口请填写单个页面 slug，例如 Skill_Gems，或 /cn/ 页面链接。")
    encoded = quote(path, safe="()_-")
    return f"{BASE_URL}/{locale}/{encoded}"


def normalize_article_link(href: str, current_url: str, locale: str) -> str | None:
    if not href or href.startswith(("#", "javascript:", "mailto:", "data:")):
        return None
    candidate = urljoin(current_url, href)
    try:
        normalized = _validate_page_url(candidate, locale)
    except ValueError:
        return None
    return normalized


def _clean_text(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\u200b", "")
    lines: list[str] = []
    for raw_line in value.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return "\n".join(lines).strip()


def _page_title(soup: BeautifulSoup, slug: str) -> str:
    for selector in ("h1", ".itemName.typeLine", ".itemName"):
        node = soup.select_one(selector)
        if node:
            title = _clean_text(node.get_text(" ", strip=True))
            if title:
                return title

    if soup.title:
        title = _clean_text(soup.title.get_text(" ", strip=True))
        for suffix in (
            " - 流亡2编年史, Path of Exile Wiki cn",
            " - 流亡2編年史, Path of Exile Wiki tw",
        ):
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
                break
        if title:
            return title
    return "首页" if not slug else slug.replace("_", " ")


def _split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    max_chars = max(300, max_chars)
    overlap = min(max(0, overlap), max_chars // 3)
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            split_at = max(
                text.rfind("\n", start, end),
                text.rfind("。", start, end),
                text.rfind("！", start, end),
                text.rfind("？", start, end),
                text.rfind("；", start, end),
            )
            if split_at > start + int(max_chars * 0.55):
                end = split_at + 1
        part = text[start:end].strip()
        if part:
            chunks.append(part)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def parse_poe2db_page(
    url: str,
    html: str,
    locale: str,
    chunk_chars: int = 1200,
    overlap_chars: int = 100,
    max_page_chars: int = 50000,
) -> ParsedPage:
    locale = normalize_locale(locale)
    url = _validate_page_url(url, locale)
    soup = BeautifulSoup(html, "lxml")
    segments = [unquote(part) for part in urlparse(url).path.split("/") if part]
    slug = segments[1] if len(segments) > 1 else ""
    title = _page_title(soup, slug)

    root = soup.select_one(".page-content") or soup.body or soup
    working = BeautifulSoup(str(root), "lxml")
    root = working.select_one(".page-content") or working.body or working
    for selector in REMOVE_SELECTORS:
        for node in root.select(selector):
            node.decompose()

    links: list[str] = []
    seen_links: set[str] = set()
    for anchor in root.select("a[href]"):
        link = normalize_article_link(anchor.get("href", "").strip(), url, locale)
        if link and link not in seen_links and link != url:
            links.append(link)
            seen_links.add(link)

    body = _clean_text(root.get_text("\n", strip=True))
    if len(body) > max_page_chars:
        body = body[:max_page_chars].rstrip() + "\n[页面内容过长，已截断]"

    prefix = (
        "游戏：流放之路2\n"
        f"语言：{LOCALE_NAMES[locale]}\n"
        f"词条：{title}\n"
        f"页面标识：{slug or '/'}\n"
        f"来源：{url}\n\n"
    )
    content_limit = max(300, chunk_chars - len(prefix))
    chunks = [
        f"{prefix}{part}".strip()
        for part in _split_text(body, content_limit, overlap_chars)
    ]
    return ParsedPage(
        locale=locale,
        slug=slug,
        title=title,
        url=url,
        chunks=chunks,
        links=links,
    )

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests


ARXIV_API_URL = "https://export.arxiv.org/api/query"
DBLP_API_URL = "https://dblp.org/search/publ/api"
CROSSREF_API_URL = "https://api.crossref.org/works"
REQUEST_TIMEOUT = 60
REQUEST_SLEEP = 0.35
AUTO_BLOCK_START = "<!-- AUTO-HARVEST:START -->"
AUTO_BLOCK_END = "<!-- AUTO-HARVEST:END -->"
SOURCE_CHOICES = ("arxiv", "dblp", "crossref")
ARTICLE_LIKE_CROSSREF_TYPES = {
    "journal-article",
    "proceedings-article",
    "posted-content",
    "book-chapter",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "using",
    "via",
    "with",
}
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}


@dataclass
class SourceRecord:
    source: str
    query: str
    title: str
    year: int | None = None
    venue: str = ""
    official_url: str = ""
    pdf_url: str = ""
    doi: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""


@dataclass
class Candidate:
    title: str
    normalized_title: str
    year: int | None = None
    venue: str = ""
    official_url: str = ""
    pdf_url: str = ""
    doi: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    sources: list[dict[str, object]] = field(default_factory=list)
    source_names: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    include_hits: list[str] = field(default_factory=list)
    exclude_hits: list[str] = field(default_factory=list)
    best_query_score: float = 0.0
    final_score: float = 0.0
    classification: str = ""
    existing_in_vault: bool = False
    note_path: str = ""
    local_pdf: str = ""


@dataclass
class VaultScan:
    titles: set[str] = field(default_factory=set)
    dois: set[str] = field(default_factory=set)
    urls: set[str] = field(default_factory=set)
    note_by_title: dict[str, str] = field(default_factory=dict)
    note_by_doi: dict[str, str] = field(default_factory=dict)
    note_by_url: dict[str, str] = field(default_factory=dict)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Harvest candidate papers for a research knowledge base from web sources."
    )
    parser.add_argument("--topic", required=True, help="Human-readable topic title.")
    parser.add_argument("--query", action="append", default=[], help="Seed query. Repeatable.")
    parser.add_argument(
        "--include-keyword",
        action="append",
        default=[],
        help="Optional keyword that boosts relevance. Repeatable.",
    )
    parser.add_argument(
        "--exclude-keyword",
        action="append",
        default=[],
        help="Optional keyword that lowers confidence. Repeatable.",
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=SOURCE_CHOICES,
        default=[],
        help="Source to query. Defaults to arxiv, dblp, and crossref.",
    )
    parser.add_argument("--max-per-query", type=int, default=40, help="Maximum hits per query per source.")
    parser.add_argument("--year-from", type=int, help="Optional lower bound for publication year.")
    parser.add_argument("--year-to", type=int, help="Optional upper bound for publication year.")
    parser.add_argument("--vault", help="Optional vault root for duplicate checking and managed pending import.")
    parser.add_argument("--prefix", help="KB prefix used to locate <prefix>-待处理清单.md inside the vault.")
    parser.add_argument("--notes-folder", help="Optional canonical notes folder name inside the vault.")
    parser.add_argument("--triage-folder", help="Optional triage note folder name inside the vault.")
    parser.add_argument("--out-dir", help="Directory for the JSON manifest and Markdown report.")
    parser.add_argument(
        "--download-pdfs",
        action="store_true",
        help="Force PDF download even when no vault path is provided.",
    )
    parser.add_argument(
        "--skip-pdf-download",
        action="store_true",
        help="Skip PDF download even when a vault or PDF directory is provided.",
    )
    parser.add_argument("--pdf-dir", help="Directory for downloaded PDFs.")
    parser.add_argument("--max-downloads", type=int, default=12, help="Maximum PDFs to download in one run.")
    parser.add_argument(
        "--skip-note-stubs",
        action="store_true",
        help="Do not create or update triage note stubs for harvested papers.",
    )
    parser.add_argument(
        "--mailto",
        help="Optional email address for polite API access, especially helpful for Crossref.",
    )
    return parser.parse_args(argv)


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(text: str | None) -> str:
    text = clean_text(text).lower()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[_\\-–—/]+", " ", text)
    text = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_title(text: str | None) -> str:
    return normalize_text(text)


def normalize_doi(text: str | None) -> str:
    value = clean_text(text).lower().strip()
    value = value.removeprefix("https://doi.org/")
    value = value.removeprefix("http://doi.org/")
    return value.rstrip("/")


def normalize_url(text: str | None) -> str:
    return clean_text(text).strip().rstrip("/")


def slugify(text: str) -> str:
    text = normalize_text(text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "topic"


def query_terms(query: str) -> list[str]:
    query = clean_text(query)
    if re.search(r"[\u4e00-\u9fff]", query) and " " not in query:
        return [normalize_text(query)]
    terms = [term for term in re.split(r"[^a-zA-Z0-9]+", query.lower()) if term]
    return [term for term in terms if term not in STOPWORDS and len(term) > 1]


def unique_preserve(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = clean_text(value)
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def remember_path(mapping: dict[str, str], key: str, relative_path: str) -> None:
    if key and key not in mapping:
        mapping[key] = relative_path


def obsidian_link(relative_path: str, alias: str | None = None) -> str:
    if alias:
        return f"[[{relative_path}|{alias}]]"
    return f"[[{relative_path}]]"


def looks_like_pdf(url: str) -> bool:
    normalized = normalize_url(url).lower()
    return normalized.endswith(".pdf") or "/pdf/" in normalized or "download" in normalized


def build_session(mailto: str | None) -> requests.Session:
    session = requests.Session()
    agent = "Codex-Research-KB-Harvester/1.0"
    if mailto:
        agent = f"{agent} ({mailto})"
    session.headers.update({"User-Agent": agent})
    return session


def build_arxiv_search_query(query: str) -> str:
    terms = query_terms(query)
    if len(terms) == 1:
        return f'all:"{terms[0]}"'
    if terms:
        return " AND ".join(f'all:"{term}"' for term in terms)
    phrase = clean_text(query)
    return f'all:"{phrase}"'


def extract_crossref_year(item: dict[str, object]) -> int | None:
    for key in ("published-print", "published-online", "issued", "created"):
        value = item.get(key)
        if not isinstance(value, dict):
            continue
        parts = value.get("date-parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                continue
    return None


def score_query_match(title: str, abstract: str, query: str) -> float:
    normalized_title = normalize_title(title)
    normalized_text = normalize_text(f"{title} {abstract}")
    phrase = normalize_text(query)
    terms = query_terms(query)
    score = 0.0
    if phrase and phrase in normalized_title:
        score += 12.0
    elif phrase and phrase in normalized_text:
        score += 8.0
    if terms:
        title_hits = sum(1 for term in terms if term in normalized_title)
        text_hits = sum(1 for term in terms if term in normalized_text)
        if title_hits == len(terms):
            score = max(score, 9.0)
        elif text_hits == len(terms):
            score = max(score, 6.0)
        else:
            score = max(score, min(float(title_hits * 2 + max(text_hits - title_hits, 0)), 5.0))
    return score


def keyword_hits(title: str, abstract: str, venue: str, keywords: list[str]) -> list[str]:
    normalized_text = normalize_text(f"{title} {abstract} {venue}")
    hits = []
    for keyword in keywords:
        normalized = normalize_text(keyword)
        if normalized and normalized in normalized_text:
            hits.append(keyword)
    return unique_preserve(hits)


def find_best_pdf_url(record: SourceRecord) -> str:
    if looks_like_pdf(record.pdf_url):
        return record.pdf_url
    if looks_like_pdf(record.official_url):
        return record.official_url
    if record.official_url.startswith("https://arxiv.org/abs/"):
        return record.official_url.replace("/abs/", "/pdf/") + ".pdf"
    return ""


def fetch_arxiv(session: requests.Session, query: str, max_results: int) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    start = 0
    while start < max_results:
        batch = min(100, max_results - start)
        response = session.get(
            ARXIV_API_URL,
            params={"search_query": build_arxiv_search_query(query), "start": start, "max_results": batch},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        entries = root.findall("atom:entry", ARXIV_NS)
        if not entries:
            break
        for entry in entries:
            title = clean_text(entry.findtext("atom:title", default="", namespaces=ARXIV_NS))
            abstract = clean_text(entry.findtext("atom:summary", default="", namespaces=ARXIV_NS))
            authors = [
                clean_text(author.findtext("atom:name", default="", namespaces=ARXIV_NS))
                for author in entry.findall("atom:author", ARXIV_NS)
            ]
            official_url = ""
            pdf_url = ""
            for link in entry.findall("atom:link", ARXIV_NS):
                href = clean_text(link.attrib.get("href"))
                rel = clean_text(link.attrib.get("rel"))
                title_attr = clean_text(link.attrib.get("title"))
                if rel == "alternate" and href:
                    official_url = href
                if title_attr == "pdf" and href:
                    pdf_url = href
            published = clean_text(entry.findtext("atom:published", default="", namespaces=ARXIV_NS))
            year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
            records.append(
                SourceRecord(
                    source="arxiv",
                    query=query,
                    title=title,
                    year=year,
                    venue="arXiv",
                    official_url=official_url,
                    pdf_url=pdf_url,
                    authors=unique_preserve(authors),
                    abstract=abstract,
                )
            )
        if len(entries) < batch:
            break
        start += len(entries)
        time.sleep(REQUEST_SLEEP)
    return records


def fetch_dblp(session: requests.Session, query: str, max_results: int) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    offset = 0
    while offset < max_results:
        batch = min(100, max_results - offset)
        response = session.get(
            DBLP_API_URL,
            params={"q": query, "format": "json", "h": batch, "f": offset},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        if isinstance(hits, dict):
            hits = [hits]
        if not hits:
            break
        for hit in hits:
            info = hit.get("info", {})
            if not isinstance(info, dict):
                continue
            raw_authors = info.get("authors", {}).get("author", [])
            if isinstance(raw_authors, dict):
                raw_authors = [raw_authors]
            authors = [
                clean_text(author.get("text") if isinstance(author, dict) else str(author))
                for author in raw_authors
            ]
            ee = info.get("ee", "")
            if isinstance(ee, list):
                ee = next((clean_text(item) for item in ee if clean_text(item)), "")
            else:
                ee = clean_text(ee)
            doi = clean_text(info.get("doi", ""))
            pdf_url = ee if looks_like_pdf(ee) else ""
            records.append(
                SourceRecord(
                    source="dblp",
                    query=query,
                    title=clean_text(info.get("title", "")),
                    year=int(info["year"]) if str(info.get("year", "")).isdigit() else None,
                    venue=clean_text(info.get("venue", "")),
                    official_url=ee or clean_text(info.get("url", "")) or (f"https://doi.org/{doi}" if doi else ""),
                    pdf_url=pdf_url,
                    doi=doi,
                    authors=unique_preserve(authors),
                )
            )
        if len(hits) < batch:
            break
        offset += len(hits)
        time.sleep(REQUEST_SLEEP)
    return records


def fetch_crossref(session: requests.Session, query: str, max_results: int, mailto: str | None) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    offset = 0
    while offset < max_results:
        batch = min(100, max_results - offset)
        params = {"query.title": query, "rows": batch, "offset": offset}
        if mailto:
            params["mailto"] = mailto
        response = session.get(CROSSREF_API_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
        if not items:
            break
        for item in items:
            if item.get("type") not in ARTICLE_LIKE_CROSSREF_TYPES:
                continue
            title_list = item.get("title", [])
            title = clean_text(title_list[0] if title_list else "")
            container_titles = item.get("container-title", [])
            venue = clean_text(container_titles[0] if container_titles else "")
            official_url = clean_text(
                item.get("resource", {}).get("primary", {}).get("URL") or item.get("URL", "")
            )
            pdf_url = ""
            for link in item.get("link", []) or []:
                if not isinstance(link, dict):
                    continue
                candidate_url = clean_text(link.get("URL", ""))
                if looks_like_pdf(candidate_url):
                    pdf_url = candidate_url
                    break
            authors = []
            for author in item.get("author", []) or []:
                if not isinstance(author, dict):
                    continue
                given = clean_text(author.get("given", ""))
                family = clean_text(author.get("family", ""))
                full_name = clean_text(f"{given} {family}")
                if full_name:
                    authors.append(full_name)
            records.append(
                SourceRecord(
                    source="crossref",
                    query=query,
                    title=title,
                    year=extract_crossref_year(item),
                    venue=venue or clean_text(item.get("publisher", "")),
                    official_url=official_url or (f"https://doi.org/{item['DOI']}" if item.get("DOI") else ""),
                    pdf_url=pdf_url,
                    doi=clean_text(item.get("DOI", "")),
                    authors=unique_preserve(authors),
                    abstract=clean_text(item.get("abstract", "")),
                )
            )
        if len(items) < batch:
            break
        offset += len(items)
        time.sleep(REQUEST_SLEEP)
    return records


def filter_records_by_year(records: list[SourceRecord], year_from: int | None, year_to: int | None) -> list[SourceRecord]:
    filtered: list[SourceRecord] = []
    for record in records:
        if year_from is not None and record.year is not None and record.year < year_from:
            continue
        if year_to is not None and record.year is not None and record.year > year_to:
            continue
        filtered.append(record)
    return filtered


def merge_candidates(records: list[SourceRecord]) -> list[Candidate]:
    merged: dict[str, Candidate] = {}
    for record in records:
        key = normalize_doi(record.doi) or normalize_title(record.title)
        if not key:
            continue
        candidate = merged.get(key)
        if candidate is None:
            candidate = Candidate(title=record.title, normalized_title=normalize_title(record.title))
            merged[key] = candidate
        if record.title and len(record.title) > len(candidate.title):
            candidate.title = record.title
        if candidate.year is None and record.year is not None:
            candidate.year = record.year
        elif candidate.year is not None and record.year is not None:
            candidate.year = min(candidate.year, record.year)
        if record.venue and (not candidate.venue or candidate.venue == "arXiv"):
            if record.source != "arxiv" or not candidate.venue:
                candidate.venue = record.venue
        if record.official_url and (not candidate.official_url or "arxiv.org" in candidate.official_url):
            candidate.official_url = record.official_url
        if record.doi and not candidate.doi:
            candidate.doi = record.doi
        if record.abstract and len(record.abstract) > len(candidate.abstract):
            candidate.abstract = record.abstract
        if record.pdf_url and not candidate.pdf_url:
            candidate.pdf_url = record.pdf_url
        candidate.authors = unique_preserve(candidate.authors + record.authors)
        candidate.queries = unique_preserve(candidate.queries + [record.query])
        candidate.source_names = unique_preserve(candidate.source_names + [record.source])
        candidate.sources.append(asdict(record))
    return list(merged.values())


def scan_existing_vault(vault: Path | None) -> VaultScan:
    scan = VaultScan()
    if vault is None or not vault.exists():
        return scan
    for path in vault.rglob("*.md"):
        parts_lower = {part.lower() for part in path.parts}
        if ".obsidian" in parts_lower or "assets" in parts_lower:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relative_path = path.relative_to(vault).as_posix()
        title_match = re.search(r"^title:\s*(.+)$", content, flags=re.MULTILINE)
        if title_match:
            key = normalize_title(title_match.group(1).strip().strip("\"'"))
            scan.titles.add(key)
            remember_path(scan.note_by_title, key, relative_path)
        heading_match = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        if heading_match:
            key = normalize_title(heading_match.group(1).strip())
            scan.titles.add(key)
            remember_path(scan.note_by_title, key, relative_path)
        doi_match = re.search(r"^doi:\s*(.+)$", content, flags=re.MULTILINE)
        if doi_match:
            normalized = normalize_doi(doi_match.group(1))
            if normalized and normalized != "n a":
                scan.dois.add(normalized)
                remember_path(scan.note_by_doi, normalized, relative_path)
        for url in re.findall(r"https?://[^\s)>]+", content):
            normalized = normalize_url(url)
            if normalized:
                scan.urls.add(normalized)
                remember_path(scan.note_by_url, normalized, relative_path)
    return scan


def classify_candidates(
    candidates: list[Candidate],
    include_keywords: list[str],
    exclude_keywords: list[str],
    vault_scan: VaultScan,
) -> None:
    for candidate in candidates:
        candidate.include_hits = keyword_hits(candidate.title, candidate.abstract, candidate.venue, include_keywords)
        candidate.exclude_hits = keyword_hits(candidate.title, candidate.abstract, candidate.venue, exclude_keywords)
        candidate.best_query_score = max(
            (score_query_match(candidate.title, candidate.abstract, query) for query in candidate.queries),
            default=0.0,
        )
        candidate.final_score = (
            candidate.best_query_score
            + max(0, len(candidate.source_names) - 1)
            + 2 * len(candidate.include_hits)
            - 3 * len(candidate.exclude_hits)
        )
        candidate.pdf_url = find_best_pdf_url(
            SourceRecord(
                source="merged",
                query="",
                title=candidate.title,
                year=candidate.year,
                venue=candidate.venue,
                official_url=candidate.official_url,
                pdf_url=candidate.pdf_url,
                doi=candidate.doi,
                authors=candidate.authors,
                abstract=candidate.abstract,
            )
        )
        title_key = normalize_title(candidate.title)
        doi_key = normalize_doi(candidate.doi)
        url_key = normalize_url(candidate.official_url)
        if title_key in vault_scan.titles or (doi_key and doi_key in vault_scan.dois) or (url_key and url_key in vault_scan.urls):
            candidate.existing_in_vault = True
            candidate.note_path = (
                vault_scan.note_by_doi.get(doi_key)
                or vault_scan.note_by_title.get(title_key)
                or vault_scan.note_by_url.get(url_key, "")
            )
            candidate.classification = "existing"
            continue
        if candidate.final_score >= 10 and not candidate.exclude_hits:
            candidate.classification = "core"
        elif candidate.final_score >= 6 or (candidate.include_hits and candidate.final_score >= 4):
            candidate.classification = "bridge"
        else:
            candidate.classification = "low-confidence"


def safe_file_name(title: str, year: int | None) -> str:
    prefix = f"{year} " if year else ""
    base = (prefix + clean_text(title)).strip()
    base = re.sub(r'[<>:"/\\\\|?*]+', "-", base)
    base = re.sub(r"\s+", " ", base).strip()
    return (base[:160] or "paper") + ".pdf"


def safe_note_name(title: str, year: int | None) -> str:
    prefix = f"{year} " if year else ""
    base = (prefix + clean_text(title)).strip()
    base = re.sub(r'[<>:"/\\\\|?*]+', "-", base)
    base = re.sub(r"\s+", " ", base).strip()
    return (base[:160] or "paper") + ".md"


def kb_config_path(vault: Path, prefix: str) -> Path:
    return vault / "assets" / "paper_search" / "configs" / f"{prefix}-kb-config.json"


def load_kb_config(vault: Path | None, prefix: str | None) -> dict[str, object]:
    if vault is None or prefix is None:
        return {}
    path = kb_config_path(vault, prefix)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_note_folders(
    vault: Path | None,
    prefix: str | None,
    notes_folder_arg: str | None,
    triage_folder_arg: str | None,
) -> tuple[str, str]:
    if vault is None:
        return clean_text(notes_folder_arg), clean_text(triage_folder_arg)

    config = load_kb_config(vault, prefix)
    notes_folder = clean_text(notes_folder_arg) or clean_text(str(config.get("notes_folder", "")))
    triage_folder = clean_text(triage_folder_arg) or clean_text(str(config.get("triage_folder", "")))

    if not notes_folder and prefix:
        candidates = [
            child.name
            for child in vault.iterdir()
            if child.is_dir()
            and child.name not in {"assets", ".obsidian"}
            and child.name.startswith(f"{prefix}-")
            and not child.name.endswith("-待处理")
        ]
        if len(candidates) == 1:
            notes_folder = candidates[0]

    if not triage_folder:
        if notes_folder:
            triage_folder = f"{notes_folder}-待处理"
        elif prefix:
            triage_folder = f"{prefix}-待处理笔记"

    return notes_folder, triage_folder


def build_triage_note(candidate: Candidate, prefix: str, vault: Path) -> str:
    safe_title = candidate.title.replace('"', "'")
    local_pdf_embed = ""
    if candidate.local_pdf:
        pdf_path = Path(candidate.local_pdf)
        if vault in pdf_path.parents:
            local_pdf_embed = obsidian_link(pdf_path.relative_to(vault).as_posix())

    lines = [
        "---",
        "tags:",
        "  - paper-note",
        "  - triage-note",
        f"  - {prefix}",
        f"title: \"{safe_title}\"",
        f"year: {candidate.year if candidate.year is not None else 'N/A'}",
        f"venue: {candidate.venue or 'N/A'}",
        "tier: pending",
        f"subtype: {candidate.classification or 'pending'}",
        "category: pending",
        f"official_url: {candidate.official_url or 'N/A'}",
        f"doi: {candidate.doi or 'N/A'}",
        f"reading_status: {'pdf-downloaded' if candidate.local_pdf else 'metadata-only'}",
        f"evidence_level: {'pdf-available' if candidate.local_pdf else 'metadata-only'}",
        f'one_sentence: "{safe_title} | pending triage"' if safe_title else 'one_sentence: "pending triage"',
        "---",
        "",
        f"# {safe_title}",
        "",
        f"[[{prefix}-待处理清单|返回待处理清单]]",
        f"[[{prefix}-索引|返回总索引]]",
        "",
        "## 当前状态",
        "",
        f"- 分类：{candidate.classification or 'pending'}",
        f"- 年份：{candidate.year if candidate.year is not None else '待补'}",
        f"- 来源：{candidate.venue or '待补'}",
        f"- 分数：{candidate.final_score:.1f}",
        f"- 检索来源：{', '.join(candidate.source_names) if candidate.source_names else '待补'}",
        f"- 命中查询：{', '.join(candidate.queries) if candidate.queries else '待补'}",
        "",
        "## 外部入口",
        "",
        f"- 官方页面：{candidate.official_url or 'N/A'}",
        f"- 在线 PDF：{candidate.pdf_url or 'N/A'}",
        f"- 本地 PDF：{local_pdf_embed or '待下载'}",
        "",
    ]
    if local_pdf_embed:
        lines += [
            "## 论文原文（内嵌 PDF）",
            "",
            f"!{local_pdf_embed}",
            "",
        ]
    lines += [
        "## 为什么先收进来",
        "",
        f"- 相关查询：{', '.join(candidate.queries) if candidate.queries else '待补'}",
        f"- include 命中：{', '.join(candidate.include_hits) if candidate.include_hits else '无'}",
        f"- exclude 命中：{', '.join(candidate.exclude_hits) if candidate.exclude_hits else '无'}",
        "",
        "## 读这篇时优先确认什么",
        "",
        "- 它到底解决什么任务设置",
        "- 它相对最近 baseline 的真实改动",
        "- 训练和推理流程是否真的和 claim 对应",
        "- 最强证据是否足够支撑作者结论",
        "",
        "## 当前摘录",
        "",
        "- 摘要要点：待补",
        "- 方法主线：待补",
        "- 主结果：待补",
        "- 最大疑问：待补",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def ensure_note_stub(
    candidate: Candidate,
    vault: Path,
    prefix: str,
    triage_folder: str,
) -> bool:
    if candidate.note_path or candidate.classification not in {"core", "bridge"}:
        return False
    target = vault / triage_folder / safe_note_name(candidate.title, candidate.year)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(build_triage_note(candidate, prefix, vault), encoding="utf-8")
    candidate.note_path = target.relative_to(vault).as_posix()
    return True


def download_candidate_pdfs(
    session: requests.Session,
    candidates: list[Candidate],
    pdf_dir: Path,
    max_downloads: int,
) -> int:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    downloads = 0
    ordered = sorted(
        (candidate for candidate in candidates if candidate.classification in {"core", "bridge"} and not candidate.existing_in_vault),
        key=lambda item: (item.classification != "core", -item.final_score, item.year or 0),
    )
    for candidate in ordered:
        if downloads >= max_downloads:
            break
        if not candidate.pdf_url:
            continue
        target = pdf_dir / safe_file_name(candidate.title, candidate.year)
        if target.exists() and target.stat().st_size > 10_240:
            candidate.local_pdf = str(target)
            continue
        try:
            response = session.get(candidate.pdf_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException:
            continue
        content_type = response.headers.get("content-type", "").lower()
        content = response.content
        if "pdf" not in content_type and not content.startswith(b"%PDF"):
            continue
        target.write_bytes(content)
        candidate.local_pdf = str(target)
        downloads += 1
        time.sleep(REQUEST_SLEEP)
    return downloads


def format_candidate_line(candidate: Candidate, vault: Path | None) -> str:
    title = obsidian_link(candidate.note_path, candidate.title) if candidate.note_path else candidate.title
    parts = [title]
    meta: list[str] = []
    if candidate.year:
        meta.append(str(candidate.year))
    if candidate.venue:
        meta.append(candidate.venue)
    if meta:
        parts.append(f"({' ; '.join(meta)})".replace(" ; ", "; "))
    parts.append(f"`score={candidate.final_score:.1f}`")
    parts.append(f"`sources={','.join(candidate.source_names)}`")
    if candidate.doi:
        parts.append(f"`doi={normalize_doi(candidate.doi)}`")
    line = "- " + " ".join(parts)
    extra_lines: list[str] = []
    if candidate.note_path:
        extra_lines.append(f"  Note: {obsidian_link(candidate.note_path)}")
    if candidate.official_url:
        extra_lines.append(f"  Official: {candidate.official_url}")
    if candidate.pdf_url:
        extra_lines.append(f"  PDF: {candidate.pdf_url}")
    if candidate.local_pdf:
        local_path = Path(candidate.local_pdf)
        if vault and vault in local_path.parents:
            relative = local_path.relative_to(vault).as_posix()
            extra_lines.append(f"  Local PDF: [[{relative}]]")
        else:
            extra_lines.append(f"  Local PDF: {candidate.local_pdf}")
    why_bits: list[str] = []
    if candidate.queries:
        why_bits.append("queries=" + ", ".join(candidate.queries))
    if candidate.include_hits:
        why_bits.append("include=" + ", ".join(candidate.include_hits))
    if candidate.exclude_hits:
        why_bits.append("exclude=" + ", ".join(candidate.exclude_hits))
    if why_bits:
        extra_lines.append("  Why: " + " | ".join(why_bits))
    return "\n".join([line] + extra_lines)


def build_report(
    topic: str,
    queries: list[str],
    include_keywords: list[str],
    exclude_keywords: list[str],
    candidates: list[Candidate],
    raw_records: int,
    errors: list[str],
    downloaded_count: int,
    note_stub_count: int,
    pending_updated: bool,
    vault: Path | None,
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    groups = {
        name: [candidate for candidate in candidates if candidate.classification == name]
        for name in ("core", "bridge", "low-confidence", "existing")
    }
    lines = [
        "---",
        "tags:",
        "  - paper-harvest",
        "  - knowledge-base",
        f"generated: {generated_at}",
        "---",
        "",
        f"# {topic} Harvest Report",
        "",
        "## Summary",
        "",
        f"- Seed queries: {', '.join(queries)}",
        f"- Include keywords: {', '.join(include_keywords) if include_keywords else 'none'}",
        f"- Exclude keywords: {', '.join(exclude_keywords) if exclude_keywords else 'none'}",
        f"- Raw source records: {raw_records}",
        f"- Merged candidates: {len(candidates)}",
        f"- Core: {len(groups['core'])}",
        f"- Bridge: {len(groups['bridge'])}",
        f"- Low-confidence: {len(groups['low-confidence'])}",
        f"- Existing in vault: {len(groups['existing'])}",
        f"- PDFs downloaded this run: {downloaded_count}",
        f"- Triage note stubs created this run: {note_stub_count}",
        f"- Pending page updated: {'yes' if pending_updated else 'no'}",
        "",
    ]
    if errors:
        lines += ["## Source Errors", ""] + [f"- {error}" for error in errors] + [""]
    for group_name, heading in (
        ("core", "Core Candidates"),
        ("bridge", "Bridge Candidates"),
        ("low-confidence", "Low-confidence Candidates"),
        ("existing", "Already in Vault"),
    ):
        lines += [f"## {heading}", ""]
        group = sorted(groups[group_name], key=lambda item: (-item.final_score, item.title.lower()))
        if not group:
            lines.append("- none")
        else:
            for candidate in group:
                lines.append(format_candidate_line(candidate, vault))
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_pending_block(candidates: list[Candidate], vault: Path) -> str:
    local_items = [
        candidate
        for candidate in candidates
        if candidate.classification in {"core", "bridge"} and candidate.local_pdf
    ]
    online_items = [
        candidate
        for candidate in candidates
        if candidate.classification == "core" and not candidate.local_pdf
    ]
    bridge_items = [
        candidate
        for candidate in candidates
        if candidate.classification == "bridge" and not candidate.local_pdf
    ]

    def emit_section(title: str, items: list[Candidate]) -> list[str]:
        block = [f"### {title}", ""]
        if not items:
            block.append("- 待补")
            block.append("")
            return block
        for candidate in sorted(items, key=lambda item: (-item.final_score, item.title.lower())):
            block.append(format_candidate_line(candidate, vault))
            block.append("")
        return block

    lines = [
        f"> Last refreshed: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "> Managed by `scripts/harvest_topic_papers.py`. Safe to overwrite by rerunning the harvest.",
        "",
    ]
    lines += emit_section("本地已下载但未入库", local_items)
    lines += emit_section("线上已确认但未下载", online_items)
    lines += emit_section("扩展参考（暂不进主线）", bridge_items)
    return "\n".join(lines).rstrip()


def upsert_pending_block(path: Path, block: str) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    managed = f"{AUTO_BLOCK_START}\n{block}\n{AUTO_BLOCK_END}"
    if AUTO_BLOCK_START in content and AUTO_BLOCK_END in content:
        updated = re.sub(
            re.escape(AUTO_BLOCK_START) + r".*?" + re.escape(AUTO_BLOCK_END),
            managed,
            content,
            flags=re.DOTALL,
        )
    else:
        updated = content.rstrip() + "\n\n## 自动检索候选\n\n" + managed + "\n"
    path.write_text(updated, encoding="utf-8")
    return True


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(text: str | None) -> str:
    text = clean_text(text).lower()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub("[_\\-/\\u2013\\u2014]+", " ", text)
    text = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_title(text: str | None) -> str:
    return normalize_text(text)


def slugify(text: str) -> str:
    text = normalize_text(text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "topic"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    queries = unique_preserve(args.query or [args.topic])
    sources = args.source or list(SOURCE_CHOICES)
    vault = Path(args.vault).expanduser().resolve() if args.vault else None
    notes_folder, triage_folder = resolve_note_folders(vault, args.prefix, args.notes_folder, args.triage_folder)
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else None
    if out_dir is None:
        if vault:
            out_dir = vault / "assets" / "paper_search" / "reports"
        else:
            out_dir = Path.cwd() / "paper_search_reports"
    manifest_dir = out_dir.parent / "manifests" if out_dir.name == "reports" else out_dir
    topic_slug = slugify(args.topic)
    manifest_path = manifest_dir / f"{topic_slug}-harvest-manifest.json"
    report_path = out_dir / f"{topic_slug}-harvest-report.md"
    should_download_pdfs = False
    if not args.skip_pdf_download:
        should_download_pdfs = bool(args.download_pdfs or args.pdf_dir or vault)

    pdf_dir = None
    if should_download_pdfs:
        if args.pdf_dir:
            pdf_dir = Path(args.pdf_dir).expanduser().resolve()
        elif vault:
            pdf_dir = vault / "assets" / "paper_pdfs" / "待处理"
        else:
            pdf_dir = out_dir / "pdfs"

    session = build_session(args.mailto)
    errors: list[str] = []
    raw_records: list[SourceRecord] = []
    source_counts: dict[str, int] = {}
    for source in sources:
        for query in queries:
            try:
                if source == "arxiv":
                    records = fetch_arxiv(session, query, args.max_per_query)
                elif source == "dblp":
                    records = fetch_dblp(session, query, args.max_per_query)
                else:
                    records = fetch_crossref(session, query, args.max_per_query, args.mailto)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{source}:{query} -> {exc}")
                continue
            records = filter_records_by_year(records, args.year_from, args.year_to)
            raw_records.extend(records)
            source_counts[source] = source_counts.get(source, 0) + len(records)

    candidates = merge_candidates(raw_records)
    vault_scan = scan_existing_vault(vault)
    classify_candidates(candidates, args.include_keyword, args.exclude_keyword, vault_scan)

    downloaded_count = 0
    if pdf_dir is not None:
        downloaded_count = download_candidate_pdfs(session, candidates, pdf_dir, args.max_downloads)

    note_stub_count = 0
    if vault and args.prefix and triage_folder and not args.skip_note_stubs:
        for candidate in candidates:
            if ensure_note_stub(candidate, vault, args.prefix, triage_folder):
                note_stub_count += 1

    pending_updated = False
    if vault and args.prefix:
        pending_path = vault / f"{args.prefix}-待处理清单.md"
        pending_updated = upsert_pending_block(pending_path, build_pending_block(candidates, vault))

    candidates.sort(key=lambda item: (item.classification, -item.final_score, item.title.lower()))
    manifest_payload = {
        "topic": args.topic,
        "queries": queries,
        "include_keywords": args.include_keyword,
        "exclude_keywords": args.exclude_keyword,
        "sources": sources,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_record_count": len(raw_records),
        "source_counts": source_counts,
        "pending_updated": pending_updated,
        "downloaded_count": downloaded_count,
        "note_stub_count": note_stub_count,
        "notes_folder": notes_folder,
        "triage_folder": triage_folder,
        "errors": errors,
        "candidates": [asdict(candidate) for candidate in candidates],
    }
    report_text = build_report(
        topic=args.topic,
        queries=queries,
        include_keywords=args.include_keyword,
        exclude_keywords=args.exclude_keyword,
        candidates=candidates,
        raw_records=len(raw_records),
        errors=errors,
        downloaded_count=downloaded_count,
        note_stub_count=note_stub_count,
        pending_updated=pending_updated,
        vault=vault,
    )
    write_json(manifest_path, manifest_payload)
    write_text(report_path, report_text)

    print(f"Manifest: {manifest_path}")
    print(f"Report: {report_path}")
    if pdf_dir is not None:
        print(f"PDF directory: {pdf_dir}")
    if triage_folder:
        print(f"Triage note folder: {triage_folder}")
    print(f"NoteStubs={note_stub_count}")
    print(f"Core={sum(1 for item in candidates if item.classification == 'core')}")
    print(f"Bridge={sum(1 for item in candidates if item.classification == 'bridge')}")
    print(f"LowConfidence={sum(1 for item in candidates if item.classification == 'low-confidence')}")
    print(f"Existing={sum(1 for item in candidates if item.classification == 'existing')}")
    print(f"PendingUpdated={'yes' if pending_updated else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

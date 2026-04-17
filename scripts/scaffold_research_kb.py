#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import sys


INVALID_PATH_CHARS = '<>:"/\\|?*'
DEFAULT_TRACKS = [
    ("core", "核心主线"),
    ("bridge", "桥接问题"),
    ("application", "应用与扩展"),
]


@dataclass(frozen=True)
class Track:
    slug: str
    title: str

    @property
    def filename(self) -> str:
        return f"{self.slug}-子任务清单.md"

    @property
    def page_name(self) -> str:
        return f"{self.slug}-子任务清单"


def safe_fragment(text: str) -> str:
    text = text.strip()
    text = re.sub(f"[{re.escape(INVALID_PATH_CHARS)}]", "-", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "untitled"


def parse_track(raw: str) -> Track:
    if "|" in raw:
        slug, title = raw.split("|", 1)
    elif ":" in raw:
        slug, title = raw.split(":", 1)
    else:
        slug, title = raw, raw
    return Track(slug=safe_fragment(slug), title=title.strip() or safe_fragment(slug))


def choose_tracks(raw_tracks: list[str]) -> list[Track]:
    if not raw_tracks:
        return [Track(slug=s, title=t) for s, t in DEFAULT_TRACKS]
    tracks: list[Track] = []
    seen: set[str] = set()
    for item in raw_tracks:
        track = parse_track(item)
        if track.slug in seen:
            continue
        seen.add(track.slug)
        tracks.append(track)
    return tracks


def ensure_dir(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str, force: bool, dry_run: bool) -> str:
    existed = path.exists()
    if existed and not force:
        return "skipped"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return "updated" if existed else "created"


def write_json(path: Path, payload: object, force: bool, dry_run: bool) -> str:
    existed = path.exists()
    if existed and not force:
        return "skipped"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return "updated" if existed else "created"


def join_links(items: list[tuple[str, str]]) -> str:
    return "、".join(f"[[{name}|{label}]]" for name, label in items) if items else "待补"


def build_index(prefix: str, title: str, notes_folder: str, tracks: list[Track]) -> str:
    track_links = [(f"{prefix}-{track.page_name}", track.title) for track in tracks]
    lines = [
        "---",
        "tags:",
        "  - index",
        f"  - {prefix}",
        "  - knowledge-base",
        "---",
        "",
        f"# {title} 总索引",
        "",
        "> 这个页面负责知识库导航，不负责堆积原始阅读记录。",
        "",
        "## 快速入口",
        "",
        f"- 子任务：{join_links(track_links)}",
        f"- 浏览与回看：[[{prefix}-知识库浏览器|知识库浏览器]]、[[{prefix}-待处理清单|待处理清单]]、[[{prefix}-模板化扫描清单|模板化扫描清单]]、[[{prefix}-不相关条目|不相关条目]]",
        f"- 主笔记目录：`{notes_folder}/`",
        "",
        "## 使用规则",
        "",
        f"- 成熟笔记统一放在 `{notes_folder}/`。",
        "- 每篇成熟笔记统一采用同一章节骨架：背景、动机、方法总览、方法拆解、核心公式、实验与结果、结论、证据边界等。",
        "- 新增条目先进入待处理清单，再决定是否进入核心、桥接或不相关状态。",
        "",
        "## 按任务入口",
        "",
    ]
    for track in tracks:
        lines.append(f"- [[{prefix}-{track.page_name}|{track.title}]]：待补代表论文与阅读路径。")
    lines += [
        "",
        "## 推荐阅读路径",
        "",
        "1. 先从每个子任务页的 `核心主线` 开始。",
        "2. 再回到总索引整合不同子任务之间的关系。",
        "3. 最后用知识库浏览器按年份、类别、方法标签重新切片。",
        "",
        "## 完整年度索引",
        "",
        f"## {date.today().year}",
        "",
        "- 待补",
        "",
    ]
    return "\n".join(lines)


def build_track_page(prefix: str, track: Track) -> str:
    return "\n".join(
        [
            "---",
            "tags:",
            "  - index",
            f"  - {prefix}",
            f"  - {track.slug}",
            "---",
            "",
            f"# {track.title} 子任务清单 [[{prefix}-索引|返回总索引]]",
            "",
            "> 纯索引页，只保留该子任务的分组、入口和待补清单。",
            "",
            "## 快速入口",
            "",
            "- 代表论文：待补",
            "- 桥接 / 强相关：待补",
            "",
            "## 推荐阅读路径",
            "",
            "1. 待补",
            "",
            "## 核心主线",
            "",
            "- 待补",
            "",
            "## 桥接 / 强相关",
            "",
            "- 待补",
            "",
            "## 待补条目",
            "",
            "- 待补",
            "",
        ]
    )


def build_pending(prefix: str, title: str, notes_folder: str) -> str:
    return "\n".join(
        [
            "---",
            "tags:",
            "  - index",
            f"  - {prefix}",
            "  - pending",
            "---",
            "",
            f"# {title} 待处理清单",
            f"[[{prefix}-索引|返回总索引]]",
            "",
            "## 说明",
            "",
            f"- 这里列出尚未并入 `[[{prefix}-索引]]` 的候选条目。",
            f"- 成熟笔记完成后，统一归入 `{notes_folder}/`。",
            f"- 自动检索候选会优先回填已有笔记；如果还没有笔记，会自动生成可内嵌 PDF 的待处理笔记草稿。",
            "- 本地附件如果采用状态桶，建议先放 `assets/paper_pdfs/待处理`，完成后移入 `assets/paper_pdfs/已入库`。",
            "- 明确不进入主线的条目，移入 `assets/paper_pdfs/不相关`，并登记到 `不相关条目` 页面。",
            "",
            "## 自动检索候选",
            "",
            "> 由 `scripts/harvest_topic_papers.py` 维护，可重复运行覆盖。",
            "",
            "<!-- AUTO-HARVEST:START -->",
            "- 待补",
            "<!-- AUTO-HARVEST:END -->",
            "",
            "## 本地已下载但未入库",
            "",
            "- 待补",
            "",
            "## 线上已确认但未下载",
            "",
            "- 待补",
            "",
            "## 扩展参考（暂不进主线）",
            "",
            "- 待补",
            "",
        ]
    )


def build_excluded(prefix: str, title: str) -> str:
    return "\n".join(
        [
            "---",
            "tags:",
            "  - index",
            f"  - {prefix}",
            "  - excluded",
            "---",
            "",
            f"# {title} 不相关条目",
            f"[[{prefix}-索引|返回总索引]]",
            "",
            "## 说明",
            "",
            "- 这里记录明确不进入主线知识库的条目，避免后续重复搜集和重复判断。",
            "- 条目可以是不相关、过度偏题、证据不足，或只适合放在扩展背景中的工作。",
            "",
            "## 条目清单",
            "",
            "- 待补",
            "",
        ]
    )


def build_audit(prefix: str, title: str) -> str:
    today = date.today().isoformat()
    return "\n".join(
        [
            "---",
            "tags:",
            f"  - {prefix}",
            "  - audit",
            "  - template-cleanup",
            "---",
            f"# {title} 模板化扫描清单",
            "",
            f"> 扫描时间：{today}",
            "> 判定标准：是否保留通用模板句、是否仍有结果表占位、是否仍缺关键图、是否存在元数据异常。",
            "",
            "## 已确认基本达标",
            "",
            "- 待补",
            "",
            "## 高风险仍模板化",
            "",
            "- 待补",
            "",
            "## 中度疑似模板化",
            "",
            "- 待补",
            "",
            "## 待复核",
            "",
            "- 待补",
            "",
            "## 当前建议的清理顺序",
            "",
            "1. 先清高风险模板化条目。",
            "2. 再清中度疑似条目。",
            "3. 最后补复核项与元数据异常。",
            "",
            "## 备注",
            "",
            "- 这份清单是质量控制页面，不是学术价值排序页面。",
            "",
        ]
    )


def build_browser_page(prefix: str, title: str) -> str:
    return "\n".join(
        [
            "---",
            "tags:",
            "  - index",
            f"  - {prefix}",
            "  - bases",
            f"updated: {date.today().isoformat()}",
            "---",
            "",
            f"# {title} 知识库浏览器",
            "",
            f"[[{prefix}-索引|返回总索引]]",
            "",
            "## 说明",
            "",
            "- 这个页面使用 Obsidian 自带的 `Bases`。",
            "- 它不替代总索引，而是补上筛选、分组、局部检索和换视图浏览这一层。",
            "- 适合做近两年筛选、方法标签 regroup、快速回看和最近更新检查。",
            "",
            f"![[{prefix}-知识库浏览器.base|no-toolbar]]",
            "",
        ]
    )


def build_browser_base(notes_folder: str) -> str:
    return "\n".join(
        [
            "filters:",
            "  and:",
            "    - file.ext == \"md\"",
            f"    - file.inFolder(\"{notes_folder}\")",
            "    - file.hasTag(\"paper-note\")",
            "formulas:",
            "  paper: file.asLink(title)",
            "  methods: file.tags.filter(value.startsWith(\"method-\")).sort().join(\", \")",
            "  task_tags: file.tags.filter(value.startsWith(\"task-\")).sort().join(\", \")",
            "  recently_updated: if(file.mtime > now() - \"30d\", \"近 30 天\", \"更早\")",
            "properties:",
            "  formula.paper:",
            "    displayName: 条目",
            "  year:",
            "    displayName: 年份",
            "  tier:",
            "    displayName: 层级",
            "  venue:",
            "    displayName: 来源",
            "  subtype:",
            "    displayName: 任务",
            "  category:",
            "    displayName: 分类",
            "  formula.task_tags:",
            "    displayName: 任务标签",
            "  formula.methods:",
            "    displayName: 方法标签",
            "  file.mtime:",
            "    displayName: 修改时间",
            "  formula.recently_updated:",
            "    displayName: 最近更新",
            "views:",
            "  - type: table",
            "    name: 全部条目",
            "    groupBy:",
            "      property: year",
            "      direction: DESC",
            "    order:",
            "      - formula.paper",
            "      - tier",
            "      - venue",
            "      - subtype",
            "      - category",
            "      - formula.methods",
            "      - file.mtime",
            "  - type: table",
            "    name: 最近更新",
            "    groupBy:",
            "      property: formula.recently_updated",
            "      direction: ASC",
            "    order:",
            "      - formula.paper",
            "      - year",
            "      - category",
            "      - formula.methods",
            "      - file.mtime",
            "  - type: cards",
            "    name: 按分类浏览",
            "    groupBy:",
            "      property: category",
            "      direction: ASC",
            "    order:",
            "      - formula.paper",
            "      - year",
            "      - tier",
            "      - formula.task_tags",
            "      - formula.methods",
            "    limit: 24",
            "",
        ]
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold a layered research knowledge base in an Obsidian vault.")
    parser.add_argument("--vault", required=True, help="Target vault or workspace path.")
    parser.add_argument("--prefix", required=True, help="Short file prefix, for example ltvr or mmmissing.")
    parser.add_argument("--title", required=True, help="Human-readable topic title used in page headings.")
    parser.add_argument("--notes-folder", help="Optional override for the canonical notes folder name.")
    parser.add_argument(
        "--track",
        action="append",
        default=[],
        help="Track definition, for example core|核心主线. Repeat to add more tracks.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without writing files.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    vault = Path(args.vault).expanduser().resolve()
    prefix = safe_fragment(args.prefix)
    title = args.title.strip()
    if not title:
        raise SystemExit("--title cannot be empty")

    tracks = choose_tracks(args.track)
    notes_folder = args.notes_folder.strip() if args.notes_folder else f"{prefix}-{title}"
    triage_folder = f"{notes_folder}-待处理"

    print(f"Vault: {vault}")
    print(f"Prefix: {prefix}")
    print(f"Title: {title}")
    print(f"Notes folder: {notes_folder}")
    print(f"Triage folder: {triage_folder}")
    print("Tracks:")
    for track in tracks:
        print(f"  - {track.slug}: {track.title}")

    ensure_dir(vault / notes_folder, args.dry_run)
    ensure_dir(vault / triage_folder, args.dry_run)
    ensure_dir(vault / "assets" / "paper_pdfs" / "已入库", args.dry_run)
    ensure_dir(vault / "assets" / "paper_pdfs" / "待处理", args.dry_run)
    ensure_dir(vault / "assets" / "paper_pdfs" / "不相关", args.dry_run)
    ensure_dir(vault / "assets" / "paper_figures" / "已入库", args.dry_run)
    ensure_dir(vault / "assets" / "paper_figures" / "待处理", args.dry_run)
    ensure_dir(vault / "assets" / "paper_figures" / "不相关", args.dry_run)
    ensure_dir(vault / "assets" / "paper_search" / "configs", args.dry_run)
    ensure_dir(vault / "assets" / "paper_search" / "manifests", args.dry_run)
    ensure_dir(vault / "assets" / "paper_search" / "reports", args.dry_run)

    results: list[tuple[Path, str]] = []
    files = [
        (vault / f"{prefix}-索引.md", build_index(prefix, title, notes_folder, tracks)),
        (vault / f"{prefix}-待处理清单.md", build_pending(prefix, title, notes_folder)),
        (vault / f"{prefix}-不相关条目.md", build_excluded(prefix, title)),
        (vault / f"{prefix}-模板化扫描清单.md", build_audit(prefix, title)),
        (vault / f"{prefix}-知识库浏览器.md", build_browser_page(prefix, title)),
        (vault / f"{prefix}-知识库浏览器.base", build_browser_base(notes_folder)),
    ]
    for track in tracks:
        files.append((vault / f"{prefix}-{track.filename}", build_track_page(prefix, track)))

    for path, text in files:
        status = write_text(path, text, force=args.force, dry_run=args.dry_run)
        results.append((path, status))

    config_path = vault / "assets" / "paper_search" / "configs" / f"{prefix}-kb-config.json"
    config_payload = {
        "prefix": prefix,
        "title": title,
        "notes_folder": notes_folder,
        "triage_folder": triage_folder,
        "updated": date.today().isoformat(),
    }
    results.append((config_path, write_json(config_path, config_payload, force=args.force, dry_run=args.dry_run)))

    print("")
    for path, status in results:
        print(f"{status:>7}  {path}")

    if args.dry_run:
        print("\nDry run only. No files were written.")
    else:
        print("\nScaffold complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

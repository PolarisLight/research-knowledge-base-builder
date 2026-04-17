---
name: research-knowledge-base-builder
description: "Build and maintain a topic/domain research knowledge base in an Obsidian vault using CYH's layered workflow: first harvest candidate papers from the web (for example arXiv, DBLP, and Crossref), then scaffold one canonical notes folder, one main index, one page per research track, a pending queue, an exclusion list, an audit page, a browser/base view, standardized paper-note structure, and tight method-figure / results-table crops from PDFs. Use when Codex needs to start a new literature knowledge base, port the current LTVR workflow to another field, refactor a flat paper collection into a structured vault, or keep notes, web-discovered papers, PDFs, figures, screenshot crops, and Zotero-ready metadata aligned."
---

# Research Knowledge Base Builder

Use this skill when the user wants a reusable knowledge-base method, not just one more paper note.

## Quick Start

1. Run `scripts/harvest_topic_papers.py` with `2-6` seed queries to collect candidate papers from the web.
2. Define the boundary from the harvested set: `in scope`, `near scope`, `out of scope`.
3. Decide `2-6` research tracks based on how the user will read, compare, or write about the field.
4. Run `scripts/scaffold_research_kb.py` to create the layered vault skeleton.
5. Download reachable PDFs into the pending bucket before promoting papers into canonical notes.
6. Use `references/templates.md` when writing or rewriting canonical note pages.
7. Run `scripts/extract_paper_key_regions.py` when a mature note needs a method figure or a main results table crop.
8. Keep the main index, track pages, pending queue, browser view, and audit page in sync as the vault grows.

## What This Pattern Preserves

Preserve the current project's layered structure instead of dumping papers into a single folder.

- One canonical notes folder per topic
- One main index for storyline and navigation
- One track page per subproblem
- One pending queue for intake and triage
- One exclusion list for out-of-scope material
- One audit page for template rot and rewrite backlog
- One browser/base view for filtering and regrouping
- Tight method-figure and results-table crops instead of full-page screenshots
- Shared PDF and figure buckets when the vault stores local attachments
- Repeatable web-harvest manifests and reports instead of ad hoc search sessions

This works because discovery, intake, analysis, retrieval, navigation, and quality control live in different files.

## Workflow

### 1. Harvest candidate papers from the web first

Do not wait for a local PDF collection before starting a new field.

Use `scripts/harvest_topic_papers.py` to:

- search multiple web sources such as `arXiv`, `DBLP`, and `Crossref`
- merge duplicates by DOI or normalized title
- compare hits against the current vault
- classify candidates into `core`, `bridge`, `low-confidence`, and `existing`
- download directly reachable PDFs into the pending bucket by default when a vault is provided
- connect each kept paper to a note page by reusing an existing note or creating a triage note with an inline PDF embed
- generate a JSON manifest plus a Markdown report

Example:

```bash
python /path/to/harvest_topic_papers.py \
  --topic "long-tailed visual recognition" \
  --query "long-tailed visual recognition" \
  --query "long tail recognition" \
  --query "class imbalance recognition" \
  --exclude-keyword "facial expression" \
  --vault "/path/to/vault" \
  --prefix "ltvr"
```

Default rules:

- use `2-6` seed queries, not one huge query blob
- prefer broad-but-legible queries over venue names
- when `--vault` is provided, treat PDF download as part of the default intake path; use `--skip-pdf-download` only when the user explicitly wants metadata-only harvest
- review the generated `core` and `bridge` blocks before promoting anything into canonical notes
- treat `low-confidence` results as triage material, not as final exclusions
- never claim the harvest is literally complete; it is a repeatable coverage pass

### 2. Define the boundary from the harvested set

Write three short lists before promoting papers:

- In scope: what belongs in the core knowledge base
- Near scope: what counts as bridge / related work
- Out of scope: what should stay outside the main line

The harvest should sharpen the boundary, not replace it.

### 3. Split by research question, not by venue

Create tracks from how the user reasons about the field, for example:

- main task line
- adjacent task line
- generation / deployment / evaluation branch
- application or domain-specific branch

A good track page should answer "what should I read next for this subproblem?" without scanning the whole vault.

### 4. Scaffold the vault

If the user provides a vault path, a prefix, a title, and optional tracks, run the scaffolder:

```bash
python /path/to/scaffold_research_kb.py \
  --vault "/path/to/vault" \
  --prefix "mmmissing" \
  --title "Missing Modality Learning" \
  --track "core|Core Line" \
  --track "bridge|Bridge Questions"
```

Use the script by default for new knowledge bases. Hand-build the files only when the vault already exists and needs a careful merge.

### 5. Normalize note structure at two depths

Do not treat every note as if it has the same maturity.

Use two levels on purpose:

- `triage / pending`: enough to remember why the paper is in the queue
- `canonical / mature`: deep enough that the user can understand what the paper actually does without reopening the PDF

The stable skeleton lives in `references/templates.md`.

Keep the frontmatter machine-readable. The browser view and any future automation assume fields such as:

- `title`
- `year`
- `venue`
- `tier`
- `subtype`
- `category`
- `official_url`
- `doi`
- `tags`
- `reading_status`
- `evidence_level`
- `one_sentence`

Default rule:

- do not move a paper into the canonical notes folder unless the note already answers the core questions: `what problem`, `why prior work is insufficient`, `what the method actually changes`, `how training / inference works`, `what evidence is strongest`, and `what the real limitation is`
- even a triage note should let the user directly open the paper inside the note via an inline PDF embed when a local PDF exists

### 6. Extract key method and results visuals

Treat screenshot extraction as part of note normalization, not as an optional afterthought.

When a mature note needs a framework image or a main comparison table:

- run `scripts/extract_paper_key_regions.py`
- keep the method figure and results table as separate artifacts
- reject crops that are close to full-page screenshots

Example:

```bash
python /path/to/extract_paper_key_regions.py \
  --pdf "/path/to/paper.pdf" \
  --out-dir "/path/to/assets/paper_figures/已入库"
```

Default rules:

- prefer the main method figure from early pages
- prefer the main comparison table from experiment pages
- if a crop uses more than about `70%` of the page area, treat it as low confidence
- if automatic detection stays low confidence, switch to manual bounding boxes instead of accepting a full page render

### 7. Separate intake state from canonical state

Do not mix `discovered`, `downloaded`, `read`, `promoted`, and `irrelevant` into one list.

Use the pending queue for papers that are:

- harvested from the web but not yet downloaded
- downloaded but not fully written up
- useful as extended context but not part of the core line

If the vault uses attachment buckets, prefer:

- `assets/paper_pdfs/已入库`
- `assets/paper_pdfs/待处理`
- `assets/paper_pdfs/不相关`
- `assets/paper_figures/已入库`
- `assets/paper_figures/待处理`
- `assets/paper_figures/不相关`
- `assets/paper_search/manifests`
- `assets/paper_search/reports`

### 8. Keep two navigation layers

Maintain both:

- a curated main index for reading order and storyline
- a browser/base view for filtering, grouping, and quick retrieval

The main index is for judgment. The browser is for search and re-slicing.

### 9. Audit note quality explicitly

Use the audit page to track:

- obviously templated notes
- notes missing a method explanation that a human can retell
- notes missing figures or core results
- metadata anomalies
- notes that still need a full rewrite

Do not rely on memory for cleanup. The audit page is part of the method.

## Operating Rules

- Prefer one canonical notes folder per topic instead of multiple partially overlapping note folders.
- Prefer track pages with `核心主线`, `桥接 / 强相关`, and `待补条目` sections over unstructured reading dumps.
- Preserve an explicit `evidence boundary and next verification` section in mature notes so later sessions know what is solid and what still needs full-text verification.
- Use tags to capture both task track and method family; this makes the browser useful later.
- Do not confuse a triage note with a mature note. Pending notes can stay light; canonical notes cannot.
- Do not accept near-full-page PDF renders as final key visuals. If the crop is not tight, mark it low confidence and redo it.
- When converting an existing flat collection, harvest and de-duplicate first, normalize a representative batch second, rebuild the main index third, then sweep the rest.
- When a page is mostly placeholder prose, log it in the audit page instead of pretending it is finished.
- When the user asks to start a new field from the web, run the harvest step before asking for local PDFs.
- Do not write canonical notes from harvest-only metadata when a reachable PDF could have been downloaded first.
- A mature note should let the user explain the paper to another person in `2-3` minutes without reopening the PDF.

## Read These References Only When Needed

- Read `references/method.md` for the full design rationale, file roles, track heuristics, and maintenance loop.
- Read `references/web-harvest.md` when the task starts from web discovery instead of a local PDF pile.
- Read `references/templates.md` for the canonical paper-note skeleton, track page template, and quality checklist.
- Read `references/figure-cropping.md` when the task includes extracting method figures or results table crops from PDFs.

# Web Harvest for Research KBs

## Goal

Use web harvest when the user wants to start a knowledge base from a topic definition instead of from an existing local PDF folder.

The first pass should answer:

- what the candidate paper pool looks like
- which items are obviously core
- which items are bridge / related work
- which items are already in the vault
- which items still need PDF download or manual review

## What the Harvester Does

`scripts/harvest_topic_papers.py` is a multi-source intake script.

It currently:

- queries `arXiv`, `DBLP`, and `Crossref`
- merges duplicates by DOI or normalized title
- filters by year if requested
- scores each candidate against the supplied seed queries
- applies optional include / exclude keywords
- checks whether the paper already exists in the target vault
- downloads directly reachable PDFs into a pending bucket by default when `--vault` or `--pdf-dir` is provided
- reuses an existing note or creates a triage note stub so the paper is directly viewable from a note page
- writes a JSON manifest and a Markdown report
- updates the managed auto-harvest block in the pending page when `--vault` and `--prefix` point at an existing scaffolded KB

## Query Design

Prefer `2-6` seed queries.

Good patterns:

- task name
- alternate wording of the task
- adjacent wording the field actually uses
- one bridge query for the strongest neighboring area

Bad patterns:

- giant query dumps with ten unrelated phrases
- venue names without task wording
- overly generic words such as `deep learning` or `foundation model`

Suggested pattern:

```bash
python /path/to/harvest_topic_papers.py \
  --topic "long-tailed visual recognition" \
  --query "long-tailed visual recognition" \
  --query "long tail recognition" \
  --query "class imbalance recognition" \
  --include-keyword "long-tailed" \
  --include-keyword "class imbalance" \
  --exclude-keyword "facial expression" \
  --vault "/path/to/vault" \
  --prefix "ltvr"
```

## Output Files

The script writes two main artifacts:

- `<topic-slug>-harvest-manifest.json`
- `<topic-slug>-harvest-report.md`

If the vault is scaffolded, prefer storing them in:

- `assets/paper_search/manifests`
- `assets/paper_search/reports`

If PDF download is enabled, prefer:

- `assets/paper_pdfs/待处理`

## Reading the Output

The report groups results into:

- `core`: strong matches that should usually enter the pending queue
- `bridge`: useful but not necessarily main-line papers
- `low-confidence`: weak matches or likely off-topic items that still need judgment
- `existing`: already present in the vault

Do not treat `low-confidence` as a final exclusion list.

The first pass should optimize for recall plus intelligible triage, not for pretending the classifier is perfect.

## Recommended Loop

1. Harvest from the web with `2-6` seed queries.
2. Download reachable PDFs into the pending queue.
3. Reuse existing notes or create triage notes with inline PDF embeds.
4. Review `core` and `bridge` candidates.
5. Refine the field boundary and track list.
6. Scaffold the KB if needed.
7. Promote only the important papers into canonical notes.
8. Re-run harvest after boundary or query changes.

## Limits

- The harvester is a repeatable coverage pass, not a guarantee of literal completeness.
- Publisher pages and metadata services disagree on titles, years, and PDF accessibility; manual review still matters.
- Some sources expose metadata but not a downloadable PDF.
- Use `--skip-pdf-download` only when metadata-only harvest is intentional.
- Domain-specific sources can be added later when the field needs them.

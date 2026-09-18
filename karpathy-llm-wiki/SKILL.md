---
name: karpathy-llm-wiki
description: "Use when building or maintaining a personal LLM-powered knowledge base. Triggers: ingesting sources into a wiki, querying wiki knowledge, linting wiki quality, 'add to wiki', 'what do I know about', or any mention of 'LLM wiki' or 'Karpathy wiki'."
---

# Karpathy LLM Wiki

Build and maintain a personal knowledge base using LLMs. You manage two directories: `raw/` (immutable source material) and `wiki/` (compiled knowledge articles). Sources go into raw/, you compile them into wiki articles, and the wiki compounds over time.

Core ideas from Karpathy:
- "The LLM writes and maintains the wiki; the human reads and asks questions."
- "The wiki is a persistent, compounding artifact."

## Architecture

Three layers, all under the project root (see Project Root below — not necessarily the current working directory):

**raw/** — Immutable source material. You read, never modify. Organized by topic subdirectories (e.g., `raw/machine-learning/`).

**wiki/** — Compiled knowledge articles. You have full ownership. Organized by topic subdirectories, one level only: `wiki/<topic>/<article>.md`. Contains two special files:
- `wiki/index.md` — Global index. One row per article, grouped by topic, with link + summary + Updated date.
- `wiki/log.md` — Append-only operation log.

**SKILL.md** (this file) — Schema layer. Defines structure and workflow rules.

Templates live in `references/` relative to this file. Read them when you need the exact format for raw files, articles, archive pages, or the index.

### Project root

Resolve this first, before Initialization — do not default to the current working directory without checking.

1. Run `claude mcp list` (works from any directory, in any session). Look for an `obsidian-mcp` entry and a `--vault wiki=<path>` argument in its command — that `<path>` is the project root. (This works because the MCP registration is global/user-scope, unlike the working directory of any one session; `raw/` and `wiki/` are still read and written as plain files, never through the MCP server's own tools, which are Markdown-only and deliberately hide host paths.)
2. If `claude mcp list` has no `obsidian-mcp` entry, or no `wiki=` vault in its args, fall back to the current working directory — a dedicated `wiki=` vault isn't guaranteed to be set up on every machine this skill runs on.
3. Having found the root by either path, do all `raw/`/`wiki/` reads and writes against it for the rest of the session — don't re-resolve per operation.

### Initialization

Triggers only on the first Ingest. Check whether `raw/` and `wiki/` exist under the resolved project root. Create only what is missing; never overwrite existing files:

- `raw/` directory (with `.gitkeep`)
- `wiki/` directory (with `.gitkeep`)
- `wiki/index.md` — heading `# Knowledge Base Index`, empty body
- `wiki/log.md` — heading `# Wiki Log`, empty body

If Query or Lint cannot find the wiki structure, tell the user: "Run an ingest first to initialize the wiki." Do not auto-create.

## The Grounding Invariant

Every load-bearing fact in wiki/ — numbers, dates, direct quotes — exists verbatim in the raw/ files linked by that article's Raw field. Compile *establishes* this invariant (locate before you write); lint *verifies* it (`scripts/check_evidence.py` greps the high-signal literals — suffixed or large numbers, decimals, ISO dates, longer quotes — in the linked raws; the compile-time locate-before-write rule covers the rest). Because raw/ is immutable, a verified article stays verified; the script re-checks the whole wiki in seconds, so there is no incremental state to maintain.

---

## Ingest

Fetch a source into raw/, then compile it into wiki/ — unless the source adds nothing new. Always fetch; whether to compile depends on the triage below.

### Fetch (raw/)

1. Get the source content using whatever web or file tools your environment provides. If nothing can reach the source, ask the user to paste it directly.

2. Pick a topic directory. Check existing `raw/` subdirectories first; reuse one if the topic is close enough. Create a new subdirectory only for genuinely distinct topics.

3. Save as `raw/<topic>/YYYY-MM-DD-descriptive-slug.md`.
   - Slug from source title, kebab-case, max 60 characters.
   - Published date unknown → omit the date prefix from the file name (e.g., `descriptive-slug.md`). The metadata Published field still appears; set it to `Unknown`.
   - If a file with the same name already exists, append a numeric suffix (e.g., `descriptive-slug-2.md`).
   - Include metadata header: source URL, collected date, published date.
   - Preserve original text. Clean formatting noise. Do not rewrite opinions.

   See `references/raw-template.md` for the exact format.

4. **Converted sources: archive the original alongside.** If the source was not natively text/markdown and reached raw/.md via a converter (PDF, ODT, or any other format needing one), copy the original file as-is into the same `raw/<topic>/` directory, same base name as the .md (e.g. `descriptive-slug.pdf` next to `descriptive-slug.md`). Do this whether the source came from a local path or a URL — for a URL, archive the exact bytes that were fetched and converted, not a re-fetch. `check_evidence.py` only inspects `.md` files and ignores other extensions, so this never interferes with linting; it exists purely so the exact input to the converter can be re-examined later (re-run the converter, diff its output, check for content a converter dropped or normalized away). Set the raw file's Source field to link to this local copy (see `references/raw-template.md`) in addition to the origin URL/path description.

   Known converters on this system: PDF -> `pdf-ingest` skill (docling); HTML and ODT -> `pandoc-convert` skill (pandoc).

5. **Embedded images: download and archive, don't drop or leave remote.** A source can embed images that carry load-bearing content (schematics, diagrams, plots) rather than decoration — text-only extraction (e.g. a browser's plain-text reading mode) silently loses these with no trace, and even an accessibility-tree read only yields alt text, never the image itself. Before treating a source with embedded images as fully captured:
   - Get real HTML (not just a text/accessibility-tree reading) and convert it with a converter that preserves `<img>` references as markdown image links (pandoc does this).
   - Download every referenced image into `raw/<topic>/` alongside the .md (flat, or an `assets/` subfolder if there are many), and rewrite the markdown's image links to these local relative paths — a remote URL in wiki/ or raw/ will rot.
   - Judge each image on the same terms as prose: purely decorative (logos, banners, spacers) can be skipped; anything a paragraph refers to ("schéma ci-dessous", "figure 3", a table rendered as an image) must be archived.
   - **PDF via docling: `generate_picture_images=True` is required, and it is not `pdf-ingest`'s default.** The shared `convert_pdfs.py` calls `export_to_markdown()` with default options, which emits a bare `<!-- image -->` placeholder for every figure — schematics, pinouts, plots all silently vanish, with no trace that anything was dropped. For an llm-wiki ingestion, convert with `PdfPipelineOptions(generate_picture_images=True)` and export via `document.save_as_markdown(path, artifacts_dir=<assets_dir>, image_mode=ImageRefMode.REFERENCED)` (docling_core) instead — this writes the actual figures as files and links them in the markdown. This produces one image file per detected picture, including repeated logos/headers on every page (same content, different crop hash each time) — view each once and drop the decorative repeats per the judgment rule above before archiving.

### Triage

After saving the raw file and before editing wiki/, search wiki/ with the source's key entities and synonyms, then state the disposition:

- **New** — creates one or more new articles.
- **Update** — merges into existing article(s).
- **Disputed** — contradicts existing content; may combine with New or Update (see Compile for conflict annotation).
- **No material** — adds no knowledge beyond what the wiki already holds. Keep the raw file, log it (see Post-Ingest), and stop. Do not force an article out of a thin source.

New, Update, and Disputed may be combined. No material is exclusive.

### Compile (wiki/)

Determine where the new content belongs:

- **Same core thesis as existing article** → Merge into that article. Add the new source to Sources/Raw. Update affected sections.
- **New concept** → Create a new article in the most relevant topic directory. Name the file after the concept, not the raw file.
- **Spans multiple topics** → Place in the most relevant directory. Add See Also cross-references to related articles elsewhere.

These are not mutually exclusive. A single source may warrant merging into one article while also creating a separate article for a distinct concept it introduces. In all cases, check for factual conflicts: if the new source contradicts existing content, mark the contested claims with a **Status: Disputed** block (see `references/article-template.md`). When the conflicting content lives in separate articles, mark both and cross-link them.

**Source fidelity.** Every number, date, and direct quote must be located in the raw file (grep or read) *before* it is written; write the value exactly as found — if the source says 42K, write 42K, not 42,000. Derived values (sums, deltas, counts you computed) must show their components so each component is findable in raw. If you cannot locate a value, do not write its exact form; drop it or state it without precision.

See `references/article-template.md` for article format. Key points:
- Sources field: author, organization, or publication name + date, semicolon-separated.
- Raw field: markdown links to raw/ files, semicolon-separated.
- Relative paths from `wiki/<topic>/` use `../../raw/<topic>/<file>.md` (two levels up to project root).

### Cascade Updates

After the primary article, check for ripple effects. Do not rely on the index alone: search the full wiki for the source's key entities, aliases, and the claims it touches, then update every non-archive article whose content is materially affected. Each updated file gets its Updated date refreshed.

When the new source supersedes or contradicts an existing claim, keep the old claim for the record but mark it with a Status block (see `references/article-template.md`): **Outdated** when something newer replaces it, **Disputed** when sources disagree. Never silently rewrite history.

Archive pages are never cascade-updated (they are point-in-time snapshots).

### Post-Ingest

Update `wiki/index.md`: add or update entries for every touched article. When adding a new topic section, include a one-line description. The Updated date reflects when the article's knowledge content last changed, not the file system timestamp. See `references/index-template.md` for format.

Append to `wiki/log.md`:

```
## [YYYY-MM-DD] ingest | <primary article title>
- Disposition: <New; Update; Disputed>
- Raw: <raw file path>
- Updated: <cascade-updated article title>
```

Omit `- Updated:` lines when no cascade updates occur. For No material, log and stop. Use a project-root-relative raw path (for example, `raw/topic/file.md`):

```
## [YYYY-MM-DD] ingest | no material: <project-root-relative raw file path>
- Disposition: No material
```

The exact no-material heading is the machine-readable inventory key; the Disposition line remains required for a complete human-readable log entry.

### Research (multi-source ingest)

Use only when the user explicitly asks to research a topic or gather sources into the wiki. Ordinary knowledge questions go to Query, which never writes files.

1. Split the topic into a few angles. For each, search with a wide net — official names, abbreviations, and synonyms, not just the literal keywords.
2. For any core claim you expect to conclude, deliberately search the opposing side: failures, criticism, failed replications.
3. Save selected sources to raw/ as usual. Searching may run in parallel; compilation must not — compile one source at a time, because index.md, log.md, and cascade updates are shared state.

---

## Query

Search the wiki and answer questions. Examples of triggers:
- "What do I know about X?"
- "Summarize everything related to Y"
- "Compare A and B based on my wiki"

### Steps

1. Read `wiki/index.md` to locate candidate articles, then full-text search wiki/ with the topic's key terms *and their synonyms*. Never claim the wiki has no relevant content until both the index and the full-text search come back empty — and say that you searched.
2. Read the articles you found and synthesize an answer.
3. Prefer wiki content over your own training knowledge. Cite sources with markdown links: `[Article Title](wiki/topic/article.md)` (project-root-relative paths for in-conversation citations; within wiki/ files, use paths relative to the current file).
4. Output the answer in the conversation. Do not write files unless asked.

### Archiving

When the user explicitly asks to archive or save the answer to the wiki:

1. Write the answer as a new wiki page. See `references/archive-template.md`. When converting conversation citations to the archive page, rewrite project-root-relative paths (e.g., `wiki/topic/article.md`) to file-relative paths (e.g., `../topic/article.md` or `article.md` for same-directory).
   - Sources: markdown links to the wiki articles cited in the answer.
   - No Raw field (content does not come from raw/).
   - File name reflects the query topic, e.g., `transformer-architectures-overview.md`.
   - Place in the most relevant topic directory.
2. Always create a new page. Never merge into existing articles (archive content is a synthesized answer, not raw material).
3. Update `wiki/index.md`. Prefix the Summary with `[Archived]`.
4. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] query | Archived: <page title>
   ```

---

## Lint

Quality checks on the wiki. Three categories with different authority levels.

### Safe Fixes (auto-fix)

Fix these automatically:

**Index consistency** — compare `wiki/index.md` against actual wiki/ files (excluding index.md and log.md):
- File exists but missing from index → add entry with `(no summary)` placeholder. For Updated, use the article's metadata Updated date if present (for archive pages, the Archived date); otherwise fall back to file's last modified date.
- Index entry points to nonexistent file → mark as `[MISSING]` in the index. Do not delete the entry; let the user decide.
- Index entry's Updated differs from the article's metadata Updated (or Archived, for archive pages) → update the index entry to match the article.

**Internal links** — for every markdown link in wiki/ article files (body text and Sources metadata), excluding Raw field links (validated by Raw references below), excluding See Also section links (handled by the See Also rule below), and excluding index.md/log.md (handled above):
- Target does not exist → search wiki/ for a file with the same name elsewhere.
  - Exactly one match → fix the path.
  - Zero or multiple matches → report to the user.

**Raw references** — every link in a Raw field must point to an existing raw/ file:
- Target does not exist → search raw/ for a file with the same name elsewhere.
  - Exactly one match → fix the path.
  - Zero or multiple matches → report to the user.

**See Also** — within each topic directory:
- Target of a See Also link does not exist → search wiki/ for a file with the same name elsewhere.
  - Exactly one match → fix the path.
  - Zero matches → remove the link (a dead cross-reference is not load-bearing).
  - Multiple matches → report to the user.

### Mechanical Reports (no fixes)

Run these mechanically with `python3 <skill-dir>/scripts/check_evidence.py <project-root>` (optionally followed by project-root-relative article paths to limit scope). Default scope is the whole wiki; the script is fast. Report findings; never auto-fix facts.

**Source fidelity** — reported suspects are candidates, not verdicts: derived values and product names may appear. Judge each against the raw context and report only real mismatches.

**Evidence errors** — articles the script cannot verify (missing Raw field, unresolvable Raw links, or Raw links escaping `raw/`). These always need a decision, not a fix from the script.

**Unreferenced raw files** — files logged with a No material disposition are excluded; everything else is a genuine backlog reminder.

### Judgment Reports (no fixes)

These rely on your judgment. Report findings without auto-fixing:

- Factual contradictions across articles
- Outdated claims superseded by newer sources but still presented without a Status block
- Missing conflict annotations where sources disagree
- Obviously missing cross-references between related articles (suggest them; do not add silently)
- Malformed Status blocks (Outdated missing its date, or either block missing its explanation; format reference: `references/article-template.md`)
- Orphan pages with no inbound links from other wiki articles
- Missing cross-topic references
- Concepts frequently mentioned but lacking a dedicated page
- Archive pages whose cited source articles have been substantially updated since archival

### Post-Lint

Append to `wiki/log.md`:

```
## [YYYY-MM-DD] lint | <N> issues found, <M> auto-fixed
```

---

## Conventions

- Standard markdown with relative links throughout.
- wiki/ supports one level of topic subdirectories only. No deeper nesting.
- Today's date for log entries, Collected dates, and Archived dates. Updated dates reflect when the article's knowledge content last changed. Published dates come from the source (use `Unknown` when unavailable).
- Inside wiki/ files, all markdown links use paths relative to the current file. In conversation output, use project-root-relative paths (e.g., `wiki/topic/article.md`).
- Ingest updates both `wiki/index.md` and `wiki/log.md` (a No material ingest updates only the log). Archive (from Query) updates both. Lint updates `wiki/log.md` (and `wiki/index.md` only when auto-fixing index entries). Plain queries do not write any files.

# llm-wiki-skills

Three [Claude Code Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for building a personal, LLM-maintained knowledge base and feeding it from PDF/HTML/ODT sources.

## Skills

### `karpathy-llm-wiki`

A fork of [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki) (MIT), itself an implementation of [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): the agent maintains two directories, `raw/` (immutable sources) and `wiki/` (compiled, cross-linked knowledge articles), through four operations — ingest, query, lint, and archive.

Changes from upstream:
- **Source archival on conversion** — when a source needs a converter (PDF, ODT, HTML, ...) to reach `raw/*.md`, the original file (and any embedded images the source references) is archived alongside the `.md`, so the exact converter input can be re-examined later. Upstream only kept the converted text.
- **Project-root discovery via MCP** — the project root is no longer assumed to be the current working directory. If an `obsidian-mcp` server is registered with a `--vault wiki=<path>` argument (visible via `claude mcp list` from any directory/session), that path is used; otherwise it falls back to the working directory. This lets the same wiki be reached from a session started anywhere, without hardcoding a path in a memory file.
- Points to the `pandoc-convert` skill below as the known HTML/ODT converter.

### `pandoc-convert`

Convert HTML and ODT documents to Markdown with [pandoc](https://pandoc.org/), including embedded images (`--extract-media` for ODT; HTML `<img>` references need a separate download pass, since pandoc only rewrites the link). Written to complement `karpathy-llm-wiki`'s source-archival rule, but usable standalone.

### `pdf-ingest`

Convert PDF documents to Markdown with [docling](https://github.com/docling-project/docling), including figures (`generate_picture_images` — see `karpathy-llm-wiki`'s note on why this must be set explicitly). Runs each PDF in its own subprocess so page/model memory is released between files instead of accumulating over a batch — useful on memory-constrained machines. The HuggingFace model cache directory is machine-specific and read from a git-ignored `.env` (copy `.env.template` and adjust the path); everything else in the script is portable.

## Install

Copy a skill's folder into `~/.claude/skills/<name>/` (global) or `<project>/.claude/skills/<name>/` (project-scoped).
- `pandoc-convert` assumes a pandoc binary is available; edit the path at the top of its `SKILL.md` to match your system (a portable Windows build works fine, no install required).
- `pdf-ingest` assumes a Python environment with `docling` and `python-dotenv` installed (`pip install docling python-dotenv`); edit the venv/python path in its `SKILL.md`, and copy `.env.template` to `.env` with your own `HF_CACHE_DIR`.

## License

`karpathy-llm-wiki/` keeps its original MIT license (see `karpathy-llm-wiki/LICENSE`) and attribution to Astro-Han. `pandoc-convert/` and `pdf-ingest/` are MIT as well.

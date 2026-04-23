# LLM Wiki Handoff v1

This document is an implementation-oriented companion to [LLM Wiki Architecture](./llm_wiki_architecture.md).

Use the architecture doc as the canonical source for high-level system principles. Use this handoff doc for repo-specific implementation direction and open design questions.

## Goal

Turn the current personal wiki workflow into a true persistent LLM-maintained knowledge base consistent with the architecture document:

- raw notes stay immutable source material
- the wiki becomes the maintained synthesis layer
- new captures are integrated into existing pages, not just indexed for later retrieval
- queries should read from the wiki first, not rediscover facts from raw notes every time

## Current State

The repo already has the core ingredients:

- `raw/` holds immutable source notes
- `wiki/` holds markdown pages and links
- `wiki/index.md` is a navigation layer
- `wiki/log.md` is a chronological audit trail
- `scripts/vault_pipeline.py` performs deterministic capture/export/ingest
- `scripts/bootstrap_wiki.py` can use a model for synthesis and splitting

What this means in practice:

- not every new note requires an LLM call
- some wiki maintenance is rule-based and local
- the model is used for higher-level synthesis work, not as a mandatory step in every ingest

## Desired End State

The wiki should behave like a compounding artifact:

- every new source updates relevant existing pages
- cross-links are added when a relationship is real
- contradictions are flagged instead of overwritten silently
- topic pages emerge only when they compress a real cluster
- the index stays compact and usable as the main navigation surface

## Scope

### In scope

- ingesting new captures from Obsidian into `raw/`
- integrating raw notes into existing wiki pages
- maintaining the index and log
- supporting LLM-assisted synthesis where it adds value
- keeping raw notes immutable

### Out of scope for v1

- replacing all deterministic ingestion with LLM calls
- building a full embedding/RAG search stack
- changing the public/private mirror workflow
- reproducing the Obsidian folder structure in the wiki

## Workflow Contract

### Ingest

When a new note arrives:

1. export it to `raw/`
2. identify the relevant existing wiki pages
3. update or create pages with the new information
4. add meaningful wikilinks
5. append an entry to `log.md`
6. refresh `index.md`

### Query

When answering a question:

1. read `index.md` first
2. inspect the most relevant pages
3. follow one or two tight wikilinks if they add context
4. answer from wiki content, not general memory

### Lint

Periodically check for:

- orphan pages
- duplicated concepts without consolidation
- contradictions between pages
- dead links in sources
- clusters that should become topic pages

## Spec Questions to Resolve

- Which ingest steps must remain deterministic?
- Which steps should be LLM-assisted?
- What page types are mandatory versus optional?
- How should contradictions be represented?
- When should a new source update an existing page versus create a new one?
- What is the minimum useful index format at scale?
- What is the expected human review loop, if any?

## Acceptance Criteria

The design is good enough if:

- a new source can be folded into the wiki without hand-editing multiple pages
- the wiki remains navigable through `index.md`
- the log provides a clear history of ingests and queries
- the system does not require re-deriving the same synthesis on every query
- the workflow still works when LLM calls are unavailable for simple ingests

## Non-Goals

- turning the wiki into a generic RAG system
- auto-generating pages that have no real source grounding
- creating massive summary pages that flatten distinct ideas
- forcing every note into a new page

## Open Questions

- Should the LLM write only synthesis pages, or also maintain atomic notes?
- Should page updates be diff-based, full rewrites, or hybrid?
- Should wiki queries ever write back into the wiki automatically?
- Should bootstrap and ingest share the same synthesis engine?
- What is the right boundary between `raw/` and `wiki/` for each note type?

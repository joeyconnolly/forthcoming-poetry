# Adding the next publisher

Expansion is the next expected use, not a hypothetical redesign. The registry is the source of truth; nothing in the core or frontend enumerates the initial ten.

1. Assign a permanent lowercase publisher ID. Display names and URLs may change; do not recycle IDs.
2. Inspect official discovery and detail pages, pagination, robots and usage terms. Record exact scope and unresolved restrictions. Keep inaccessible publishers registered but disabled with an explanatory status.
3. Add `id`, `name`, `country`, `website`, `adapter`, `enabled`, `access_status`, `sources`, `allowed_hosts`, `coverage`, and `max_requests` to `config/publishers.json`. Source and detail hosts must be explicitly allowed. Do not increase budgets simply to crawl unrelated backlist indefinitely.
4. Reuse a compatible adapter if its DOM contract is actually the same. Otherwise add `def publisher(config, fetch, today) -> Result` in `adapters.py`, then add it to `ADAPTERS`. As this file grows, move each function into its own module and retain the registry; callers do not change.
5. Use `fetch.get(url)` for requests. Return common records with `make_record`; keep evidence specific to title, contributor and release statement. Never use an article's JSON-LD `datePublished` as the book date. Preserve contributor roles where supported. Optional ISBNs are evidence, not the sole work identifier.
6. Increment candidate/excluded counts. Call `result.warn(url, reason)` for malformed cards, incomplete pagination, request failures or uncertain classification. Mark a zero result complete only with evidence the intended source was exhaustively processed.
7. Add minimal representative fixtures and tests for at least one valid title, one excluded/uncertain item, and a changed/empty response. Verify diacritics, pagination and far-future titles.
8. Run `collect --publisher ID`, inspect `data/review.json`, manually compare results with the actual source, then build. Record the checked sample and scope in `SOURCE_STATUS.md`.

## Shared adapter contract

`Result.records` contains validated bibliographic facts; `Result.complete` describes extraction/discovery coverage. A partial source may contribute independently verified records. Adapters do not write files, delete missing books, merge publishers, schedule jobs or render HTML. Those responsibilities remain shared.

The same adapter can serve several registry entries when configured sources share a structure. The same publisher can use several sources. For more complex sources, compose discovery and detail helpers inside that adapter rather than coupling publishers together.

## What scales without changes

- Registry-driven filters, counts, coverage and ordering.
- Per-publisher failure isolation, request budgets and cache directories.
- Incremental targeted collection via repeated `--publisher` arguments.
- Stable source identity, content-based aliases, first observation dates and change history.
- JSON schema version and explicit rejection of unsupported versions.

## When to change the implementation

The initial collector runs publishers sequentially. With dozens of sources, introduce bounded concurrency **between hosts**, preserving per-host throttling and serial reconciliation. With a much larger observation history, migrate the versioned JSON state to SQLite behind the storage functions. Neither requires changing adapters or the static page contract. Before adding many large catalogues, add detail-refresh policies for already-published books and durable discovery checkpoints; avoid arbitrary truncation labelled as complete.

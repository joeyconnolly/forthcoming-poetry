# Expansion validation, 9 November 2026

36 offline checks passed for the expanded collector. The local reviewed build has 87 forthcoming titles across 21 publishers. See [COVERAGE_EXPANSION.md](COVERAGE_EXPANSION.md) for the current scope. The original validation notes below are retained as historical evidence. GitHub Pages deployment was already verified for the first prototype; the expansion also passed collection, durable saving and publication in GitHub Actions run 42648509072.

# Validation and remaining work

## Verified locally, 9 November 2026

- Live publisher requests populated the dataset; no sample records are used in the public calendar.
- All ten publishers are registered; five have active adapters and five explicit access/reuse holds.
- Three configured source scopes processed without outstanding extraction warnings: Bloodaxe, Nine Arches, Seren. Shearsman has editorial review cases; Gallery rolling-feed coverage remains partial.
- Offline tests cover all five publishers, date precision/boundaries, split ordinals, format aliases, conflicting dates, source failures, suspicious empty results, stable updates, corrections, missing observations, file locking, robots checks, allowed hosts and conditional caches.
- Desktop and 390px mobile layout inspected in browser. Mobile horizontal page overflow corrected. Search, publisher filtering and no-results state tested. Labels, headings, source links and source-status table inspected through browser accessibility state.
- Source evidence and contributor diacritics are retained. Public text is HTML-escaped; no publisher descriptions, poems, covers or prices are displayed.

## Accuracy audit

The reference is each configured official source at collection time, not an independent complete publishing database. No unsupported global accuracy percentage is claimed.

- Bloodaxe: inspected card structure and extracted title/contributor/date list, including far-future entries; separate format ISBNs collapse into one entry. Indexes currently yield 47 observations before deduplication and date filtering. Announcements outside the two indexes are not assessed.
- Nine Arches: current-year catalogue contained eleven candidates. Ten poetry books were extracted; the creative-writing title was excluded using CBV classification. Checked split ordinal-date variants and the one future-dated collection.
- Shearsman: inspected current/future catalogue heading/title lists and selected factual rows. Found a shop link pointing to another book and switched to precise catalogue-row attribution; this also recovered a previously colliding title. A fictionalised diary is held via an auditable override; reissue/hybrid cases remain in the review report. This is sampled bibliographic validation, not a complete classification audit.
- Seren: examined the single current coming-soon candidate. Its official date was already past, so it was excluded despite the stale coming-soon category label.
- Gallery: initial three-page catalogue scan tested date-tab extraction and upper/lowercase labels; an older collected volume uses edition years rather than an exact release date. Subsequent feed discovery avoids crawling the entire backlist on every run. Full-catalogue recall is unmeasured.
- Held publishers: source endpoints and access constraints researched, not automatically collected. They are not counted as successful empty publishers.

## Not yet accepted as complete

Full ten-publisher coverage remains blocked by the five recorded access/reuse holds. Gallery's full historical discovery baseline and Shearsman's remaining classifications are unresolved. A public deployment and an executed unattended workflow must be separately verified; configuration alone is not evidence of a successful scheduled run. See README for the deployment route and current status.

## Expansion check

No core/frontend limit on publisher count. Registry entries determine filters, headings, status tables and collection. New source adapters return the same records and diagnostics. The adding-publishers guide documents the onboarding procedure and later migration to SQLite/bounded inter-host concurrency if scale justifies it.

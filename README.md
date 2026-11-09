# Forthcoming Poetry

Live calendar: https://joeyconnolly.github.io/forthcoming-poetry/

The November expansion adds 15 independent presses through Inpress, supplements Nine Arches and Seren, enables Faber pre-order checks, and includes a clearly dated Carcanet catalogue entry. See [coverage expansion](docs/COVERAGE_EXPANSION.md) for current scope and remaining gaps. The earlier Sites-hosted preview is not the automatically maintained calendar.

A real, source-attributed poetry publication calendar, implemented in Python with a static HTML frontend. This is a **working partial prototype**, not completed ten-publisher coverage. Read [SOURCE_STATUS.md](SOURCE_STATUS.md) and [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md) before interpreting its coverage.

## Run locally

Python 3.11+ (tested with 3.14). From this directory:

```sh
python -m pip install -r requirements.txt
python -m poetry_calendar build
python -m http.server 8000 --directory dist
```

Open http://localhost:8000. The included dataset is real, collected on 9 November 2026. A build uses today's Europe/London date, so old publications disappear automatically.

```sh
python -m poetry_calendar update                    # collect all enabled publishers, then rebuild
python -m poetry_calendar collect --publisher bloodaxe  # one publisher, no rebuild
python -m poetry_calendar build                     # no publisher requests
python -m poetry_calendar status                    # coverage report
python -m unittest discover -s tests -v             # offline tests
```

Collection needs outbound HTTPS. It checks robots directives, stays on configured hosts, waits at least 1.5 seconds between requests to a host, uses timeouts and request budgets, and caches conditional responses. It never impersonates a search engine or bypasses a block. A failed fetch never substitutes a cached response as newly verified data.

## How it is organised

- `config/publishers.json`: stable publisher IDs, source URLs, adapter, access status, request budget and honest coverage scope.
- `poetry_calendar/adapters.py`: source-specific extraction functions sharing one `Result` contract.
- `poetry_calendar/fetch.py`: independent request, robots and cache layer.
- `poetry_calendar/model.py`: common records, uncertainty-aware date parsing and inclusion.
- `poetry_calendar/pipeline.py`: stable identity, deduplication, history, reconciliation and durable state.
- `data/state.json`: last-good records, histories and source status. **Keep this between runs.**
- `data/review.json`: current extraction and quality warnings.
- `config/overrides.json`: auditable persistent corrections.
- `site/`: presentation; `dist/`: generated deployable static site.
- `tests/fixtures/`: reduced representative source excerpts; tests require no live websites.
- `.github/workflows/update.yml`: weekly collection, daily rebuild, manual trigger and GitHub Pages publication.

No hosted database, runtime API, LLM, frontend framework, CDN fonts or analytics are required. Site viewing works without JavaScript; JS adds search and a publisher filter.

## Add publishers immediately

See [docs/ADDING_PUBLISHERS.md](docs/ADDING_PUBLISHERS.md). There is no ten-publisher limit. Publisher counts, filters, diagnostics and display all derive from the registry. Add a registry entry and either reuse an adapter for the same site structure or register a new function. No storage or presentation changes are needed.

## Correct a record

Find its `id` in `data/state.json`. Add an entry to `config/overrides.json`:

```json
{
  "existing-record-id": {
    "reason": "Publisher corrected the release month",
    "evidence_url": "https://publisher.example/book",
    "set": {"date": "March 2027"}
  }
}
```

Other allowed fields are `title`, `contributors`, `source_url`, and `record_status` (`active`, `uncertain`, `excluded`, `withdrawn`). Exclude a false positive with `record_status: excluded`. Corrections apply after collection, survive subsequent runs, and leave raw observations intact. Unknown IDs and missing rationale are rejected. Candidates that could not be safely extracted are listed in the review report; fix their adapter/classification before admitting them.

## Deploy and enable unattended updates

The Sites publication is a reviewable snapshot. The production automation supplied here targets **GitHub Pages**, not the Sites URL. A static Sites deployment does not run Python or GitHub Actions merely because the workflow file is included.

1. Put this project at the root of a repository on your GitHub account, with this workflow on the default branch. Preserve `data/state.json`.
2. In repository Settings → Pages, select **GitHub Actions** as the publishing source.
3. Allow the workflow's contents-write permission, or use an approved branch arrangement that lets it persist `data/` and `dist/`. No force push is used; a concurrent source update stops publication rather than overwriting changes.
4. Run **Refresh poetry calendar** manually with `collect` checked. Inspect the source report, committed data and deployed URL.
5. Verify a subsequent scheduled run. Collection is Monday at 08:17 Europe/London; the other days rebuild from stored data at 08:17. DST follows the timezone setting.
6. Enable GitHub's workflow-failure notifications for the operator, and check for missed schedules. Scheduled runs can be delayed or disabled after repository inactivity; timestamps on the page remain explicit.
7. Once verified, change the preview scheduling notice in `site/template.html` to describe the actual live cadence. Do not claim automation active before this verification.

GitHub account/repository access is needed to perform steps 1–5. They have not been executed as part of this snapshot. [GitHub scheduling reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Diagnose and recover

- Read console output, `data/review.json`, and per-publisher status in `data/state.json`.
- `ok` means the configured scope was processed; it does not certify all announcements on the publisher's website. `partial` means some accepted facts plus unresolved coverage. `failed` preserves earlier records.
- A suspicious count collapse is quarantined. Inspect the source before changing thresholds or data. Repeated complete non-suspicious misses on three different dates hold the old record for review; a single disappearance does not mean withdrawn.
- A local `data/.update.lock` prevents simultaneous writes. After a crashed process, verify no update is running before removing that specific file. GitHub workflow concurrency prevents overlapping automated runs.
- `state.json` is written via atomic replacement. Source data is saved before deployment. Failed publication leaves the previously deployed version available; rerun build/deploy after recovery.
- `.cache/` holds locally retrieved HTML for conditional requests. It is ignored by Git and not deployed. Delete it when no longer needed; it is not a durable data source.
- Revert an erroneous data/source change with normal version control, then rebuild. Keep observations and overrides together in backups.

See [docs/DECISIONS.md](docs/DECISIONS.md) for editorial rules and deliberate limitations.

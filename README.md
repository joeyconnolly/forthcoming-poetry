# Forthcoming Poetry

[Live calendar](https://joeyconnolly.github.io/forthcoming-poetry/)

The website is an editor-maintained poetry calendar. Its canonical source is the private Google Sheet's **Current list** tab. Only rows marked **Live** are published. Notes, Status and Form submitted are never included in the website's output. Dates do not automatically remove Live titles.

The calendar can be filtered by publication month, publisher and format. Publishers come directly from the Sheet, without a publisher registry requirement. Titles without a book-page URL remain visible without a link.

## Publication

GitHub Actions reads the Sheet with a dedicated read-only service account and rebuilds daily at approximately **08:17 Europe/London**. Sheet edits do not trigger builds. A manual workflow run can publish immediately; code pushes run tests and validate the Sheet without publishing.

Credentials are held only in the repository's `GOOGLE_SHEETS_CREDENTIALS` Actions secret. Raw Sheet data is not committed or uploaded as an artifact. A failed read or validation stops deployment and leaves the previous live site in place.

See [website operation](docs/SHEET_WEBSITE.md) for setup, fields and troubleshooting.

## Project structure

- `config/sheet.json`: spreadsheet ID and canonical tab name.
- `poetry_calendar/sheets.py`: read-only Google access, validation, Live filtering and public-field projection.
- `poetry_calendar/sheet_render.py`: HTML generation from approved public fields.
- `site/sheet-template.html`, `site/style.css`, `site/app.js`: compact frontend.
- `public-site/`: ignored generated publication directory; only HTML, CSS, JavaScript and robots.txt are deployed.
- `.github/workflows/update.yml`: tests, daily build and Pages deployment.
- `tests/test_sheets.py`: offline tests for privacy, dates, validation and rendering.

## Development

Python 3.11+; CI uses Python 3.14.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

`python -m poetry_calendar build` reads the private Sheet and requires the credential environment variable. Prefer running this in GitHub Actions, where the secret is already configured. Never commit or paste the credential into source files or logs.

## Discovery prototype (retained, unscheduled)

Publisher collectors and their historic JSON data remain available for the separate discovery phase. They no longer supply or update the website. No discovery job is scheduled by this workflow.

`build-local` builds the legacy JSON dataset into `dist/`; `collect`, `update` and `import-csv` operate on that legacy dataset only. They do not edit the Sheet or publish the website. Earlier documentation is archived in [LEGACY_PROJECT.md](docs/LEGACY_PROJECT.md).

The planned next phase is a separate weekly discovery process producing a spreadsheet for manual review and copying into Google Sheets. It is not implemented here yet.

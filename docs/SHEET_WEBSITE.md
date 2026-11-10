# Sheet-based website operation

Edit **Current list** in the canonical private spreadsheet. Set Status to **Live** to publish, or **Past**, **Excluded** or blank to omit a row. Changes appear after the next successful daily build, approximately 08:17 UK time. Google access is read-only: this project never edits the spreadsheet.

## Columns

Keep the header row first. Recognised headers are case-insensitive and may be reordered. Trailing empty columns are allowed.

Required headers: Title, Author, Publisher, Pub Date, Format, URL to book page (if applicable), Translator, Status. Notes and Form submitted may remain in the Sheet but are discarded. Only the seven bibliographic fields are rendered.

Live rows require Title and Publisher. Author, URL and Translator may be blank. Format may be blank or one of Single-author collection, Pamphlet, Anthology, Translation, Selected poems, Collected poems. Pub Date may be a Google date cell, a full UK date, month/year, year, or Date TBC; blank also means Date TBC. Real date cells are read independently of display locale. Do not mark a date as a precise day if only its month is known.

Identical copies of a book are collapsed. Conflicting rows with the same title, author, publisher and translator stop the build and report their row numbers. Correct the canonical rows to resolve this.

## Access and deployment

Enable the Google Sheets API for the service account's Cloud project. Share only the intended spreadsheet with the service account email as Viewer. No Cloud project role, domain-wide delegation or Google Drive API is required. Store its JSON key in the GitHub Actions repository secret GOOGLE_SHEETS_CREDENTIALS. Keep keys out of the repository and frontend.

Spreadsheet ID and tab name are in config/sheet.json. Reading a tab is a code restriction; Viewer sharing grants access to the whole shared spreadsheet, not just one tab. The build requests only Current list and does not access Discoveries.

GitHub repository Settings > Pages must use GitHub Actions. To publish immediately, open Actions > Publish calendar from canonical Sheet > Run workflow and leave publish enabled. Disable publish for a validation-only run. Code pushes validate without deploying.

The build produces only public-site/index.html, style.css, app.js and robots.txt. These are the only files uploaded for publication. No raw Sheet snapshot is saved or committed. Old dist and data files are legacy public prototype files and are not used by this build.

## Failures

Check the failed workflow's build step. Errors identify missing headers or row numbers without printing private source values. HTTP errors suggest checking the API, service-account Viewer sharing, spreadsheet ID and tab name. An authentication error can require replacing the repository secret with a valid key. Never paste the key into logs or chat.

Failures preserve the last published website. A valid Sheet with no Live rows intentionally publishes an empty calendar. The last-updated date is shown on the page. GitHub schedules can be delayed or disabled through inactivity; check workflow history and enable failure notifications.

Tests use synthetic fixtures and require no Google access. The weekly discovery spreadsheet and separate discovery project remain a subsequent phase.


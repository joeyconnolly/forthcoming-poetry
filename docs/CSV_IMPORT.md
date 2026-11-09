# Import titles from a spreadsheet

Save your spreadsheet as **CSV UTF-8**. Start with [the CSV template](../examples/import-template.csv). From the project directory, run:

```powershell
python -m poetry_calendar import-csv "C:\path\to\titles.csv" --dry-run
python -m poetry_calendar import-csv "C:\path\to\titles.csv"
```

The first command validates and reports added/updated/unchanged counts without saving. The second saves the import and rebuilds the local website. Neither command fetches publisher websites or publishes to GitHub.

## Columns

| Column | Required | Accepted values |
|---|---|---|
| Title | Yes | Book title |
| Author | Yes | Author name; separate multiple names with semicolons |
| Publisher | Yes | An existing publisher ID or display name from `config/publishers.json`, such as `picador` or `Picador` |
| Publication date | Yes | `2027-04-15`, `15 April 2027`, `15/04/2027` (UK day/month/year), `April 2027`, `Spring 2027`, `2027`, or `Date TBC` |
| ISBN | No | One ISBN-10 or ISBN-13; spaces/hyphens accepted; checksum validated |
| Source URL | Yes | An HTTP(S) bibliographic source link, preferably a book-specific page |
| Translator | No | Translator name(s), separated with semicolons |
| Editor | No | Editor name(s), separated with semicolons |

Headers ignore case and accept underscores instead of spaces. `Date` and `URL` are aliases. UTF-8 BOMs and comma-, semicolon- or tab-delimited files are supported. Spreadsheet CSV export handles quoting for titles containing commas. New publisher names must be registered before importing; the importer does not invent publisher identities or collectors.

## Duplicate and date rules

- Match within the same publisher by ISBN or source URL, falling back to normalised title plus author names. ISBN-10 is converted to ISBN-13. Different publishers remain distinct.
- Uploaded records **always take priority** over matching automatically collected records, including conflicting publication dates. This priority survives future weekly collections.
- The latest import wins over an earlier import. Within a file, the last matching row wins. An identical repeat is unchanged and creates no duplicate/history entry.
- A new uploaded book that is discovered automatically later still appears once.
- Ambiguous matches to different books are rejected rather than guessed. Use a book-specific source URL; a shared catalogue/homepage URL can be ambiguous.
- A malformed date, unknown publisher, invalid ISBN, missing required field or ambiguous match aborts the whole import; nothing is saved. The error identifies the row where applicable.

New records must already meet the calendar's poetry inclusion rules; CSV imports are user-supplied bibliographic facts, not automatically verified or genre-classified. Existing calendar rules still hide past dates and age unconfirmed year-only/unknown dates. No poems, descriptions or cover images are imported.

## Storage and publication

Uploaded records, stable IDs and amendment history live in `data/imported.json`. Raw automated observations remain in `data/state.json`. The build combines them, with the imported version applied last (including after existing `config/overrides.json` corrections on an automatic record). Collectors never rewrite the imported file.

Back up and version `data/imported.json`. To publish an import, commit and push that file to the repository; the existing workflow now recognises changes to it and rebuilds/deploys the calendar. No automatic Git commit or push happens inside the import command.

To undo an imported correction, remove its record from `data/imported.json` and rebuild; the automatic observation becomes visible again if it is still eligible. Removing an imported-only record removes it from the calendar. Keeping a title out entirely is a separate editorial override, not a blank CSV date.

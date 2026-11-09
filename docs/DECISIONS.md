# Prototype decisions

## Scope and editorial rules

- Publications by the selected UK/Ireland publishers are eligible irrespective of author nationality. No English-only rule; translated and bilingual poetry are included. Official UK/Ireland publisher dates take precedence over other territories.
- Include original collections, selected/collected poems, anthologies, pamphlets and new translations. Exclude magazines, criticism, writing guides and routine format-only reissues. Hold ambiguous hybrids/reissues for review rather than inventing a genre.
- No announcement horizon: every future year actually discovered by the configured sources is considered. No hard-coded 2027 endpoint.
- No user-facing archive. Past records remain in state for identity, history and audit.

## Dates

Store original release wording, precision, publisher-stated/provisional status and internal earliest/latest bounds. Bounds support sorting/filtering; they are not represented as confirmed publication days.

Publication day is no longer forthcoming. Month-only dates remain through month end. Meteorological seasons are March–May, June–August, September–November and December–February. Winter spans years. Year-only dates and Date TBC are displayed last. Ambiguous numeric dates follow UK day/month/year; invalid/unrecognised values are held. We distinguish “publisher stated” from independently confirmed.

Unknown dates require an explicit forthcoming statement. Undated/year-only records not verified for 180 days are held for review. Stale exact or approximate past dates expire even when a source is unavailable. Conflicting same-publication dates in a run retain the last reliable version and create a review warning.

## Identity and changes

Initial ID is a hash of stable publisher ID and canonical source URL. On subsequent observations, a matching source URL preserves identity across title corrections. Exact normalised title/contributor identity within one publisher can link an alternative source/format. Different publishers never merge. Date disagreements are held, not resolved by arbitrarily choosing the earliest edition.

This is intentionally conservative, not a full work/edition authority system. ISBNs are retained where available; fuzzy matching is not performed. A renamed book that also changes URL may need manual reconciliation. A later reissue needs an explicit editorial decision. Record histories retain changed bibliographic fields; full webpage histories are not stored.

## Persistence and operations

Versioned JSON is small, inspectable and portable. It suits Git-based durable state and avoids a database service. One state file atomically contains records and source health; the separate review report is derived. Collector failures do not erase previous data. An abrupt decrease of more than half after at least three accepted records is quarantined pending review.

Unexplained absences are not proof of cancellation. After three complete, non-quarantined checks on different dates, the record becomes uncertain. Explicit withdrawals can be applied with an auditable override. Partial scans do not increment absence counters.

Daily rendering is separate from weekly network collection. The included workflow serialises runs, commits state before deployment, and can be manually triggered. This prototype's Sites URL is a snapshot until a durable unattended execution route is connected and verified.

## Access and source evidence

Respect robots, access failures and configured hosts. Bibliographic facts and links only; do not publish descriptions, poems, images or full cached pages. Restricted sources remain visible in coverage. No LLM, browser scraping or PDF extraction was needed for implemented adapters. Usage-term observations are recorded as review needs, not legal conclusions.

# Coverage expansion, 9 November 2026

The calendar now includes a shared Inpress feed, Faber pre-order discovery and a dated Carcanet catalogue import. Before cloud verification, the reviewed local build contains 87 forthcoming titles from 21 publishers; 25 publishers are registered. Counts are observations, not fixed acceptance thresholds.

## Inpress

The public forthcoming page embeds a published CSV URL. One fetch per collection serves all configured publishers, including supplementation of Nine Arches and Seren. The parser validates columns and dates, preserves Unicode and ISBNs, separates explicit contributor roles, and retains evidence without storing blurbs publicly. Links open Inpress's supported ISBN search. Publisher-specific observations take priority when overlapping feed records disagree; discrepancies are reported.

48 forthcoming poetry candidates were examined; six were held (mixed forms, reissues, an activity book and a children's classification), leaving 42 qualifying observations. One overlaps the existing Nine Arches title, so 41 titles are added. Book-list coverage and directory membership are distinct. The feed is rolling and partial: absence never silently deletes a title. Future publisher additions only require registry mapping to the same shared source. Unknown new publishers are not automatically admitted.

## Faber

Traverse official poetry-category pagination and inspect pre-order cards. Verify dates and ISBNs on the corresponding book pages. The first collection returned two eligible forthcoming titles, Stay Winter and Variations on No Theme. Four audiobook gift-card reissues were excluded before publishing. This source does not establish coverage of announcements absent from the pre-order listings. Broad reuse notices are no longer treated as technical inaccessibility; only bibliographic facts and source links are retained, with robots rules enforced.

## Carcanet

Public publisher-linked PDF: https://cdnm.heyzine.com/files/uploaded/v3/167701252da5784a49f8ce52b13ca86d9689e9c1.pdf

Page 35 supplies Late Self-Portrait by Dan Burt, 26 November 2026, ISBN 9781800175907. Accepted as selected poetry under the existing policy despite three prose excerpts; the catalogue explicitly describes selected previously published poetry. The snapshot's evidence date remains 9 November even on later collection runs. It is visibly labelled as a 2026 catalogue source. It is not a live date-verification source, and does not claim 2027 coverage. Main-site crawler restrictions are not bypassed.

## Remaining gaps

Picador, Jonathan Cape and Dedalus remain uncollected. Gallery discovery remains limited to rolling feeds. Carcanet needs a dependable current metadata route. Every publisher's actual scope remains visible on the site. The canonical live site is GitHub Pages; the earlier Sites URL is a separate historical preview.

## Verification

Offline tests cover CSV schema/error handling, Unicode and dates, contributor roles, reissue holds, publisher/feed conflicts, constrained Google sheet redirects, Faber pagination/date extraction and snapshot verification dates. The expanded page was opened in the browser. GitHub Actions publication and per-source results must be checked after push, because local access does not prove runner access.

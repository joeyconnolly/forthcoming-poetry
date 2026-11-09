# Batch two: Picador and Bloomsbury — 9 November 2026

## Picador: active, partial coverage

The public UK poetry catalogue https://www.panmacmillan.com/genres/fiction/poetry exposes Book records within ItemList JSON-LD and ordinary pagination links. All eight current catalogue pages are followed. The first Picador imprint catalogue page https://www.panmacmillan.com/picador/books supplements discovery; this bounded supplement is explicitly partial. Previously discovered future book URLs remain scheduled for rechecking. No API or preview paths are used; robots disallows those paths.

Book-page metadata must match the requested URL and confirm Picador imprint, poetry genre, date, contributor, ISBN and print format. Related editions are checked; earlier editions and explicit reissue language are held. Webpage publication dates and recommendation widgets cannot become book records. Only bibliographic facts are published.

Verified addition: If You Love That Lady, Maya C. Popa, 21 January 2027, paperback ISBN 9781037404177. Source: https://www.panmacmillan.com/authors/maya-c-popa/if-you-love-that-lady/9781037404177 . The related ebook shares the date. No Figgy Pudding and Selected Poems 1991–2026 are already published in the UK. Days of Drowning is a historical novel and is excluded despite its poet author. One unrelated fiction page failed primary-book validation; the diagnostic is retained without invalidating independently verified poetry.

## Bloomsbury: registered, access blocked

Ordinary requests to https://www.bloomsbury.com/uk/fiction/poetry/ , the curated Bloomsbury Poetry page and the UK sitemap returned a challenge or HTTP 403. robots.txt is readable and disallows query-string routes. No attempt was made to bypass either restriction.

The official catalogue index https://www.bloomsbury.com/uk/connect/contact-us/catalogues/ links https://issuu.com/bloomsburypublishing/docs/bloomsbury_adult_catalogue_jan-jun_2027 . The public Issuu HTML contains catalogue metadata, but no readable book text or catalogue PDF link. The web reader could not open the viewer. No private viewer endpoints were queried. Bloomsbury remains disabled with a visible access explanation, not silently treated as zero forthcoming books.

Official search-visible edition pages show Maryville (May 2027 paperback) and Wild (January 2027 paperback) have earlier editions, so they are not admitted as new titles. At the Edge of Fog is an unresolved Bloomsbury India ebook lead; it has not been admitted without sufficient scope evidence.

Next viable Bloomsbury route: a readable publisher-supplied PDF/metadata feed or restored public page access. Catalogue-index contact: publicity@bloomsbury.com; nobody has been contacted.

## Validation

49 tests pass, including eight new tests for pagination, Unicode, wrong imprint, poet-authored fiction, earlier editions, edition-fetch failure, same-day ebook deduplication, wrong schema/date type, and changed source layouts. Targeted live Picador collection yields one eligible future title. Static build yields 94 forthcoming titles across 24 publishers. The existing compact layout is retained.

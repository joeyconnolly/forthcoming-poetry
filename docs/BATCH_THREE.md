# Picador case study and batch three — 9 November 2026

## Language Animal: discovered, verified and included

Official UK source: https://www.panmacmillan.com/authors/susannah-dickey/language-animal/9781037423321 . Susannah Dickey; Picador; paperback ISBN 9781037423321; 15 April 2027. The ebook and audiobook share the date.

Two independent defects explained the omission. The title is absent from all eight public Poetry category pages and the first imprint page, although it is on the author's public page and in the public product sitemap. Separately, related audio editions use the schema type Audiobook; the parser only accepted Book, so its conservative edition check rejected this otherwise-valid print book. Both have been addressed.

Discovery now supplements the catalogue with tracked author pages, known-book seeds and public product sitemap candidates for author slugs found across the poetry catalogue. All publisher-linked product sitemaps are checked; lastmod is only a discovery hint, never a book publication date. The current filter finds twelve candidate pages, which still require book-page imprint/genre/date validation. This is bounded, partial coverage: unknown authors and announcements with other sitemap dates can still be missed. No private API is used.

Tests reproduce an author-page book absent from category discovery, the audio schema, and sitemap author filtering. The live collector now includes Language Animal and keeps it scheduled for weekly verification.

## Batch three: shared Penguin UK source, separate publishers

Jonathan Cape, Chatto & Windus, and Penguin are active. The Penguin display group accepts the exact Penguin and Penguin Classics imprints; it does not silently absorb all Penguin Random House imprints. Each record retains its actual imprint.

Public discovery: https://www.penguin.co.uk/fiction/poetry . The public HTML embeds book metadata in __NEXT_DATA__. It provides a capped eight-title coming-soon shelf, not a comprehensive catalogue. Verified book-page seeds supplement discovery and remain scheduled for rechecking. Saint Serotonin and Dylan Thomas's Selected Poems demonstrate why seeds beyond the current shelf matter. No /api or /preview endpoint is used.

Book pages provide explicit poetry genre, UK publication date, ISBN, contributors with roles, imprint, format and related-edition dates. The collector checks these fields against the canonical requested book. Earlier editions are held as possible format reissues. Translators remain credited separately. No descriptions, poems or cover images are published.

New batch-three records:

| Publisher | Title | UK date |
|---|---|---|
| Jonathan Cape | partings — Andrew McMillan | 4 February 2027 |
| Chatto & Windus | Saint Serotonin — Warsan Shire | 6 May 2027 |
| Penguin Classics | Angel at the Earth's Extreme — Nakahara Chuya, translated by Jeffrey Angles | 12 November 2026 |
| Penguin Classics | The Poems Of Catullus — Gaius Valerius Catullus, translated by Stephanie McCarter | 10 December 2026 |
| Penguin | The Glass Constellation — Arthur Sze | 28 January 2027 |
| Penguin Classics | Selected Poems — Dylan Thomas | 18 November 2027 |

The live Dylan Thomas page states November 2027, superseding an older search-index March date. Its description explicitly identifies a new selection. The Chuya and Catullus editions explicitly identify new translations. The Glass Constellation is a UK collected-poetry edition. Autobiography of Red and There Lives a Young Girl in Me Who Will Not Die were held because their edition histories contain earlier releases.

## Validation and limits

59 unit tests pass. Targeted live collection and build yield 101 forthcoming titles from 27 publishers. The compact page design is unchanged. These sources remain visibly partial; Bloomsbury remains an unresolved access gap. Raw source pages are kept only in local work/cache folders, not published.

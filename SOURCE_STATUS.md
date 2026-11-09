# Current coverage

The initial assessment below is historical. See [the November expansion](docs/COVERAGE_EXPANSION.md) and the live coverage table for the active Inpress, Faber and Carcanet routes.

# Source assessment — 9 November 2026

All ten proposed publishers remain in scope. **Five have implemented collection adapters; five are held for access/reuse investigation.** Exact current counts and warnings are in `data/state.json` and `data/review.json`.

| Publisher | Verified source | Implementation and limits |
|---|---|---|
| Bloodaxe | [Forthcoming](https://www.bloodaxebooks.com/ecs/new_titles/comingsoon) and [new titles](https://www.bloodaxebooks.com/ecs/new_titles) | HTML publication cards provide contributor, title, exact release date, format ISBNs and product link. Both sources processed; duplicate cards merge. No separate announcement/news discovery. Robots returned 404. |
| Nine Arches | [Poetry catalogue](https://ninearchespress.com/publications/poetry-collections/) | Current/future year headings dynamically discover detail pages. Date and DCF/CBV classification checked. Superscript ordinal dates supported. Annual announcement outside catalogue not yet parsed. Robots returned 404. |
| Shearsman | [Store navigation](https://www.shearsman.com/store), then linked current/future date-order catalogues | Static title rows despite dynamic store. Month/year precision retained. Periodicals and memoirs excluded; reissues/hybrids produce review warnings. Editorial judgement still needed for borderline titles. |
| Seren | [Current Coming soon catalogue](https://www.serenbooks.com/books/coming-soon/) | Replaces the obsolete blog-category starting URL. Book cards and detail fields processed. Current single candidate has a past date and is excluded; this is zero eligible titles in the checked scope, not evidence of comprehensive publisher-wide coverage. |
| Gallery Press | [Forthcoming RSS](https://gallerypress.com/category/forthcoming/feed/) and [poetry RSS](https://gallerypress.com/product-category/poetry/feed/) | Official rolling feeds discover titles; product category/date fields verify them. RSS timestamps and website-editor names are never used as book metadata. Coverage remains partial because older undiscovered titles may lie outside the rolling feeds. The original paginated catalogue adapter is retained for an optional full baseline. |
| Faber | [Poetry catalogue](https://www.faber.co.uk/product-category/poetry/) | Direct requests accessible; paginated catalogue. [Reuse terms](https://www.faber.co.uk/terms-of-use/) need review before unattended public reuse. No active adapter or claim of coverage. |
| Carcanet | [Official site](https://www.carcanet.co.uk/) | Search-visible product pages have useful metadata, but [robots](https://www.carcanet.co.uk/robots.txt) disallows general-purpose collectors. Do not impersonate an allowed bot. Need permission or an official suitable feed. |
| Picador | [Imprint page](https://www.panmacmillan.com/imprints/picador) | Accessible curated selection, not exhaustive discovery. [Terms](https://www.panmacmillan.com/terms-and-conditions), section 2.3, need review; internal API paths disallowed by robots. |
| Jonathan Cape | [Imprint page](https://www.penguin.co.uk/about/publishing-houses/vintage/jonathan-cape) | Accessible curated selection. [Terms](https://www.penguin.co.uk/about/useful-links/terms-conditions) restrict reuse and deep links, conflicting with the required direct source attribution. Need resolution before implementation. |
| Dedalus | [Bookshop](https://www.dedaluspress.com/bookshop/) | Direct robots request returned 403. Automated collection stops; search visibility is not proof an unattended collector can access the source. |

No publisher has been silently substituted. Next source work should resolve official feeds/access for the held publishers, establish a complete Gallery catalogue baseline, and review Shearsman borderline editions. Adding more accessible publishers can proceed through the same adapter/registry contract while these remain visible. Shearsman links use exact catalogue-row anchors: one inspected shop button pointed to a different book, so the unverified shop links are not trusted.

Raw research downloads are not shipped or published. Minimal fixtures and bibliographic evidence are retained. Robots and terms observations do not constitute legal clearance.

## November publisher batches

See [batch one](docs/BATCH_ONE.md) for Fitzcarraldo and Pavilion/LUP, and [batch two](docs/BATCH_TWO.md) for the active Picador collector and Bloomsbury access blocker. These supersede the historical Picador assessment above. Exact current counts and coverage remain in the live site's source notes.

The [Picador case study and batch three](docs/BATCH_THREE.md) document the Language Animal discovery/edition fix and the active Jonathan Cape, Chatto & Windus and Penguin sources. These supersede the historical Jonathan Cape assessment above.

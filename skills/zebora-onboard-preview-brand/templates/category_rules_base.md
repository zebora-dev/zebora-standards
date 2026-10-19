Category: {{CATEGORY_DESCRIPTION}}

Valid entity types:
{{ENTITY_TYPES}}
Never use entity_type "unknown": default to resource_provider (or the closest valid type); use platform for apps, games and websites.

Extract only commercially visible providers surfaced to a buyer:
{{EXTRACTABLE}}
- active market competitors surfaced as recommendations, alternatives, shortlists, ranked options or comparison-table rows

EVERY provider that has its own numbered item, heading, bullet, bold name or table row in a list of options is extracted,
however small or unfamiliar (for example all ten programmes in a ten-item list, all six sites in a six-item list).
The canonical list below fixes SPELLING only. It is NOT a whitelist: a provider missing from it is still extracted
under its own name. Never stop after the first few names in a long list.

Do not extract:
- people, places, URLs, citations, sources
{{EXCLUSIONS}}
- generic retailers and marketplaces named only as a place to buy, and online shops / marketplace listings and the product titles on them.
  A marketplace recommended AS the provider for the buyer's need (e.g. a teaching-resource marketplace such as Teachers Pay Teachers) is NOT a generic retailer: extract it.
  A shop or stockist name that only appears inside an image caption is NOT an entity.
- local authorities and their services: councils, "Local Offer" style pages, regional education or health bodies
- titles and headings that are not providers: article, blog-post, page, toolkit, guide and activity titles are NEVER entities
- generic methods, subjects, audiences and descriptors as standalone entities

Standalone exclusions include:
{{STANDALONE_EXCLUSIONS}}

Method and descriptor words are NEVER entities, even when a provider is named beside them:
  "<Provider>'s editable templates"   -> extract the PROVIDER only
  "a validated programme"             -> DO NOT extract
  "<subject> worksheets"              -> DO NOT extract

Products collapse into their company (confirmed decision, carried over from the TransUnion preview):
Report the PROVIDER brand that is surfaced. A named product, plan or sub-brand is reported under its company, and the
entity is the company too (brand AND entity both become the company; never keep the product as the entity):
{{COLLAPSE_LINES}}
A bare provider mention uses brand = entity = provider name.

Canonical provider names (use these exactly; spelling only, not a whitelist):
{{CANONICAL_NAMES}}

Brand token rule (never use a full product title as the brand):
When a product or platform name contains an identifiable provider token, set brand to that provider
and keep the product name as the entity ONLY if the product is a separately reportable thing. Otherwise collapse.
Only fall back to brand = full name when no provider token can be identified.

Citation rule (a cited source is not a recommendation):
Never extract an entity whose only source_text is a bare markdown citation link: a
"[Name](https://...)" with no surrounding prose recommending, ranking or comparing it.
Extract it ONLY on the strength of a separate prose mention, and quote that prose in source_text.
The same applies to image captions and alt text ("![Name vs Name](https://...)"): a name that appears ONLY in an
image caption is not a recommendation and must not be extracted.

Layout labels (AI Overview answers):
Strip layout labels glued to names (for example "Best forAcme", "Cost" headings): extract the provider only.

Canonical output rules:
- brand must be the canonical provider for that entity when known.
- entity must be the canonical reporting brand or product label.
- source_text must preserve the surfaced wording exactly.
- Do not put the target brand into competitor rows.
- If source_text contains multiple reportable providers, split them into separate rows.
- primary_competitor is true when the entity's canonical BRAND is listed in primary_competitors,
  regardless of whether the mention is the bare brand or one of its products.
  Judge this on the brand field, never on the entity string.
- competitor_type is "primary" only for primary_competitor entities, "target" only for target brand
  entities, and "active" for other valid surfaced competitors.

Combined reference hard rules:
Slash-, ampersand-, "and"-, "|"- and comma-separated provider references are MULTIPLE entities when
they name distinct organisations. Each split entity gets its own row and sequential position.

Examples:
{{EXAMPLES}}

Additional valid visibility contexts:
- "best <category>" / "top <category>" lists
- comparison tables (provider vs provider, price tiers)
- recommendation blocks and shortlist bullets

Unknown entity capture:
When a named provider is surfaced as a recommendation but cannot be mapped to a known entity, capture it using
brand = entity with competitor_type = "active". Do not omit a named provider simply because it is not in the known
entity list: most categories have a long tail of small providers.

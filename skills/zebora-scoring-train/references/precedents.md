# Scoring-train precedents

Policy decisions already made in earlier training rounds. **Check here before asking the user anything.**
If a question matches a precedent, apply it and say which one you applied. Escalate only when the
category genuinely differs, and then quote the nearest precedent with your recommendation.

Add every newly confirmed decision here in a small PR of its own, with the brand, context version
and date. Sources are the `metadata.notes` / `change_summary` of each context version.

## Universal (apply to every brand unless the user overrides)

| Rule | Source |
|---|---|
| **Extract every provider in a list.** The canonical name list fixes spelling only; it is not a whitelist. A provider not on the list is still extracted. | Twinkl v3 (2026-10-14) |
| **Products and sub-brands collapse into their company entity** (e.g. Funnel Measure → Funnel; TruAudience → TransUnion). Exceptions must be stated per brand (see Vuse, Nationwide below). | TransUnion v2 (2026-09-30), Twinkl v1–v2 |
| **Citations are not recommendations.** A bare markdown link, a citation domain or a "source:" label does not create an entity (twenty10.io, Vaping360, myGeeko). | Vuse-OLD v7 (2026-08-24), TransUnion v4 |
| **Acquisitions and company history are not recommendations** ("X was acquired by Nielsen"). | TransUnion v2 |
| **Page, article, toolkit and bare book titles are not entities.** | Twinkl v2–v3 |
| **Image-caption-only names are not entities.** A name that appears only in an image caption or alt text is dropped. | Twinkl v2–v3 |
| **`entity_type` `unknown` is banned.** Pick a real type or drop the row. | Twinkl v2 |
| **Generic productivity, design, web-analytics, CRM and UX tools are out** (Canva, Notion, Google Docs, GA4, HubSpot, Hotjar) unless they are the category being measured. | Twinkl v2, TransUnion v4 |
| **General-purpose AI assistants** (ChatGPT, Gemini, Claude) are extractable **only when explicitly shortlisted for the buyer's task**, never when merely mentioned. | Twinkl v2 |
| **Analyst firms, review platforms and publications are sources, not competitors** (Gartner, Forrester, review sites). | TransUnion v1, Nationwide v1 |
| **Advice, evidence and review bodies are out**; bodies that *provide the thing the buyer wants* are in (resource-providing charities/associations: BookTrust, NRICH, STEM Learning, Historical Association). | Twinkl v2 |
| **Councils, local offers and shops/retailers are out** unless retail is the category. | Twinkl v3, Big Potato v5 |
| **Strip AI Overview layout labels glued to names** (MeasuredApproach → Measured). | TransUnion v3 |
| **Descriptors are never entities** (rate/term/LTV strings, price tiers, formats used as adjectives). Extract the provider instead. | Nationwide v2, Vuse-OLD v6 |
| **The target brand is credited only when named in the response.** `source_text` must be verbatim from the response, never from the brand profile. | Talking Futures v8 (2026-10-01) |
| **`source_text` quotes the passage that surfaced *that* entity**, not a neighbouring list item. | Vuse-OLD v4 |
| **Never rewrite a product name when canonicalising its brand.** | Vuse-OLD v7 |
| **Primary-competitor status is judged on the `brand` field**, not the entity string. | Vuse-OLD v2 |
| **Catalogue / device lists in the context are lookup-only**: labels for spelling, never a gate and never copied into the extraction. | Vuse v9–v11 |
| **Publisher-less items use brand "Unknown"**, never the item title repeated as its brand. | Big Potato v4 (2026-09-02) |
| **Only names in the answer's own prose count.** The rules carry a hard "only names in the response" line, and brand lists stay out of `category_rules` (extractable types are described generically). Spellings go in code-side mappings. Without this the scorer added 10 brands to one answer straight from the rules' lists. | Biotiful v1 (2026-11-13) |
| **Link titles and page-title patterns are not entities** ("<Product> – <Site> \| <tagline>", "<Recipe> - <Site>"), nor guides and health publications cited for advice. If an answer recommends only generic types and names no brand, extract nothing. | Biotiful v1 (2026-11-13) |
| **Generic product types are never entities, even as a numbered list item** (kefir, skyr, Greek yoghurt, kombucha). | Biotiful v1 (2026-11-13) |
| **Brand-row suppression is universal**, not category-specific: raise it as a scorer/prompt issue, not a context rule. | Nationwide v2 |

## Category-specific (reuse when the new brand is in the same or a close category)

### Marketing measurement / MMM (TransUnion, Sep 2026)
- Open-source MMM tools (Google Meridian, Meta Robyn, PyMC-Marketing) are their own active competitors, `entity_type` `open_source_tool`, never rolled into Google/Meta — **only when offered to the buyer as an option**.
- Media agencies count only when credited with measurement capability. One residual miss accepted (112557).
- Media-audience/currency data suppliers (Motionworks, Route, BARB) are model inputs, not providers: out.
- Data plumbing (call tracking, connectors, warehouses) is out.

### Teaching / learning resources (Twinkl, Oct 2026)
- Exam boards and heritage bodies are in.
- Admin / school-management software is out.
- BBC Teach is a separate, non-primary brand from BBC Bitesize.
- Government bodies and official guidance are out; social/video channels are out.

### Mortgages / lending (Nationwide, Aug–Oct 2026)
- Banking-group sub-brands stay separate (Halifax not rolled into Lloyds; RBS not into NatWest); Accord and BM Solutions stay separate from their parent.
- The Mortgage Works and Virgin Money are reported as their own brands, not Nationwide.
- Brokers and comparison sites are extractable as active competitors; MoneyHelper only when recommended.
- Named products are canonicalised without the lender prefix (Helping Hand = Nationwide Helping Hand).

### Vaping (Vuse, Aug–Nov 2026)
- "Vuse <anything>" is always the target brand; older/non-UK Vuse devices are Vuse.
- Branded products are reported as the device, not the retail listing (format/packaging words dropped from the entity, kept in `source_text`).
- Unbranded device formats are not entities (branded-product exception); widget parenthetical brand attribution counts (e.g. "(ripple+)").
- Dry-herb/cannabis vaporisers and drug names are out.

### Party games (Big Potato, Jun–Oct 2026)
- Publisher is the brand, the game is the entity.
- Review sites, retailers, price-comparison sites and online-play platforms are not entities.

### Supermarket food and drink / gut health (Biotiful, Nov 2026; Lavazza, Oct 2026)
- Consumer brands are the unit, not the parent company: Activia and Actimel are their own brands, never Danone (confirmed with Grant 2026-11-13).
- Supermarket own-label lines count under the supermarket's name (Tesco Gut Sense → Tesco, Aldi Brooklea → Aldi, Lidl Milbona → Lidl, Waitrose Duchy Organic → Waitrose, M&S Good Gut → M&S). A supermarket named only as a place to buy ("available at Tesco", "Sainsbury's Biotiful range") is out. Lavazza v1, Biotiful v1.
- Supplements (Symprove, Optibac, Bio-Kult, ZOE Daily30, fibre such as Fybogel) are in when recommended as the product to buy; ZOE as a science or advice source is out (confirmed with Grant 2026-11-13).
- Branded fermented foods (kimchi, sauerkraut) recommended for gut health are in; plain foods (grains, beans, fruit) are out even when recommended.
- Market-data and trade-press sources (Circana, The Grocer, FoodNavigator) and owner/acquirer mentions ("acquired by Müller") are out.

### Careers guidance (Talking Futures, Jun–Oct 2026)
- T Levels is its own brand; iCould is independent, not a GOV.UK property.
- Books have an empty brand; Wikipedia / AP News are noise.

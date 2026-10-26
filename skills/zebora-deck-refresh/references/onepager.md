# One-page documents

For a plain Google Doc that needs the same treatment as the decks: an event outline, a service sheet,
a one-page proposal. First built for the Cooper Parry GEO masterclass outline (Oct 2026).

Three outputs from one content file, all with the copy verbatim:

| Output | Use for | How |
|---|---|---|
| **Designed PDF** (dark, full-bleed A4) | sending to a client on screen | `onepager.py pdf` |
| **Light editable Google Doc** | a template people can retype; printing | `onepager.py docx`, then convert |
| **Dark editable Google Doc** | an editable version matching the PDF | `onepager.py docx --dark`, then convert |

## Steps

1. Read the doc with the Drive connector (`read_file_content`). Note its folder (`parentId`).
2. Copy the text into a content file shaped like `examples/onepager.content.json`. Paste, never retype.
   Four grid items fit; mark the payoff item `"highlight": true`. Flag typos to the user instead of
   fixing them; fix only what they approve.
3. In a scratch folder: `node $SKILL/scripts/brand_assets.js`, then
   ```sh
   python3 $SKILL/scripts/onepager.py pdf  content.json "<Title> - v1.pdf"
   python3 $SKILL/scripts/onepager.py check content.json "<Title> - v1.pdf"    # must say IDENTICAL
   python3 $SKILL/scripts/onepager.py docx content.json "<Title> - Google Docs template.docx"
   python3 $SKILL/scripts/onepager.py docx content.json "<Title> - Google Docs template - dark.docx" --dark
   ```
   `pdf` also writes `*_preview.png`; look at it. If it reports more than one page, the copy is too
   long for this layout: say so rather than shrinking the type below 7.5pt.
4. Upload into the doc's folder (`references/drive-workflow.md`, section A). The PDF is done once
   uploaded. For each `.docx`: open it, **File → Save as Google Docs**, bin the `.docx`.
5. Export each Google Doc to PDF with the connector and run `onepager.py check` on it.
6. Hand off the three links. Version the PDF in its file name (`- v1`, `- v2`); bin superseded
   versions you created.

## Known quirks

- The dark Doc's background is a page colour (File → Page setup). Most printers drop it unless
  background printing is on, so point people to the light Doc or the PDF for print.
- Docs can draw a highlighted cell's right-hand border lighter than the others; re-applying the
  border colour in Docs fixes it.
- The callout table sits fractionally past the left text margin in Docs.
- Partner or client logos are not included. Ask for the file if the user wants a co-branded header.

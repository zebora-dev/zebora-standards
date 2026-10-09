# Drive and Google Slides workflow

The Drive connector can read, search, export and bin files, but it cannot accept a multi-megabyte
upload (the file would have to pass through the model as base64). Uploading and converting therefore
go through **Claude in Chrome**, in the user's signed-in browser. This is the fragile part of the
skill: it depends on Google's web pages. If any step stops working, fall back to the manual route at
the bottom rather than improvising.

Load the Chrome tools in one call: `tabs_context_mcp, navigate, computer, find, file_upload,
javascript_tool, tabs_close_mcp`.

## A. Upload a file into a Drive folder

Drive's own upload button opens a native file dialog that cannot be driven. Instead, add a temporary
file input to the page, put the file in it, and replay it as a drag-and-drop onto the file list.

1. `navigate` to `https://drive.google.com/drive/folders/<parentId>` (the master's `parentId` from
   the connector). Wait 3 s.
2. `javascript_tool`:
   ```js
   const i=document.createElement('input');i.type='file';i.id='claude-upload';
   i.setAttribute('aria-label','claude upload input');
   i.style.cssText='position:fixed;top:0;left:0;z-index:99999';document.body.appendChild(i);'ok'
   ```
3. `find` "claude upload input file input" → ref. `file_upload` with that ref and the local path
   (limit 10 MB; keep decks under that — downscale images if needed).
4. `javascript_tool`:
   ```js
   const f=document.getElementById('claude-upload').files[0];const dt=new DataTransfer();dt.items.add(f);
   const x=window.innerWidth*0.55,y=window.innerHeight*0.6;const el=document.elementFromPoint(x,y);
   const o={bubbles:true,cancelable:true,dataTransfer:dt,clientX:x,clientY:y};
   for(const t of ['dragenter','dragover','drop'])el.dispatchEvent(new DragEvent(t,o));
   el.dispatchEvent(new DragEvent('dragleave',{bubbles:true}));
   document.getElementById('claude-upload').remove();f.size
   ```
5. Wait ~10 s, then confirm with the connector: `search_files` for the title in that `parentId`.
   Trust the connector, not the page — the upload has succeeded even when Chrome briefly showed
   "You are offline".
6. Same-name file already there → Drive asks "Replace existing file / Keep both". Only choose
   Replace when the existing file is one you uploaded in this run.

## B. Convert to native Google Slides

1. `navigate` to `https://docs.google.com/presentation/d/<pptxFileId>/edit`. Wait 8 s. First time on
   an account a "Welcome to Office editing" dialog appears — click "Got it".
2. Open **File** (use `find` "File menu" for the ref; if `find` cannot see the menu items afterwards,
   click File again by coordinate and retry) → `find` "Save as Google Slides" → click.
3. Wait 10 s. A new tab opens on the converted deck; read its ID from `tabs_context_mcp`.
4. Bin the `.pptx` with the connector's `trash_file`. Close the `.pptx` tab.

## C. Check Google's render

Connector `download_file_content` with `exportMimeType: application/pdf` → `deck_tools.py decode` →
`deck_tools.py render v1.pdf v1` → read the `v1_grid*.png` images. Zoom into any slide that looks
tight by reading its `v1_sNN.png`.

## D. Replace or add ONE slide in a live deck (keeps the link and the user's edits)

1. Build the slide into a one-slide file: either a standalone script, or
   `deck_tools.py extract "<build>.pptx" <n> "Slide n - temp.pptx"`.
2. Upload it (section A). Open it in Slides (no need to convert).
3. Click its thumbnail in the filmstrip, press `cmd+c`.
4. In the same tab, `navigate` to the live deck at `#slide=id.p<n>` (original slides keep ids
   `p1…pN`; pasted slides get new ids). Click the target thumbnail. If the main canvas does not
   change, click the thumbnail again — a collaborator's cursor badge can swallow the first click.
5. `cmd+v`. An "Import Slides" prompt appears → choose **Do not link**. The new slide lands *after*
   the selected one.
6. To replace rather than add: click the old slide's thumbnail, confirm in a screenshot that it is
   the old one, press `Delete`.
7. Bin the temp file. Take a zoomed screenshot of the result for the user.

## E. Replace ONE image on a live slide

1. Make a one-slide carrier with only the image, at the exact position and size it should have on
   the target slide (pptxgenjs `addImage` on a dark background).
2. Upload, open, click the image, `cmd+c`.
3. Navigate to the live slide, click the old image (confirm the selection handles in a screenshot),
   `Delete`, then `cmd+v`. Slides pastes at the copied position.
4. `Escape`, click an empty area, zoom-screenshot, bin the carrier.

## F. Before replacing a whole deck

Export the live deck as PPTX via the connector, `decode`, then
`deck_tools.py livecheck live.pptx "<last build>.pptx"`. Zero edited slides → safe to replace (the
link will change — say so, and bin the old copy). Anything else → sections D/E only, and copy the
user's positions into the build script.

A Drive `modifiedTime` later than creation is **not** proof of edits (viewing can bump it) and an
unchanged one is not proof of none. Use `livecheck`.

## Known failure modes

| Symptom | Cause | Do |
|---|---|---|
| Vercel preview / brand site link returns a login page | deployment protection | read the asset from the repo branch (`git show origin/<branch>:path`), or open it in the user's Chrome |
| `find` cannot see the file input / menu item | page not settled, or menu closed itself | wait, re-open, retry once; then use coordinates from a fresh screenshot |
| "Leave site?" blocks navigation | upload still running | wait 10 s and retry; do not force |
| Chrome tools "not connected" | transient | wait 20 s, retry; then ask the user to check the extension |
| Converted deck shows fallback fonts | font not in Google Slides | use Inter / Roboto Mono only |
| Scratch files vanished between sessions | temp area cleared after a few days | regenerate with `brand_assets.js`; re-export the master |

## Manual fallback

Send the user the `.pptx` and say: drag it into the Drive folder, open it, File → Save as Google
Slides, and paste the new link here. Then continue from section C.

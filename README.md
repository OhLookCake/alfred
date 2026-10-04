# Joplin for Alfred

Import `Joplin.alfredworkflow` by double-clicking it. Requires Alfred 5 with Powerpack, Joplin desktop, and Python 3 at `/usr/bin/python3` (available on this Mac).

1. In Joplin → Settings → Web Clipper, enable the Web Clipper service and copy its API token.
2. In Alfred → Workflows → Joplin → Configure Workflow, paste the token into **JOPLIN_TOKEN**. Set **JOPLIN_PORT** to the port shown by Joplin (default `41184`).
3. Make sure a notebook named **_Inbox** exists. **JOPLIN_NOTEBOOK** is already set to `_Inbox`; change it to choose another default notebook. The name must be unique.

Keep Joplin running while using the workflow.

- `js foo`: search note titles and contents using Joplin's search syntax. Select a result and press Return to open it. Shows up to 100 results; refine the query if there are more.
- `jn bar`: press Return to create an empty note titled `bar` in `_Inbox` and open it. Typing alone never creates a note.
- `jj foo blah hah`: press Return to append `foo blah hah` on a new line at the end of the existing `SCRATCHPAD` note in `_Inbox`. A notification confirms the append. Set **JOPLIN_APPEND_NOTE** and **JOPLIN_APPEND_NOTEBOOK** to change the destination. The note must already exist and its title must be unique within that notebook. Typing alone never changes the note.

Errors appear in Alfred for search/creation previews and in notifications for actions. No notebook is created automatically. The export contains no API token; re-exporting after configuration may include your token, so remove it before sharing.

Rebuild the importable archive with `python3 build.py`. Run the API integration tests with `python3 -m unittest discover -s tests -v`.

References: [Joplin Data API](https://joplinapp.org/help/api/references/rest_api/), [Joplin external links](https://joplinapp.org/help/apps/external_links/), [Alfred Script Filters](https://www.alfredapp.com/help/workflows/inputs/script-filter/).

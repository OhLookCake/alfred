# Pickleballtv for Alfred

Double-click `Pickleballtv.alfredworkflow` to import it into Alfred. Requires Alfred with Powerpack and `/usr/bin/python3` (available on this Mac).

Type `pb ` to fetch the ten newest uploads from https://www.youtube.com/@Pickleballtv/videos. Use ↑/↓ to select a video, then press Return or activate the result with the mouse to open it in your default browser. Uploads stay in newest-first order. Titles and the available upload age/view count appear in the list.

No API key, login, or additional packages are needed. Each invocation fetches the current Videos page; an internet connection is required. If YouTube blocks the request or changes its page structure, the workflow offers to open the channel instead.

Build: `/usr/bin/python3 build.py` from this directory. Tests: `/usr/bin/python3 -m unittest discover -s tests -v`.

"""Generate the workflow plist and distributable archive."""
from pathlib import Path
import plistlib
import zipfile

ROOT = Path(__file__).resolve().parent
objects = []
connections = {}
positions = {}


def add(uid, kind, config, version, x, y):
    objects.append(dict(uid=uid, type='alfred.workflow.' + kind, config=config, version=version))
    positions[uid] = dict(xpos=x, ypos=y)


def connect(source, destination):
    connections[source] = [dict(destinationuid=destination, modifiers=0, modifiersubtext='', vitoclose=False)]


for keyword, mode, action, y in [('js', 'search', 'open', 100), ('jn', 'preview', 'create', 280),
                                 ('jj', 'append-preview', 'append', 460)]:
    script = 'exec /usr/bin/python3 joplin.py %s "$1"'
    add(keyword, 'input.scriptfilter', dict(keyword=keyword, withspace=True, argumenttype=1,
        argumenttrimmode=0, argumenttreatemptyqueryasnil=False, alfredfiltersresults=False,
        alfredfiltersresultsmatchmode=0, escaping=0, script=script % mode,
        scriptargtype=1, scriptfile='', type=0, queuedelaycustom=3, queuedelaymode=0,
        queuedelayimmediatelyinitially=True, queuemode=2, runningsubtext='Connecting to Joplin…',
        title={'js': 'Search Joplin', 'jn': 'New Joplin note', 'jj': 'Append to Joplin note'}[keyword], subtext=''), 3, 100, y)
    add(action, 'action.script', dict(script=script % action, scriptargtype=1, scriptfile='',
        type=0, escaping=0, concurrently=False), 2, 360, y)
    connect(keyword, action)
add('notification', 'output.notification', dict(title='Joplin', text='{query}', onlyshowifquerypopulated=True,
    lastpathcomponent=False, removeextension=False), 1, 600, 280)
connect('create', 'notification')
connect('append', 'notification')
fields = [('JOPLIN_TOKEN', '', 'API token from Joplin → Settings → Web Clipper.'),
          ('JOPLIN_NOTEBOOK', '_Inbox', 'Exact, unique notebook name for new notes.'),
          ('JOPLIN_APPEND_NOTEBOOK', '_Inbox', 'Exact, unique notebook name containing the append destination.'),
          ('JOPLIN_APPEND_NOTE', 'SCRATCHPAD', 'Exact note title for jj; must be unique within the destination notebook.'),
          ('JOPLIN_PORT', '41184', 'Local Web Clipper port shown in Joplin settings.')]
config = [dict(variable=name, label=name, type='textfield', description=description,
               config=dict(default=default, placeholder=default, required=True, trim=True))
          for name, default, description in fields]
workflow = dict(bundleid='local.ee.joplin', name='Joplin', description='Search, create, and append to Joplin notes',
    createdby='ee', version='1.1.0', disabled=False, objects=objects, connections=connections,
    uidata=positions, variables={name: default for name, default, _ in fields},
    userconfigurationconfig=config, readme=(ROOT / 'README.md').read_text())
with (ROOT / 'joplin/info.plist').open('wb') as file:
    plistlib.dump(workflow, file)
with zipfile.ZipFile(ROOT / 'Joplin.alfredworkflow', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ('info.plist', 'joplin.py'):
        archive.write(ROOT / 'joplin' / name, name)
print('Built Joplin.alfredworkflow')

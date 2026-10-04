from pathlib import Path
import plistlib
import zipfile

ROOT = Path(__file__).resolve().parent
workflow = dict(bundleid='local.ee.pickleballtv', name='Pickleballtv', createdby='ee',
    description='Browse the 10 latest Pickleballtv uploads', version='1.0.0', disabled=False,
    readme=(ROOT / 'README.md').read_text(),
    objects=[dict(uid='videos', type='alfred.workflow.input.scriptfilter', version=3, config=dict(
        keyword='pb', withspace=True, argumenttype=1, argumenttrimmode=0,
        argumenttreatemptyqueryasnil=False, alfredfiltersresults=False, alfredfiltersresultsmatchmode=0,
        escaping=0, script='exec /usr/bin/python3 videos.py', scriptargtype=1, scriptfile='', type=0,
        queuedelaycustom=3, queuedelaymode=0, queuedelayimmediatelyinitially=True, queuemode=2,
        runningsubtext='Loading the latest Pickleballtv uploads…', title='Latest Pickleballtv videos',
        subtext='Browse the newest 10 uploads')),
        dict(uid='browser', type='alfred.workflow.action.script', version=2, config=dict(
            script='exec /usr/bin/open "$1"', scriptargtype=1, scriptfile='', type=0,
            escaping=0, concurrently=False))],
    connections={'videos': [dict(destinationuid='browser', modifiers=0, modifiersubtext='', vitoclose=False)]},
    uidata={'videos': dict(xpos=100, ypos=100), 'browser': dict(xpos=360, ypos=100)})
with (ROOT / 'info.plist').open('wb') as file:
    plistlib.dump(workflow, file)
with zipfile.ZipFile(ROOT.parent / 'Pickleballtv.alfredworkflow', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ('info.plist', 'videos.py'):
        archive.write(ROOT / name, name)
print('Built Pickleballtv.alfredworkflow')

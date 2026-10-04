#!/usr/bin/env python3
"""Joplin's local Data API -> Alfred. No third-party dependencies."""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


class WorkflowError(Exception):
    pass


class Joplin:
    def __init__(self):
        self.token = os.environ.get('JOPLIN_TOKEN', '').strip()
        if not self.token:
            raise WorkflowError('Set JOPLIN_TOKEN in Configure Workflow using Joplin → Settings → Web Clipper.')
        port = os.environ.get('JOPLIN_PORT', '41184').strip()
        if not port.isdigit() or not 1 <= int(port) <= 65535:
            raise WorkflowError('JOPLIN_PORT must be a port number (normally 41184).')
        self.base = 'http://127.0.0.1:' + port
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, path, params=None, data=None, method=None):
        params = dict(params or {}, token=self.token)
        url = self.base + path + '?' + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode('utf-8'),
                                         headers={'Content-Type': 'application/json'}, method=method)
        try:
            with self.opener.open(request, timeout=5) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code in (401, 403):
                raise WorkflowError('Joplin rejected the token. Copy the API token from Settings → Web Clipper.') from None
            raise WorkflowError('Joplin API returned HTTP %s. Check Joplin and your query.' % error.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise WorkflowError('Cannot reach Joplin. Open Joplin, enable Web Clipper, and check JOPLIN_PORT.') from None
        except ValueError:
            raise WorkflowError('Unexpected response from Joplin. Check JOPLIN_PORT.') from None

    def all_items(self, path, params=None):
        page = 1
        while True:
            result = self.request(path, dict(params or {}, page=page, limit=100))
            yield from result.get('items', [])
            if not result.get('has_more'):
                break
            page += 1

    def notebook(self, variable='JOPLIN_NOTEBOOK'):
        name = os.environ.get(variable, '_Inbox').strip() or '_Inbox'
        matches = [f for f in self.all_items('/folders', {'fields': 'id,title'}) if f['title'] == name]
        if not matches:
            raise WorkflowError('Notebook "%s" not found. Create it in Joplin or change %s.' % (name, variable))
        if len(matches) > 1:
            raise WorkflowError('Multiple notebooks named "%s". Give the destination notebook a unique name.' % name)
        return matches[0]

    def scratchpad(self):
        folder = self.notebook('JOPLIN_APPEND_NOTEBOOK')
        title = os.environ.get('JOPLIN_APPEND_NOTE', 'SCRATCHPAD').strip() or 'SCRATCHPAD'
        matches = [n for n in self.all_items('/folders/%s/notes' % folder['id'],
                   {'fields': 'id,title'}) if n['title'] == title]
        if len(matches) != 1:
            raise WorkflowError('Expected one note named "%s" in "%s"; found %s. Check the destination in Joplin.'
                                % (title, folder['title'], len(matches)))
        return folder, matches[0]


def emit(items):
    print(json.dumps({'items': items}, ensure_ascii=False))


def message(title, subtitle=''):
    return {'title': title, 'subtitle': subtitle, 'valid': False}


def open_note(note_id):
    if not re.fullmatch(r'[a-fA-F0-9]{32}', note_id):
        raise WorkflowError('Invalid Joplin note ID.')
    subprocess.run(['/usr/bin/open', 'joplin://x-callback-url/openNote?id=' + note_id], check=True)


def main(mode, query):
    if mode == 'open':
        open_note(query)
    elif mode == 'search':
        if not query.strip():
            emit([message('Search Joplin', 'Type a search query; Joplin search syntax is supported.')])
            return
        api = Joplin()
        result = api.request('/search', {'query': query, 'fields': 'id,title,parent_id', 'limit': 100})
        notes = result.get('items', [])
        items = [{'uid': n['id'], 'title': n.get('title') or 'Untitled', 'subtitle': 'Open in Joplin',
                  'arg': n['id'], 'valid': True} for n in notes]
        if result.get('has_more'):
            items.append(message('Showing the first 100 results', 'Refine your search to find more specific notes.'))
        emit(items or [message('No matching notes', 'Try another Joplin search query.')])
    elif mode == 'preview':
        title = query.strip()
        if not title:
            emit([message('New Joplin note', 'Type a title, then press Return to create the note.')])
            return
        folder = Joplin().notebook()
        emit([{'title': 'Create “%s”' % title, 'subtitle': 'Create in %s and open in Joplin' % folder['title'],
               'arg': title, 'valid': True}])
    elif mode in ('append-preview', 'append'):
        if not query.strip():
            if mode == 'append-preview':
                emit([message('Append to Joplin note', 'Type text, then press Return to append it.')])
                return
            raise WorkflowError('Enter text to append.')
        api = Joplin()
        folder, note = api.scratchpad()
        if mode == 'append-preview':
            emit([{'title': 'Append to %s' % note['title'],
                   'subtitle': '%s: %s' % (folder['title'], query), 'arg': query, 'valid': True}])
            return
        current = api.request('/notes/%s' % note['id'], {'fields': 'id,body'})
        body = current['body']
        separator = '\n' if body and not body.endswith('\n') else ''
        api.request('/notes/%s' % note['id'], data={'body': body + separator + query + '\n'}, method='PUT')
        print('Appended to "%s" in %s' % (note['title'], folder['title']))
    elif mode == 'create':
        title = query.strip()
        if not title:
            raise WorkflowError('Enter a note title.')
        api = Joplin()
        folder = api.notebook()
        note = api.request('/notes', data={'title': title, 'parent_id': folder['id'], 'body': ''})
        try:
            open_note(note['id'])
        except (subprocess.CalledProcessError, WorkflowError):
            print('Created "%s" in %s. Open Joplin to view it.' % (title, folder['title']))
            return
        print('Created "%s" in %s' % (title, folder['title']))
    else:
        raise WorkflowError('Unknown workflow command.')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'search'
    try:
        main(mode, sys.argv[2] if len(sys.argv) > 2 else '')
    except (WorkflowError, subprocess.CalledProcessError) as error:
        if mode in ('search', 'preview', 'append-preview'):
            emit([message('Joplin: setup or connection problem', str(error))])
        else:
            print(str(error))

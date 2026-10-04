import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

spec = importlib.util.spec_from_file_location('workflow', Path(__file__).resolve().parents[1] / 'joplin/joplin.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.folders = [{'id': 'b' * 32, 'title': '_Inbox'}]
        self.notes = [{'id': 'd' * 32, 'title': 'SCRATCHPAD'}]
        self.body = 'Existing text'
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlsplit(self.path)
                params = parse_qs(parsed.query)
                owner.requests.append((parsed.path, params))
                if params.get('token') != ['test-token']:
                    self.send_response(403)
                    self.end_headers()
                    return
                if parsed.path == '/notes/' + 'd' * 32:
                    response = {'id': 'd' * 32, 'body': owner.body}
                elif parsed.path == '/folders/' + 'b' * 32 + '/notes':
                    page = int(params['page'][0])
                    response = {'items': [] if page == 1 else owner.notes, 'has_more': page == 1}
                elif parsed.path == '/search':
                    response = {'items': [{'id': 'a' * 32, 'title': 'Found note'}], 'has_more': False}
                else:
                    page = int(params['page'][0])
                    response = {'items': [] if page == 1 else owner.folders, 'has_more': page == 1}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            def do_POST(self):
                owner.requests.append((urlsplit(self.path).path, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'id': 'c' * 32}).encode())

            def do_PUT(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append(('PUT ' + urlsplit(self.path).path, data))
                owner.body = data['body']
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'id': 'd' * 32}).encode())

            def log_message(self, *args):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.env = patch.dict(os.environ, JOPLIN_TOKEN='test-token', JOPLIN_PORT=str(self.server.server_port), JOPLIN_NOTEBOOK='_Inbox',
                              JOPLIN_APPEND_NOTEBOOK='_Inbox', JOPLIN_APPEND_NOTE='SCRATCHPAD')
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_mode(self, mode, query):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            w.main(mode, query)
        return output.getvalue()

    def test_search_preserves_special_characters(self):
        query = 'foo & title:"café" $(touch /tmp/nope)'
        result = json.loads(self.run_mode('search', query))
        self.assertEqual(self.requests[0][1]['query'], [query])
        self.assertEqual(result['items'][0]['arg'], 'a' * 32)

    def test_preview_paginates_without_creating(self):
        result = json.loads(self.run_mode('preview', 'bar'))
        self.assertTrue(result['items'][0]['valid'])
        self.assertEqual([p for p, _ in self.requests], ['/folders', '/folders'])

    def test_creation_uses_inbox_and_opens_note(self):
        title = 'bar "quoted" café $HOME'
        with patch.object(w.subprocess, 'run') as opened:
            self.run_mode('create', title)
        self.assertEqual(self.requests[-1], ('/notes', {'title': title, 'parent_id': 'b' * 32, 'body': ''}))
        opened.assert_called_once_with(['/usr/bin/open', 'joplin://x-callback-url/openNote?id=' + 'c' * 32], check=True)

    def test_missing_or_ambiguous_notebook_never_creates(self):
        for folders in ([], self.folders * 2):
            self.folders = folders
            with self.assertRaises(w.WorkflowError):
                self.run_mode('create', 'bar')
        self.assertFalse(any(p == '/notes' for p, _ in self.requests))

    def test_missing_and_invalid_token(self):
        with patch.dict(os.environ, JOPLIN_TOKEN=''):
            with self.assertRaises(w.WorkflowError):
                w.Joplin()
        with patch.dict(os.environ, JOPLIN_TOKEN='wrong'):
            with self.assertRaisesRegex(w.WorkflowError, 'rejected the token'):
                self.run_mode('search', 'foo')

    def test_blank_title_never_creates(self):
        with self.assertRaises(w.WorkflowError):
            self.run_mode('create', '  ')
        self.assertEqual(self.requests, [])

    def test_append_preserves_body_and_text(self):
        text = 'foo blah hah "café" $HOME\nsecond line'
        for body in ('Existing text', 'Existing text\n', ''):
            self.body = body
            self.run_mode('append', text)
            expected = body + ('\n' if body and not body.endswith('\n') else '') + text + '\n'
            self.assertEqual(self.body, expected)
            self.assertEqual(self.requests[-1], ('PUT /notes/' + 'd' * 32, {'body': expected}))

    def test_append_preview_does_not_write(self):
        result = json.loads(self.run_mode('append-preview', 'foo blah hah'))
        self.assertEqual(result['items'][0]['arg'], 'foo blah hah')
        self.assertFalse(any(path.startswith('PUT ') for path, _ in self.requests))

    def test_append_missing_duplicate_or_blank_never_writes(self):
        for notes in ([], self.notes * 2):
            self.notes = notes
            with self.assertRaises(w.WorkflowError):
                self.run_mode('append', 'foo')
        with self.assertRaises(w.WorkflowError):
            self.run_mode('append', ' ')
        self.assertFalse(any(path.startswith('PUT ') for path, _ in self.requests))


if __name__ == '__main__':
    unittest.main()

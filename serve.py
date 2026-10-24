#!/usr/bin/env python3
"""Serve the Flashcard Template Maker on localhost and connect it to VoiceStudio.

Browsers block a page opened from a file from calling VoiceStudio's local API,
and VoiceStudio only accepts its own window by default. This script serves
index.html at http://localhost:8765 and forwards /voicestudio/* to VoiceStudio,
so the page and the speech API share one address. Nothing leaves your computer.

On Windows, just double-click "Start Flashcards". It runs this script.

Usage:
    python3 serve.py                      # then pick Play > Voice mode > VoiceStudio
    python3 serve.py --port 9000
    python3 serve.py --voicestudio http://127.0.0.1:3900

Needs Python 3.7 or later and nothing else.
"""
import argparse
import http.server
import json
import os
import sys
import urllib.error
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
PREFIX = '/voicestudio'
# Headers that describe one connection, or that would make VoiceStudio treat the
# request as coming from another web page, are not passed on.
SKIP_REQUEST = {'connection', 'keep-alive', 'proxy-connection', 'te', 'trailer', 'transfer-encoding', 'upgrade',
                'host', 'content-length', 'origin', 'referer', 'cookie'}
SKIP_RESPONSE = {'connection', 'keep-alive', 'proxy-connection', 'te', 'trailer', 'transfer-encoding', 'upgrade',
                 'content-length', 'set-cookie', 'access-control-allow-origin', 'access-control-allow-credentials'}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = 'FlashcardServe/1.0'

    def do_GET(self):
        self.route('GET')

    def do_HEAD(self):
        self.route('HEAD')

    def do_POST(self):
        self.route('POST')

    def route(self, method):
        path = self.path.split('?', 1)[0]
        if path == PREFIX or path.startswith(PREFIX + '/'):
            self.forward(method)
        elif path in ('/', '/index.html') and method in ('GET', 'HEAD'):
            self.send_index(method)
        else:
            self.send_json(404, {'error': {'message': 'Not found', 'code': 'not_found'}})

    def send_index(self, method):
        with open(os.path.join(ROOT, 'index.html'), 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        if method != 'HEAD':
            self.wfile.write(data)

    def forward(self, method):
        upstream = self.server.upstream
        url = upstream + (self.path[len(PREFIX):] or '/')
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in SKIP_REQUEST}
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            resp = e
        except (urllib.error.URLError, OSError):
            self.send_json(502, {'error': {
                'message': 'serve.py is running, but VoiceStudio is not reachable at ' + upstream +
                           '. Open VoiceStudio, wait until it has started, then press Connect.',
                'code': 'voicestudio_unreachable'}})
            return
        with resp:
            data = resp.read()
            self.send_response(getattr(resp, 'status', None) or resp.code)
            for k, v in resp.headers.items():
                if k.lower() not in SKIP_RESPONSE:
                    self.send_header(k, v)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            if method != 'HEAD':
                self.wfile.write(data)

    def send_json(self, status, obj):
        data = json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        # Only report problems, not every speech clip.
        if len(args) > 1 and str(args[1])[:1] in ('4', '5'):
            sys.stderr.write('%s %s\n' % (self.log_date_time_string(), fmt % args))


class Server(http.server.ThreadingHTTPServer):
    # On Windows, address reuse lets two programs share one port, so a busy port would not be noticed.
    allow_reuse_address = os.name != 'nt'
    daemon_threads = True


def flashcards_at(port):
    """True when this app is already being served on the port."""
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/' % port, timeout=2) as r:
            return b'Flashcard Template Maker' in r.read(4000)
    except Exception:
        return False


def voicestudio_running(upstream):
    try:
        with urllib.request.urlopen(upstream + '/health', timeout=3):
            return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description='Serve the Flashcard Template Maker and connect it to VoiceStudio.')
    ap.add_argument('--port', type=int, default=8765, help='port for the app (default 8765)')
    ap.add_argument('--voicestudio', default=os.environ.get('VOICESTUDIO_URL', 'http://127.0.0.1:3900'),
                    help='VoiceStudio address (default http://127.0.0.1:3900, or $VOICESTUDIO_URL)')
    ap.add_argument('--no-browser', action='store_true', help='do not open the browser')
    args = ap.parse_args()

    # If the port is busy because the flashcards are already open, reuse that copy;
    # otherwise try the next few ports.
    server = None
    for port in range(args.port, args.port + 11):
        try:
            server = Server(('127.0.0.1', port), Handler)
            break
        except OSError:
            if flashcards_at(port):
                url = 'http://localhost:%d/' % port
                print('Flashcards is already running. Opening it in your browser: ' + url)
                if not args.no_browser:
                    webbrowser.open(url)
                return
    if server is None:
        sys.exit('Could not start: ports %d to %d are all in use. Restart the computer and try again.' % (args.port, args.port + 10))
    server.upstream = args.voicestudio.rstrip('/')
    url = 'http://localhost:%d/' % server.server_address[1]

    print('')
    print('  Flashcards is running.')
    print('  Your browser should open by itself. If it does not, open this address:')
    print('      ' + url)
    print('')
    if voicestudio_running(server.upstream):
        print('  VoiceStudio is open and ready for voice mode.')
    else:
        print('  VoiceStudio is not open yet. Open it before using voice mode;')
        print('  the flashcards page will notice when it is ready.')
    print('')
    print('  Keep this window open while you play. Close it when you are done.')
    print('')
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()

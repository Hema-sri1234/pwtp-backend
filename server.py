from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
import json
import os
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / 'data.json'


def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            pass
    return {'projects': [], 'analyses': []}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/':
        self._send_json(200, {
            'message': 'PWTP Backend Running Successfully'
        })
        return

        if parsed.path == '/api/projects':
            data = load_data()
            self._send_json(200, data.get('projects', []))
            return

        if parsed.path == '/api/analysis':
            data = load_data()
            self._send_json(200, data.get('analyses', []))
            return

        if parsed.path == '/api/module-design':
            data = load_data()
            self._send_json(200, data.get('moduleDesigns', []))
            return

        if parsed.path == '/':
            file_path = ROOT / 'index.html'
        else:
            file_path = ROOT / parsed.path.lstrip('/')

        if file_path.exists() and file_path.is_file():
            content_type = 'text/html' if file_path.suffix == '.html' else 'application/javascript' if file_path.suffix == '.js' else 'text/css'
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self._send_json(404, {'error': 'Not found'})

    def do_POST(self):
        if self.path in ['/api/projects', '/api/analysis','/api/module-design','/api/ai']:
            content_length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                payload = json.loads(body or '{}')
            except json.JSONDecodeError:
                self._send_json(400, {'error': 'Invalid JSON'})
                return

            if self.path == '/api/projects':
                data = load_data()
                projects = data.get('projects', [])
                projects.insert(0, payload)
                data['projects'] = projects
                save_data(data)
                self._send_json(201, payload)
                return

            if self.path == '/api/analysis':
                data = load_data()
                analyses = data.get('analyses', [])
                analyses.append(payload)
                data['analyses'] = analyses
                save_data(data)
                self._send_json(201, payload)
                return

            if self.path == '/api/module-design':
                data = load_data()
                designs = data.get('moduleDesigns', [])
                designs.append(payload)
                data['moduleDesigns'] = designs
                save_data(data)
                self._send_json(201, payload)
                return

            if self.path == '/api/ai':
                api_key = payload.get('apiKey') or os.getenv('OPENROUTER_API_KEY')
                prompt = payload.get('prompt', '')
                model = payload.get('model', 'openai/gpt-4.1-mini')

                if not api_key or not prompt:
                    self._send_json(400, {'error': 'API key and prompt are required'})
                    return

                request_payload = {
                    'model': model,
                    'messages': [{'role': 'user', 'content': prompt}]
                }

                req = urllib.request.Request(
                    'https://openrouter.ai/api/v1/chat/completions',
                    data=json.dumps(request_payload).encode('utf-8'),
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                        'HTTP-Referer': 'http://127.0.0.1:8000',
                        'X-Title': 'PWTP Platform'
                    },
                    method='POST'
                )

                try:
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        response_text = resp.read().decode('utf-8')
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(response_text.encode('utf-8'))
                except urllib.error.HTTPError as exc:
                    error_text = exc.read().decode('utf-8', errors='ignore')
                    self._send_json(exc.code, {'error': error_text})
                except Exception as exc:  # pragma: no cover
                    self._send_json(502, {'error': str(exc)})
                return

        self._send_json(404, {'error': 'Not found'})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'PWTP server running on port {port}')
    server.serve_forever()

"""Optional local HTTP server for exported presentations, bound to localhost only."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
if __name__ == '__main__':
    print('Open http://127.0.0.1:8765/TCC_Worship_Live.html in your browser.')
    ThreadingHTTPServer(('127.0.0.1',8765),SimpleHTTPRequestHandler).serve_forever()

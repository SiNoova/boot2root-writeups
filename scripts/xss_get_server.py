#!/usr/bin/env python3

from datetime import datetime, timezone
from flask import Flask, request, Response

app = Flask(__name__)

@app.get('/c')
@app.get('/collect')
def collect():
    marker = request.args.get('test', 'received')[:200]
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    ip = request.remote_addr
    print(f'[{timestamp}] GET from {ip}: test={marker!r}', flush=True)
    return Response('OK\n', mimetype='text/plain')

@app.get('/')
def index():
    return Response('GET callback server is running. Use /c?test=hello\n', mimetype='text/plain')

if __name__ == '__main__':
    print('Listening on http://0.0.0.0:8888', flush=True)
    app.run(host='0.0.0.0', port=8888, debug=False)

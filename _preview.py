"""Temporary helper: browse the redesigned UI without a MySQL server.

Run it and open http://127.0.0.1:5050/ ; the data comes from the in-memory
fixtures in _stub_app.py, so writes are not persisted.

Shortcuts:
    /_login_as/PeterLu   log in as the admin fixture user
    /_login_as/Bronia    log in as a normal fixture user
    /_logout             clear the session
"""
from flask import redirect, request, session

from _stub_app import app

PORT = 5050


@app.route('/_login_as/<name>')
def _login_as(name):
    session['username'] = name
    session['theme'] = request.args.get('theme', session.get('theme', 'white'))
    return redirect(request.args.get('next', '/'))


@app.route('/_logout')
def _logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    print('preview on http://127.0.0.1:%d/  (login: /_login_as/PeterLu)' % PORT)
    app.run(port=PORT, use_reloader=False, threaded=True)

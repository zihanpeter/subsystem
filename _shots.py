"""Temporary visual check: serves the stubbed app and screenshots the pages."""
import os
import threading
import time

from flask import redirect, request, session

from _stub_app import app

PORT = 5099
BASE = 'http://127.0.0.1:%d' % PORT
OUT = '_shots'


@app.route('/_login_as/<name>')
def _login_as(name):
    session['username'] = name
    session['theme'] = request.args.get('theme', 'white')
    return redirect('/')


@app.route('/_logout')
def _logout():
    session.clear()
    return redirect('/')


def serve():
    app.run(port=PORT, use_reloader=False, threaded=True)


threading.Thread(target=serve, daemon=True).start()
time.sleep(2)

GAMES = ['TetrisGame', 'TwoPlayersTetrisGame', 'MinesweeperGame', 'WordleGame',
         'GreedySnakeGame', 'FruitNinjaGame', 'MarioGame', 'PinballGame', 'PlaneWarsGame',
         'T-RexDinoGame', 'TwentyFortyEightGame']

PAGES = [
    ('home', '/'),
    ('forum', '/forum'),
    ('article', '/articles?id=a1'),
    ('reciter', '/reciter'),
    ('wordlist', '/show_list?id=9f0c1a52-1234-11ef-bf2b-57fb35f9416a'),
    ('recite-spelling', '/recite?id=9f0c1a52-1234-11ef-bf2b-57fb35f9416a&pattern=Learn spelling'),
    ('recite-meaning', '/recite?id=9f0c1a52-1234-11ef-bf2b-57fb35f9416a&pattern=Learn meaning'),
    ('login', '/login'),
    ('register', '/register'),
    ('profile', '/profile?username=PeterLu'),
    ('users', '/userlist'),
    ('yule', '/yule'),
    ('game-intro', '/intro?name=TetrisGame'),
    ('game-tetris', '/games?name=TetrisGame'),
    ('create-list', '/create'),
    ('confirm-delete', '/check_del_articles?id=a1'),
]

os.makedirs(OUT, exist_ok=True)

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    browser = p.chromium.launch()

    # every game page once, to check the shared bar against each game's own layout
    ctx = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = ctx.new_page()
    page.goto('%s/_login_as/PeterLu?theme=white' % BASE, wait_until='load')
    for game in GAMES:
        page.goto('%s/games?name=%s' % (BASE, game), wait_until='load')
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(OUT, 'game-%s.png' % game))
        print('shot game', game)
    ctx.close()

    for theme in ('white', 'black'):
        ctx = browser.new_context(viewport={'width': 1280, 'height': 900},
                                  device_scale_factor=1)
        page = ctx.new_page()
        page.goto('%s/_login_as/PeterLu?theme=%s' % (BASE, theme), wait_until='load')
        for name, url in PAGES:
            page.goto(BASE + url, wait_until='load')
            page.wait_for_timeout(700)
            page.screenshot(path=os.path.join(OUT, '%s-%s.png' % (theme, name)), full_page=True)
            print('shot', theme, name)
        ctx.close()

    # mobile, logged out
    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    page = ctx.new_page()
    for name, url in [('home', '/'), ('forum', '/forum'), ('login', '/login')]:
        page.goto(BASE + url, wait_until='load')
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT, 'mobile-%s.png' % name), full_page=True)
        print('shot mobile', name)
    # mobile nav open
    page.goto(BASE + '/', wait_until='load')
    page.click('[data-nav-toggle]')
    page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(OUT, 'mobile-nav-open.png'))
    ctx.close()
    browser.close()

print('done')

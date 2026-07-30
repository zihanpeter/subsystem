"""Temporary render smoke test: requests every page in both themes."""
import os
import sys

from _stub_app import app

GET_ROUTES = [
    '/', '/reciter', '/forum', '/forum?show_mode=rest', '/yule', '/userlist', '/login', '/register',
    '/profile?username=PeterLu', '/profile?username=Bronia', '/create', '/create_articles',
    '/articles?id=a1', '/articles?id=a1&sorter=positive', '/check_del_articles?id=a1',
    '/modify_articles?id=a1', '/show_list?id=l2', '/check_del_list?id=l2', '/modify_list?id=l2',
    '/recite?id=l2&pattern=Learn meaning', '/recite?id=l2&pattern=Learn spelling',
    '/modify_intro?username=PeterLu', '/intro?name=TetrisGame', '/games?name=TetrisGame',
    '/games?name=WordleGame', '/games?name=MinesweeperGame', '/games?name=GreedySnakeGame',
]

ANON_ROUTES = ['/', '/forum', '/articles?id=a1', '/login', '/register', '/userlist',
               '/profile?username=PeterLu', '/yule', '/intro?name=TetrisGame', '/reciter',
               '/show_list?id=l2']

out_dir = '_smoke_out'
os.makedirs(out_dir, exist_ok=True)
failures = []


def fetch(client, tag, url):
    try:
        r = client.get(url)
    except Exception as exc:  # noqa: BLE001
        failures.append((tag, url, 'EXC: %r' % (exc,)))
        return
    if r.status_code != 200:
        failures.append((tag, url, 'HTTP %s' % r.status_code))
        return
    name = url.replace('/', '_').replace('?', '-').replace('&', '-').replace('=', '_')
    with open(os.path.join(out_dir, '%s%s.html' % (tag, name)), 'w', encoding='utf-8') as f:
        f.write(r.get_data(as_text=True))


count = 0
for theme in ('white', 'black'):
    client = app.test_client()
    with client.session_transaction() as s:
        s['username'] = 'PeterLu'
        s['theme'] = theme
        s['captcha'] = 'abcd'
    for url in GET_ROUTES:
        fetch(client, theme, url)
        count += 1

client = app.test_client()
for url in ANON_ROUTES:
    fetch(client, 'anon', url)
    count += 1

client = app.test_client()
with client.session_transaction() as s:
    s['username'] = 'PeterLu'
    s['theme'] = 'white'
print('change_theme ->', client.post('/change_theme',
                                     data={'theme': 'black', 'next': '/forum'}).headers.get('Location'))
print('change_theme (bad next) ->', client.post('/change_theme',
                                                data={'theme': 'black',
                                                      'next': 'http://evil.example.com'}).headers.get('Location'))
print('change_theme anonymous ->', app.test_client().post('/change_theme',
                                                          data={'theme': 'black', 'next': '/'}).headers.get('Location'))

if failures:
    print('\nFAILURES:')
    for tag, url, why in failures:
        print(' ', tag, url, '->', why)
    sys.exit(1)
print('\nAll %d page renders OK.' % count)

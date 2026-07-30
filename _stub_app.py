"""Temporary helper: the real Flask app wired to in-memory data instead of MySQL."""
import io
import sys
import types

# --- stub mysql.connector -----------------------------------------------------
mysql = types.ModuleType('mysql')
connector = types.ModuleType('mysql.connector')


class Error(Exception):
    pass


connector.Error = Error
connector.connect = lambda **kw: (_ for _ in ()).throw(Error('no db in smoke test'))
mysql.connector = connector
sys.modules['mysql'] = mysql
sys.modules['mysql.connector'] = connector

# --- stub captcha.image -------------------------------------------------------
captcha = types.ModuleType('captcha')
image_mod = types.ModuleType('captcha.image')

_PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00Z\x00\x00\x002\x08\x02\x00\x00\x00'
        b'\x9d\xb5\xd6\x91\x00\x00\x00\x1fIDATx\x9c\xed\xc1\x01\r\x00\x00\x00\xc2\xa0\xf7Om'
        b'\x0e7\xa0\x00\x00\x00\x00\x00\x00\x00\x00\xbe\r!\x00\x00\x01\x9a`\xe1\xd5\x00\x00'
        b'\x00\x00IEND\xaeB`\x82')


class ImageCaptcha:
    def __init__(self, **kw):
        pass

    def generate(self, text):
        return io.BytesIO(_PNG)


image_mod.ImageCaptcha = ImageCaptcha
captcha.image = image_mod
sys.modules['captcha'] = captcha
sys.modules['captcha.image'] = image_mod

from lib import dbConnecter  # noqa: E402

USERS = [
    {'username': 'PeterLu', 'password': 'x', 'timef': '2024-01-01 10:00', 'theme': 'white',
     'admin': 1,
     'intro': ('# Hello\n\nI am **PeterLu**, and I like $e^{i\\pi} = -1$.\n\n'
               '- Reciter maintainer\n- Forum moderator\n\n```py\nprint("hi")\n```\n')},
    {'username': 'Bronia', 'password': 'x', 'timef': '2024-02-03 09:30', 'theme': 'black',
     'admin': 0, 'intro': 'Nothing'},
    {'username': 'ycy', 'password': 'x', 'timef': '2024-02-10 19:30', 'theme': 'white',
     'admin': 0, 'intro': 'Games developer.'},
]

LISTS = [
    {'id': '9f0c1a52-1234-11ef-bf2b-57fb35f9416a', 'username': 'PeterLu',
     'listname': 'CET-6 unit 1', 'difficulty': 3, 'en': 'hello|banana|elaborate|',
     'zh': '你好|香蕉|详尽阐述|', 'sen': 'Hello everyone!|(CASE)|Please elaborate.|',
     'timef': '2024-03-01 12:00', 'o': 1, 'sm': 1},
    {'id': 'l2', 'username': 'Bronia', 'listname': 'Community words', 'difficulty': 1,
     'en': 'cat|dog|', 'zh': '猫|狗|', 'sen': '', 'timef': '2024-04-01 12:00', 'o': 0, 'sm': 0},
    {'id': 'l3', 'username': 'ycy', 'listname': 'Hard words', 'difficulty': 5,
     'en': 'quixotic|', 'zh': '不切实际的|', 'sen': '', 'timef': '2024-04-11 12:00',
     'o': 1, 'sm': 0},
]

ARTICLES = [
    {'id': 'a1', 'username': 'PeterLu', 'title': 'Welcome to the Subsystem forum', 'top': 1,
     'timef': '2024-05-01 08:00',
     'content': ('## House rules\n\nBe kind, stay on topic, and use Markdown.\n\n'
                 '| Operation | Button |\n|-|-|\n| Continue | Down / S |\n| Know | Left / A |\n\n'
                 '> Quotes look like this.\n\nInline math $x^2 + y^2 = z^2$ works too.\n\n'
                 '```python\ndef hello():\n    return "world"\n```\n')},
    {'id': 'a2', 'username': 'Bronia', 'title': 'Feature request: dark mode everywhere', 'top': 0,
     'timef': '2024-06-01 08:00', 'content': 'It would be nice to have consistent theming.'},
    {'id': '0df4c672-b375-11ef-bf2b-57fb35f9416a', 'username': 'ycy',
     'title': 'Yule Feedback Center', 'top': 1, 'timef': '2024-12-01 08:00',
     'content': 'Tell us about the games.'},
]

COMMENTS = [
    {'id': 'a1', 'username': 'Bronia', 'content': 'Great, thanks for writing this down!',
     'timef': '2024-05-02 09:00', 'to1': None},
    {'id': 'a1', 'username': 'PeterLu',
     'content': '@Bronia\r\nGlad it helps. Ping me if anything is unclear.',
     'timef': '2024-05-02 10:00', 'to1': 'Bronia'},
]

YULE = [
    {'name': 'TetrisGame', 'hot': 142, 'path': 'yule/source/TetrisGame.html',
     'intro': 'static/md/yule/TetrisGameIntro.md', 'timef': '2024-12-01 10:00', 'creator': 'ycy'},
    {'name': 'WordleGame', 'hot': 96, 'path': 'yule/source/WordleGame.html',
     'intro': 'static/md/yule/WordelGameIntro.md', 'timef': '2024-12-02 10:00', 'creator': 'ycy'},
    {'name': 'MinesweeperGame', 'hot': 61, 'path': 'yule/source/MinesweeperGame.html',
     'intro': 'static/md/yule/MinesweeperGameIntro.md', 'timef': '2024-12-03 10:00',
     'creator': 'ycy'},
    {'name': 'GreedySnakeGame', 'hot': 55, 'path': 'yule/source/GreedySnakeGame.html',
     'intro': 'static/md/yule/GreedySnakeGameIntro.md', 'timef': '2024-12-04 10:00',
     'creator': 'ycy'},
] + [{'name': n, 'hot': 20, 'path': 'yule/source/%s.html' % n,
      'intro': 'static/md/yule/TetrisGameIntro.md', 'timef': '2024-12-05 10:00', 'creator': 'ycy'}
     for n in ('TwoPlayersTetrisGame', 'FruitNinjaGame', 'MarioGame', 'PinballGame',
               'PlaneWarsGame', 'T-RexDinoGame', 'TwentyFortyEightGame')]

TABLES = {'users': USERS, 'lists': LISTS, 'articles': ARTICLES, 'comment': COMMENTS, 'yule': YULE}


def read_data(listname, con='', val=None):
    rows = TABLES.get(listname, [])
    if con == '':
        return [dict(r) for r in rows]
    out = []
    for r in rows:
        v = r.get(con)
        if v == val or str(v) == str(val) or (isinstance(v, int) and str(bool(v)) == str(val)):
            out.append(dict(r))
    return out


dbConnecter.read_data = read_data
dbConnecter.update_data = lambda *a, **k: None
dbConnecter.insert_data = lambda *a, **k: None
dbConnecter.delete_data = lambda *a, **k: None

import main_app  # noqa: E402

app = main_app.app
app.secret_key = 'smoke-test'

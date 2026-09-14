from flask import render_template, request, session, redirect, Blueprint, abort, jsonify
import uuid
import time
from urllib.parse import urlencode
from lib import dbConnecter, defender, srs, srs_store
from lib.config_loader import get_config

from user_app import user_app

recite_app = Blueprint('recite_app', __name__)
# recite_app.secret_key = os.urandom(24)
recite_app.secret_key = get_config('SECRET_KEY')
# client = pymongo.MongoClient()
# db = client.reciter

'''
    集合名 lists
    
    id 表格id
    username 用户名
    listname 表格名
    difficulty 难度
    en 英文信息
    zh 中文信息
    timef 创建时间
    o 是否为官方
    sm 是否有例句
    sen 例句
    priv 是否为私有(仅创建者可见)
    folder_id 所属文件夹, 空字符串表示不在任何文件夹里
             官方词表进 scope='official' 的公共文件夹, 私有词表进创建者自己 scope='private' 的文件夹
    
    CREATE TABLE lists (
        id VARCHAR(128), 
        username VARCHAR(64), 
        listname VARCHAR(64), 
        difficulty INT, 
        en TEXT,
        zh TEXT,
        timef VARCHAR(64), 
        o BOOL, 
        sm BOOl, 
        sen TEXT,
        priv BOOL NOT NULL DEFAULT 0,
        folder_id VARCHAR(128) NOT NULL DEFAULT ''
    );

    -- 已有数据库升级时执行一次
    ALTER TABLE lists ADD COLUMN priv BOOL NOT NULL DEFAULT 0;
    ALTER TABLE lists ADD COLUMN folder_id VARCHAR(128) NOT NULL DEFAULT '';

    -- 词表的文件夹
    -- scope='official': 官方栏目的公共文件夹, 只有管理员能建, 所有人都看得到
    -- scope='private': username 自己私有栏目的文件夹, 只有他自己看得到
    CREATE TABLE folders (
        id VARCHAR(128) NOT NULL,
        foldername VARCHAR(64) NOT NULL,
        username VARCHAR(64) NOT NULL,
        timef VARCHAR(64) NOT NULL,
        scope VARCHAR(16) NOT NULL DEFAULT 'official',
        PRIMARY KEY (id)
    );

    ALTER TABLE folders ADD COLUMN scope VARCHAR(16) NOT NULL DEFAULT 'official';

    -- Spaced repetition progress (per user, list, English word)
    CREATE TABLE word_progress (
        username VARCHAR(64) NOT NULL,
        list_id VARCHAR(128) NOT NULL,
        word VARCHAR(255) NOT NULL,
        level TINYINT NOT NULL DEFAULT 0,
        next_review DATE NOT NULL,
        seen INT NOT NULL DEFAULT 0,
        correct INT NOT NULL DEFAULT 0,
        wrong INT NOT NULL DEFAULT 0,
        PRIMARY KEY (username, list_id, word),
        INDEX idx_due (username, list_id, next_review)
    );

    -- Daily review queue for a user + list
    CREATE TABLE daily_task (
        username VARCHAR(64) NOT NULL,
        list_id VARCHAR(128) NOT NULL,
        day DATE NOT NULL,
        target_json TEXT NOT NULL,
        done_json TEXT NOT NULL,
        retry_json TEXT NOT NULL,
        PRIMARY KEY (username, list_id, day)
    );
'''

try: # 老数据库缺少 priv 列时补上, 否则修改表格会丢数据
    srs_store.ensure_lists_priv_column()
except Exception as err:
    print('lists.priv migration skipped: %s' % err)

try: # 文件夹是后加的, 老数据库没有 folders 表和 lists.folder_id
    srs_store.ensure_folder_schema()
except Exception as err:
    print('folder migration skipped: %s' % err)


def toList(str):
    l = []
    t = ''
    for i in str:
        if i == '|':
            l.append(t)
            t = ''
        else:
            t += i
    return l

def toStr(l):
    str = ''
    for i in l:
        str += i
        str += '|'
    return str

def is_private(wordlist):
    return bool(wordlist.get('priv'))

def can_read_list(wordlist, username): # 私有表格只有创建者能看
    return not is_private(wordlist) or wordlist['username'] == username

def can_edit_list(wordlist, username, admin): # 管理员不介入别人的私有表格
    if wordlist['username'] == username:
        return True
    return bool(admin) and not is_private(wordlist)

def load_list(list_id):
    rows = dbConnecter.read_data('lists', 'id', list_id)
    if not rows:
        return None
    return rows[0]

def current_admin(): # 返回 (用户名, 是否为管理员)
    username = session.get('username')
    if username == None:
        return None, False
    rows = dbConnecter.read_data('users', 'username', username)
    return username, bool(rows and rows[0]['admin'])

def folder_of(wordlist):
    return wordlist.get('folder_id') or ''

def scope_of(folder): # 私有栏目的文件夹是后加的, 老数据都属于官方栏目
    return folder.get('scope') or 'official'

def list_scope(wordlist): # 词表归哪个栏目的文件夹管, 用户栏目的表格不分文件夹
    if is_private(wordlist):
        return 'private'
    if wordlist['o']:
        return 'official'
    return None

def folder_scope(show_mode): # 用户栏目不分文件夹
    return show_mode if show_mode in ('official', 'private') else None

def can_be_filed(wordlist, scope, username): # 词表能不能放进这一栏的文件夹
    if scope == None or list_scope(wordlist) != scope:
        return False
    return scope != 'private' or wordlist['username'] == username # 私有文件夹只装自己的表格

def can_manage_folders(scope, username, admin): # 公共文件夹归管理员, 私有文件夹各管各的
    if username == None:
        return False
    if scope == 'official':
        return bool(admin)
    return scope == 'private'

def load_folders(scope, username=None):
    rows = [i for i in dbConnecter.read_data('folders') or [] if scope_of(i) == scope]
    if scope == 'private': # 别人的私有文件夹不该露面
        rows = [i for i in rows if i['username'] == username]
    rows.sort(key=lambda x: x['foldername'])
    return rows

def keep_folder(folder_id, scope): # 换了栏目的词表不留在原来的文件夹里
    if folder_id == '':
        return ''
    rows = dbConnecter.read_data('folders', 'id', folder_id)
    if not rows or scope_of(rows[0]) != scope:
        return ''
    return folder_id

def load_list_words(list_id):
    """Load a lists row and return (row, words) or (None, None)."""
    rows = dbConnecter.read_data('lists', 'id', list_id)
    if not rows:
        return None, None
    res = rows[0]
    en = toList(res['en'])
    zh = toList(res['zh'])
    sen = toList(res['sen']) if res['sm'] else []
    words = srs.parse_list_words(en, zh, sen, res['sm'])
    return res, words

@recite_app.route('/reciter', methods=["GET"]) # 依据条件展示表格列表
def reciter():
    username, admin = current_admin()
    difficulty = request.args.get('difficulty')
    key = request.args.get('key')
    show_mode = request.args.get('show_mode')
    if show_mode == None or (show_mode == 'private' and username == None):
        show_mode = 'official'
    scope = folder_scope(show_mode) # 文件夹只属于当前栏目
    rows = dbConnecter.read_data('lists') or []
    folders = load_folders(scope, username)
    folder_names = {i['id']: i['foldername'] for i in folders}
    folder = request.args.get('folder') or ''
    if folder not in folder_names: # 文件夹被删掉后回到最外层
        folder = ''
    counts = {}
    for i in rows: # 文件夹里的表格数不跟着筛选变
        if can_be_filed(i, scope, username) and folder_of(i) in folder_names:
            counts[folder_of(i)] = counts.get(folder_of(i), 0) + 1
    for i in folders:
        i['size'] = counts.get(i['id'], 0)
    searching = key != None and key != ''
    if searching: # 按名字找的时候跨文件夹一起列出来, 不停在某个文件夹里
        rows = [i for i in rows if i['listname'] == key]
        folder = ''
    if difficulty != None and difficulty != '' and difficulty != 'all':
        rows = [i for i in rows if str(i['difficulty']) == str(difficulty)]
    lists_o, lists_u, lists_p = [], [], []
    for i in rows:
        if is_private(i): # 私有表格只进创建者自己的栏目
            if username == None or i['username'] != username:
                continue
            bucket = lists_p
        elif i['o']:
            bucket = lists_o
        else:
            bucket = lists_u
        if can_be_filed(i, scope, username): # 归了档的表格只在自己的文件夹里露面
            if not searching and folder_of(i) != folder:
                continue
            if folder_of(i) != folder:
                i['folder_name'] = folder_names.get(folder_of(i), '')
        bucket.append(i)
    lists_o.sort(key=lambda x: x['listname'])
    lists_u.sort(key=lambda x: x['timef'], reverse=True)
    lists_p.sort(key=lambda x: x['timef'], reverse=True)
    return render_template('recite/lists.html', 
                           t_username=username, 
                           t_admin=admin,
                           t_lists_o=lists_o, 
                           t_lists_u=lists_u,
                           t_lists_p=lists_p,
                           t_show_mode=show_mode,
                           t_scope=scope,
                           t_folders=folders,
                           t_folder=folder,
                           t_folder_name=folder_names.get(folder, ''),
                           t_show_folders=scope != None and not searching and folder == '',
                           t_can_file=can_manage_folders(scope, username, admin),
                           t_done=request.args.get('done'),
                           t_moved=request.args.get('moved'),
                           t_msg=request.args.get('msg'))

def reciter_url(show_mode, key, difficulty, folder=None, **extra): # 操作后回到原来的栏目和筛选
    query = {'show_mode': show_mode or 'official',
             'key': key or '',
             'difficulty': difficulty or 'all'}
    if folder:
        query['folder'] = folder
    for name, value in extra.items():
        if value != None:
            query[name] = value
    return '/reciter?' + urlencode(query)

@recite_app.route('/bulk_visibility', methods=['POST']) # 批量切换公开/私有
def bulk_visibility():
    if session.get('username') == None:
        return redirect('/login')
    show_mode = request.form.get('show_mode')
    key = request.form.get('key')
    difficulty = request.form.get('difficulty')
    priv = request.form.get('priv') == 'y'
    done = 0
    for id in request.form.getlist('ids'):
        dic = load_list(id)
        if dic is None or dic['username'] != session['username']: # 只能改自己的表格
            continue
        if is_private(dic) == priv:
            continue
        dbConnecter.update_data('lists', 'id', id, 'priv', priv)
        dbConnecter.update_data('lists', 'id', id, 'folder_id', '') # 换了栏目就离开原来的文件夹
        if priv: # 私有表格不进官方列表
            dbConnecter.update_data('lists', 'id', id, 'o', False)
        done += 1
    if priv: # 跟着表格去它们现在所在的栏目
        show_mode = 'private'
    elif show_mode == 'private':
        show_mode = 'users'
    return redirect(reciter_url(show_mode, key, difficulty, done=done or None))

@recite_app.route('/create_folder', methods=['POST']) # 在当前栏目里建文件夹
def create_folder():
    username, admin = current_admin()
    if username == None:
        return redirect('/login')
    scope = request.form.get('scope')
    if not can_manage_folders(scope, username, admin):
        return 'No permission'
    key = request.form.get('key')
    difficulty = request.form.get('difficulty')
    foldername = (request.form.get('foldername') or '').strip()
    if foldername == '':
        return redirect(reciter_url(scope, key, difficulty, msg='folder_name_required'))
    for i in load_folders(scope, username): # 同一栏目里同名文件夹分不清谁是谁
        if i['foldername'] == foldername:
            return redirect(reciter_url(scope, key, difficulty, msg='folder_exists'))
    now_temp = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    dbConnecter.insert_data('folders',
                            '(id, foldername, username, timef, scope)',
                            (str(uuid.uuid1()), foldername[:64], username, now_temp, scope))
    return redirect(reciter_url(scope, key, difficulty, msg='folder_created'))

@recite_app.route('/del_folder', methods=['POST']) # 删掉空文件夹
def del_folder():
    username, admin = current_admin()
    if username == None:
        return redirect('/login')
    scope = request.form.get('scope')
    if not can_manage_folders(scope, username, admin):
        return 'No permission'
    key = request.form.get('key')
    difficulty = request.form.get('difficulty')
    folder = request.form.get('folder')
    if folder not in {i['id'] for i in load_folders(scope, username)}: # 管不着的文件夹当作不存在
        abort(404)
    for i in dbConnecter.read_data('lists') or []: # 先把里面的词表移出去, 免得它们跟着消失
        if folder_of(i) == folder:
            return redirect(reciter_url(scope, key, difficulty, folder, msg='folder_not_empty'))
    dbConnecter.delete_data('folders', 'id', folder)
    return redirect(reciter_url(scope, key, difficulty, msg='folder_deleted'))

@recite_app.route('/bulk_folder', methods=['POST']) # 批量把词表移入/移出文件夹
def bulk_folder():
    username, admin = current_admin()
    if username == None:
        return redirect('/login')
    scope = request.form.get('scope')
    if not can_manage_folders(scope, username, admin):
        return 'No permission'
    key = request.form.get('key')
    difficulty = request.form.get('difficulty')
    folder = request.form.get('folder') # 现在待的文件夹, 操作完回到这里
    if request.form.get('mode') == 'out':
        target = ''
    else:
        target = request.form.get('target_folder') or ''
    if target != '' and target not in {i['id'] for i in load_folders(scope, username)}:
        abort(404)
    moved = 0
    for id in request.form.getlist('ids'):
        dic = load_list(id)
        if dic is None or not can_be_filed(dic, scope, username): # 只整理本栏目里自己管得着的词表
            continue
        if folder_of(dic) == target:
            continue
        dbConnecter.update_data('lists', 'id', id, 'folder_id', target)
        moved += 1
    return redirect(reciter_url(scope, key, difficulty, folder, moved=moved or None))

@recite_app.route('/create') # 提供创建词汇表的页面
def create():
    if session.get('username') == None:
        return redirect('/login')
    # userdic = db.users.find_one({'username': session['username']})
    userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    return render_template('recite/create.html',
                           t_username=session.get('username'),
                           t_admin=userdic['admin'],
                           t_captcha_image=captcha_image)

@recite_app.route('/check_create', methods=['POST']) # 处理提供的创建信息
def check_create():
    if session.get('username') == None:
        return redirect('/login')
    user_captcha = request.form.get('user_captcha').lower()
    if user_captcha != session['captcha']:
        captcha_text, captcha_image = defender.generate_captcha()
        session['captcha'] = captcha_text.lower()
        # userdic = db.users.find_one({'username': session['username']})
        userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
        return render_template('recite/create.html',
                           t_username=session.get('username'),
                           t_admin=userdic['admin'],
                           t_captcha_image=captcha_image,
                            t_error='Wrong graph validate code')
    wordlist = request.form['wordlist']
    listname = request.form['listname']
    difficulty = request.form.get('difficulty')
    sm = request.form.get('sm')
    o = request.form.get('o')
    priv = request.form.get('priv') == 'y'
    en = []
    zh = []
    sen = []
    ens, zhs, sens = '', '', ''
    if sm == 'y':
        sm = True
        s = ''
        flag = 1
        for i in wordlist:
            if i == '\n':
                continue
            if i == '\r':
                if flag == 1:
                    en.append(s)
                elif flag == 2:
                    zh.append(s)
                elif flag == 3:
                    sen.append(s)
                s = ''
                flag %= 3
                flag += 1
            else:
                s += i
        sen.append(s)
        sens = toStr(sen)
    else:
        sm = False
        s = ''
        flag = 1
        for i in wordlist:
            if i == '\n':
                continue
            if i == '\r':
                if flag == 1:
                    en.append(s)
                elif flag == 0:
                    zh.append(s)
                s = ''
                flag ^= 1
            else:
                s += i
        zh.append(s)
    ens = toStr(en)
    zhs = toStr(zh)
    print(ens)
    print(zhs)
    if o == 'y' and not priv: # 私有表格不进官方列表
        o = True
    else:
        o = False
    id = str(uuid.uuid1())
    now = time.localtime()
    now_temp = time.strftime("%Y-%m-%d %H:%M", now)
    # db.lists.insert_one({'id': id,
    #                     'username': session.get('username'),
    #                     'listname': listname,
    #                     'difficulty': difficulty,
    #                     'en': en,
    #                     'zh': zh,
    #                     'timef': now_temp,
    #                     'o': o,
    #                     'sen': sen,
    #                     'sm': sm})
    dbConnecter.insert_data('lists',
                            '(id, username, listname, difficulty, en, zh, timef, o, sen, sm, priv)',
                            (id, session.get('username'), listname, difficulty, ens, zhs, now_temp, o, sens, sm, priv))
    # print('111111111111--------------------')
    if priv:
        return redirect('/reciter?show_mode=private')
    return redirect('/reciter')

# @recite_app.route('/prepare_recite', methods=['POST']) # 准备开始背诵
# def prepare_recite():
    # if session.get('username') == None:
    #     return redirect('/login')
    # id = request.form['id']
    # res = db.lists.find_one({'id': id})
    # dic = {}
    # dic['username'] = session.get('username')
    # dic['pat'] = request.form['pattern']
    # dic['en'] = res['en']
    # dic['zh'] = res['zh']
    # dic['num'] = len(res['en'])
    # dic['show'] = random.randint(0, dic['num'] - 1)
    # if res['sm']:
    #     dic['sm'] = True
    # else:
    #     dic['sm'] = False
    # dic['sen'] = res['sen']
    # dic['tong'] = {}
    # dic['list_id'] = id
    # dic['list_username'] = res['username']
    # dic['listname'] = res['listname']
    # dic['difficulty'] = res['difficulty']
    # for i in dic['en']:
    #     dic['tong'][i] = 2
    # dic['fir'] = {}
    # for i in dic['en']:
    #     dic['fir'][i] = True
    # db.temp.delete_one({'username': session.get('username')})
    # db.temp.insert_one(dic)
    # return redirect('/recite')

@recite_app.route('/recite', methods=['GET']) # 背诵
def recite():
    if session.get('username') == None:
        return redirect('/login')
    list_id = request.args.get('id')
    pattern = request.args.get('pattern')
    res, words = load_list_words(list_id)
    if res is None or not can_read_list(res, session['username']):
        abort(404)
    bootstrap = srs.session_bootstrap(session['username'], list_id, words)
    ctx = {
        't_username': session.get('username'),
        't_pat': pattern,
        't_sm': res['sm'],
        't_listname': res['listname'],
        't_list_id': list_id,
        't_card': bootstrap['card'],
        't_stats': bootstrap['stats'],
    }
    if pattern == 'Learn meaning':
        return render_template('recite/recite_meaning.html', **ctx)
    return render_template('recite/recite_spelling.html', **ctx)


@recite_app.route('/recite/rate', methods=['POST']) # 评分并取下一张
def recite_rate():
    if session.get('username') == None:
        return jsonify({'error': 'login required'}), 401
    data = request.get_json(silent=True) or {}
    list_id = data.get('list_id') or request.form.get('list_id')
    word = data.get('word') or request.form.get('word')
    rating = data.get('rating') or request.form.get('rating')
    if rating not in ('know', 'dont'):
        return jsonify({'error': 'invalid rating'}), 400
    res, words = load_list_words(list_id)
    if res is None or not can_read_list(res, session['username']):
        return jsonify({'error': 'list not found'}), 404
    word_set = {item['word'] for item in words}
    if word not in word_set:
        return jsonify({'error': 'word not in list'}), 400
    progress, daily = srs.rate_word(session['username'], list_id, words, word, rating)
    choice = srs.choose_word(words, progress, daily, current_word=word)
    stats = srs.list_statistics(words, progress, daily)
    return jsonify({
        'card': srs.card_payload(choice),
        'stats': stats,
        'finished': stats['finished'],
    })


@recite_app.route('/recite/restart_today', methods=['POST']) # 今天重学整张
def recite_restart_today():
    if session.get('username') == None:
        return redirect('/login')
    list_id = request.form.get('id')
    res, words = load_list_words(list_id)
    if res is None or not can_read_list(res, session['username']):
        abort(404)
    srs.restart_today(session['username'], list_id, words)
    return redirect('/show_list?id=' + list_id)


@recite_app.route('/recite/review_wrong', methods=['POST']) # 只复习错词
def recite_review_wrong():
    if session.get('username') == None:
        return redirect('/login')
    list_id = request.form.get('id')
    res, words = load_list_words(list_id)
    if res is None or not can_read_list(res, session['username']):
        abort(404)
    _progress, daily = srs.review_wrong(session['username'], list_id, words)
    if daily is None:
        return redirect('/show_list?id=' + list_id + '&msg=no_wrong')
    return redirect('/show_list?id=' + list_id)
# @recite_app.route('/check_recite', methods=['GET']) # 检查背诵信息
# def check_recite():
#     if session.get('username') == None:
#         return redirect('/login')
#     dic = db.temp.find_one({'username': session.get('username')})
#     flag = False
#     if dic['pat'] == 'Learn meaning':
#         res = request.args['know']
#         if res == 'Know':
#             if dic['fir'][dic['en'][dic['show']]]:
#                 dic['tong'][dic['en'][dic['show']]] = 0
#             else:
#                 dic['tong'][dic['en'][dic['show']]] -= 1
#         else:
#             dic['tong'][dic['en'][dic['show']]] = 2
#     else:
#         res = request.args['ans']
#         if res == dic['en'][dic['show']]:
#             if dic['fir'][dic['en'][dic['show']]]:
#                 dic['tong'][dic['en'][dic['show']]] = 0
#             else:
#                 dic['tong'][dic['en'][dic['show']]] -= 1
#         else:
#             dic['tong'][dic['en'][dic['show']]] = 2
#             flag = True
#     dic['fir'][dic['en'][dic['show']]] = False
#     ent = dic['en'][dic['show']]
#     zht = dic['zh'][dic['show']]
#     if dic['sm']:
#         sen = dic['sen'][dic['show']]
#     else:
#         sen = ''
#     if dic['tong'][dic['en'][dic['show']]] <= 0:
#         dic['num'] -= 1
#         del dic['en'][dic['show']]
#         del dic['zh'][dic['show']]
#         if dic['sm']:
#             del dic['sen'][dic['show']]
#     if dic['num'] == 0:
#         now = time.localtime()
#         now_temp = time.strftime("%Y-%m-%d %H:%M", now)
#         userdic = db.users.find_one({'username': session['username']})
#         flag = True
#         for i in userdic['list_record']:
#             if i['id'] == dic['list_id']:
#                 i['timef'] = now_temp
#                 flag = False
#                 break
#         if flag:
#             userdic['list_record'].append({'username': dic['list_username'],
#                                         'id': dic['list_id'],
#                                         'listname': dic['listname'],
#                                         'difficulty': dic['difficulty'],
#                                         'timef': now_temp})
#         db.users.update({'username': session['username']}, userdic)
#         return render_template('recite/finish.html',
#                                t_username=session['username'],
#                                #                                t_listname=dic['listname'])
#     dic['show'] = random.randint(0, dic['num'] - 1)
#     db.temp.update({'username': session['username']}, dic)
#     if flag:
#         fir = ""
#         if dic['fir'][dic['en'][dic['show']]]:
#             fir = "first time"
#         if dic['pat'] == 'Learn spelling':
#             return render_template('recite/tip.html',
#                                    t_username=session['username'],
#                                    t_en=ent,
#                                    t_zh=zht,
#                                    t_pat=dic['pat'],
#                                    t_res=res,
#                                    t_num=dic['num'],
#                                    t_rem=dic['tong'][dic['en'][dic['show']]],
#                                    t_fir=fir,
#                                    t_sm=dic['sm'],
#                                    t_sen=sen,
#                                    #                                    t_listname=dic['listname'])
#         else:
#             return render_template('recite/tip_meaning.html',
#                                    t_username=session['username'],
#                                    t_en=ent,
#                                    t_zh=zht,
#                                    t_pat=dic['pat'],
#                                    t_res=res,
#                                    t_num=dic['num'],
#                                    t_rem=dic['tong'][dic['en'][dic['show']]],
#                                    t_fir=fir,
#                                    t_sm=dic['sm'],
#                                    t_sen=sen,
#                                    #                                    t_listname=dic['listname'])
#     return redirect('/recite')

# @recite_app.route('/show_tip')
# def show_tip():
#     if session.get('username') == None:
#         return redirect('/login')
#     dic = db.temp.find_one({'username': session['username']})
#     ent = dic['en'][dic['show']]
#     zht = dic['zh'][dic['show']]
#     if dic['sm']:
#         sen = dic['sen'][dic['show']]
#     else:
#         sen = ''
#     fir = ""
#     if dic['fir'][dic['en'][dic['show']]]:
#         fir = "first time"
#     if dic['pat'] == 'Learn spelling':
#         return render_template('recite/tip.html',
#                                t_username=session['username'],
#                                t_en=ent,
#                                t_zh=zht,
#                                t_pat=dic['pat'],
#                                t_num=dic['num'],
#                                t_rem=dic['tong'][dic['en'][dic['show']]],
#                                t_fir=fir,
#                                t_sm=dic['sm'],
#                                t_sen=sen,
#                                #                                t_listname=dic['listname'])
#     else:
#         return render_template('recite/tip_meaning.html',
#                                t_username=session['username'],
#                                t_en=ent,
#                                t_zh=zht,
#                                t_pat=dic['pat'],
#                                t_num=dic['num'],
#                                t_rem=dic['tong'][dic['en'][dic['show']]],
#                                t_fir=fir,
#                                t_sm=dic['sm'],
#                                t_sen=sen,
#                                #                                t_listname=dic['listname'])

# @recite_app.route('/mod_list', methods=['POST'])
# def mod_list():
#     o = request.form.get('o')
#     if o == 'y':
#         o = True
#     else:
#         o = False
#     id = request.form.get('id')
#     wordlist = db.lists.find_one({'id': id})
#     wordlist['o'] = o
#     db.lists.update({'id': id}, wordlist)
#     return redirect('/lists')

@recite_app.route('/show_list', methods=['GET']) # 展示表格
def show_list():
    id = request.args.get('id')
    wordlist = load_list(id)
    if wordlist is None or not can_read_list(wordlist, session.get('username')):
        abort(404)
    wordlist['en'] = toList(wordlist['en'])
    wordlist['zh'] = toList(wordlist['zh'])
    if wordlist['sm']:
        wordlist['sen'] = toList(wordlist['sen'])
    if session.get('username') == None:
        admin = False
        stats = None
    else:
        admin = dbConnecter.read_data('users', 'username', session['username'])[0]['admin']
        words = srs.parse_list_words(
            wordlist['en'], wordlist['zh'],
            wordlist['sen'] if wordlist['sm'] else [],
            wordlist['sm'],
        )
        progress, daily = srs.ensure_today_task(session['username'], id, words)
        stats = srs.list_statistics(words, progress, daily)
    return render_template('recite/show_list.html',
                           t_username=session.get('username'),
                           t_wordlist=wordlist,
                           t_size=len(wordlist['en']),
                           t_sm=wordlist['sm'],
                           t_admin=admin,
                           t_stats=stats,
                           t_msg=request.args.get('msg'))

@recite_app.route('/check_del_list', methods=['GET'])
def check_del_list():
    if session.get('username') == None:
        return redirect('/login')
    id = request.args.get('id')
    dic = load_list(id)
    if dic is None or not can_read_list(dic, session['username']):
        abort(404)
    return render_template('recite/check_del_list.html',
                           t_id=id,
                           t_username=session.get('username'),
                           # t_listname=db.lists.find_one({'id': id})['listname']
                           t_listname=dic['listname']
                           )

@recite_app.route('/del_list', methods=['GET']) # 删除表格
def del_list():
    if session.get('username') == None:
        return redirect('/login')
    id = request.args.get('id')
    # userdic = db.users.find_one({'username': session['username']})
    userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
    # dic = db.lists.find_one({'id': id})
    dic = load_list(id)
    if dic is None:
        abort(404)
    if can_edit_list(dic, session['username'], userdic['admin']):
        dbConnecter.delete_data('lists', 'id', id)
        srs_store.delete_list_progress(id)
        return redirect('/reciter')
    else:
        return 'No permission'

@recite_app.route('/modify_list', methods=['GET']) # provide modification page
def modify_list():
    if session.get('username') == None:
        return redirect('/login')
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    id = request.args.get('id')
    dic = load_list(id)
    if dic is None:
        abort(404)
    dic['en'] = toList(dic['en'])
    dic['zh'] = toList(dic['zh'])
    if (dic['sm']):
        dic['sen'] = toList(dic['sen'])
    # dic = db.lists.find_one({'id': id})
    # userdic = db.users.find_one({'username': session['username']})
    userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
    if can_edit_list(dic, session['username'], userdic['admin']):
        info = ''
        for i in range(0, len(dic['en'])):
            info += dic['en'][i] + '\n'
            info += dic['zh'][i] + '\n'
            if dic['sm']:
                info += dic['sen'][i] + '\n'
        errorr = request.args.get('error')
        if errorr == None:
            errorr = ''
        return render_template('recite/modify_list.html',
                               t_id=id,
                               t_info=info,
                               t_admin=userdic['admin'],
                               t_listname=dic['listname'],
                               t_priv=is_private(dic),
                               t_owner=dic['username'] == session['username'],
                               t_username=session['username'],
                               t_captcha_image=captcha_image,
                               t_error=errorr)
    else:
        return 'No permission'

@recite_app.route('/modifier', methods=['POST']) # check the modification infomation
def modifier():
    if session.get('username') == None:
        return redirect('/login')
    id = request.form.get('id')
    user_captcha = request.form.get('user_captcha').lower()
    if user_captcha != session['captcha']:
        return redirect('/modify_list?id=' + id + '&error=Wrong graph validate code')
    wordlist = request.form.get('wordlist')
    listname = request.form.get('listname')
    difficulty = request.form.get('difficulty')
    sm = request.form.get('sm')
    o = request.form.get('o')
    en = []
    zh = []
    sen = []
    if sm == 'y':
        sm = True
        s = ''
        flag = 1
        for i in wordlist:
            if i == '\n':
                continue
            if i == '\r':
                if flag == 1:
                    en.append(s)
                elif flag == 2:
                    zh.append(s)
                elif flag == 3:
                    sen.append(s)
                s = ''
                flag %= 3
                flag += 1
            else:
                s += i
        sen.append(s)
    else:
        sm = False
        s = ''
        flag = 1
        for i in wordlist:
            if i == '\n':
                continue
            if i == '\r':
                if flag == 1:
                    en.append(s)
                elif flag == 0:
                    zh.append(s)
                s = ''
                flag ^= 1
            else:
                s += i
        zh.append(s)
    # dic = db.lists.find_one({'id': id})
    dic = load_list(id)
    if dic is None:
        abort(404)
    userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
    if not can_edit_list(dic, session['username'], userdic['admin']):
        return 'No permission'
    priv = request.form.get('priv')
    if dic['username'] == session['username'] and priv in ('y', 'n'): # 公开性只由创建者决定
        priv = priv == 'y'
    else:
        priv = is_private(dic)
    if o == 'y':
        o = True
    elif o == 'n':
        o = False
    else:
        o = dic['o']
    if priv: # 私有表格不进官方列表
        o = False
    dic['o'] = o
    dic['priv'] = priv
    dic['folder_id'] = keep_folder(folder_of(dic), list_scope(dic))
    dic['listname'] = listname
    dic['difficulty'] = difficulty
    dic['en'] = toStr(en)
    dic['zh'] = toStr(zh)
    if sm:
        dic['sen'] = toStr(sen)
    else:
        dic['sen'] = ''
    dic['sm'] = sm
    # db.lists.update({'id': id}, dic)
    dbConnecter.delete_data('lists', 'id', id)
    dbConnecter.insert_data('lists',
                            '(id, username, listname, difficulty, en, zh, timef, o, sen, sm, priv, folder_id)',
                            (id, dic['username'], dic['listname'], dic['difficulty'], dic['en'], dic['zh'], dic['timef'], dic['o'], dic['sen'], dic['sm'], dic['priv'], dic['folder_id'])
                            )
    if priv:
        return redirect('/reciter?show_mode=private')
    return redirect('/reciter')

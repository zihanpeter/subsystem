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
        priv BOOL NOT NULL DEFAULT 0
    );

    -- 已有数据库升级时执行一次
    ALTER TABLE lists ADD COLUMN priv BOOL NOT NULL DEFAULT 0;

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
    username = session.get('username')
    difficulty = request.args.get('difficulty')
    key = request.args.get('key')
    rows = dbConnecter.read_data('lists') or []
    if key != None and key != '':
        rows = [i for i in rows if i['listname'] == key]
    if difficulty != None and difficulty != '' and difficulty != 'all':
        rows = [i for i in rows if str(i['difficulty']) == str(difficulty)]
    lists_o, lists_u, lists_p = [], [], []
    for i in rows:
        if is_private(i): # 私有表格只进创建者自己的栏目
            if username != None and i['username'] == username:
                lists_p.append(i)
        elif i['o']:
            lists_o.append(i)
        else:
            lists_u.append(i)
    lists_o.sort(key=lambda x: x['listname'])
    lists_u.sort(key=lambda x: x['timef'], reverse=True)
    lists_p.sort(key=lambda x: x['timef'], reverse=True)
    show_mode = request.args.get('show_mode')
    if show_mode == None or (show_mode == 'private' and username == None):
        show_mode = 'official'
    return render_template('recite/lists.html', 
                           t_username=username, 
                           t_lists_o=lists_o, 
                           t_lists_u=lists_u,
                           t_lists_p=lists_p,
                           t_show_mode=show_mode,
                           t_done=request.args.get('done'))

def reciter_url(show_mode, key, difficulty, done=None): # 批量操作后回到原来的栏目和筛选
    query = {'show_mode': show_mode or 'official',
             'key': key or '',
             'difficulty': difficulty or 'all'}
    if done != None:
        query['done'] = done
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
        if priv: # 私有表格不进官方列表
            dbConnecter.update_data('lists', 'id', id, 'o', False)
        done += 1
    if priv: # 跟着表格去它们现在所在的栏目
        show_mode = 'private'
    elif show_mode == 'private':
        show_mode = 'users'
    return redirect(reciter_url(show_mode, key, difficulty, done or None))

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
    dic['listname'] = listname
    dic['difficulty'] = difficulty
    dic['en'] = toStr(en)
    dic['zh'] = toStr(zh)
    dic['o'] = o
    dic['priv'] = priv
    if sm:
        dic['sen'] = toStr(sen)
    else:
        dic['sen'] = ''
    dic['sm'] = sm
    # db.lists.update({'id': id}, dic)
    dbConnecter.delete_data('lists', 'id', id)
    dbConnecter.insert_data('lists',
                            '(id, username, listname, difficulty, en, zh, timef, o, sen, sm, priv)',
                            (id, dic['username'], dic['listname'], dic['difficulty'], dic['en'], dic['zh'], dic['timef'], dic['o'], dic['sen'], dic['sm'], dic['priv'])
                            )
    if priv:
        return redirect('/reciter?show_mode=private')
    return redirect('/reciter')

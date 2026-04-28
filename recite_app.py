from flask import render_template, request, session, redirect, Blueprint, abort
import uuid
import time
from lib import dbConnecter, defender
import os

from user_app import user_app

recite_app = Blueprint('recite_app', __name__)
# recite_app.secret_key = os.urandom(24)
recite_app.secret_key = os.getenv('SECRET_KEY')
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
        sen TEXT
    );
'''

def get_theme():
    theme = session.get('theme')
    if theme == None:
        theme = 'white'
    return theme

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

@recite_app.route('/reciter', methods=["GET"]) # 依据条件展示表格列表
def reciter():
    username = session.get('username')
    difficulty = request.args.get('difficulty')
    key = request.args.get('key')
    list_o, list_u = [], []
    if key == None or key == '':
        if difficulty == 'all' or difficulty == None:
            print(11111)
            # lists_o = db.lists.find({'o': True})
            lists_o = dbConnecter.read_data('lists', 'o', 1)
            # lists_o = list(lists_o)
            # lists_u = db.lists.find({'o': False})
            lists_u = dbConnecter.read_data('lists', 'o', 0)
            ls =  dbConnecter.read_data('lists')
            # lists_u = list(lists_u)
        else:
            print(222222)
            # lists_o = db.lists.find({'difficulty': difficulty, 'o': True})
            list_oo = dbConnecter.read_data('lists', 'difficulty', difficulty)
            for i in list_oo:
                if i['o']:
                    list_o.append(i)
                else:
                    list_u.append(i)
            # lists_o = list(lists_o)
            # lists_u = db.lists.find({'difficulty': difficulty, 'o': False})
            # lists_u = list(lists_u)
    else:
        if difficulty == 'all':
            print(3333333)
            list_oo = dbConnecter.read_data('lists', 'listname', key)

            for i in list_oo:
                if i['o']:
                    list_o.append(i)
                else:
                    list_u.append(i)
            # lists_o = db.lists.find({'listname': key, 'o': True})
            # lists_o = list(lists_o)
            # lists_u = db.lists.find({'listname': key, 'o': False})
            # lists_u = list(lists_u)
        else:
            print(44444444)
            # lists_o = db.lists.find({'listname': key, 'difficulty': difficulty, 'o': True})
            # lists_o = list(lists_o)
            # lists_u = db.lists.find({'listname': key, 'difficulty': difficulty, 'o': False})
            # lists_u = list(lists_u)
            list_oo = dbConnecter.read_data('lists', 'listname', key)
            for i in list_oo:
                if i['difficulty'] == difficulty:
                    if i['o']:
                        list_o.append(i)
                    else:
                        list_u.append(i)
    lists_o.sort(key=lambda x: x['listname'])
    lists_u.sort(key=lambda x: x['timef'], reverse=True)
    show_mode = request.args.get('show_mode')
    if show_mode == None:
        show_mode = 'official'
    return render_template('recite/lists.html', 
                           t_username=username, 
                           t_lists_o=lists_o, 
                           t_lists_u=lists_u,
                           t_theme=get_theme(),
                           t_show_mode=show_mode)

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
                           t_theme=get_theme(),
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
                           t_theme=get_theme(),
                           t_captcha_image=captcha_image,
                            t_error='Wrong graph validate code')
    wordlist = request.form['wordlist']
    listname = request.form['listname']
    difficulty = request.form.get('difficulty')
    sm = request.form.get('sm')
    o = request.form.get('o')
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
    if o == 'y':
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
                            '(id, username, listname, difficulty, en, zh, timef, o, sen, sm)',
                            (id, session.get('username'), listname, difficulty, ens, zhs, now_temp, o, sens, sm))
    # print('111111111111--------------------')
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
    id = request.args.get('id')
    # res = db.lists.find_one({'id': id})
    res = dbConnecter.read_data('lists', 'id', id)[0]
    dic = {}
    dic['username'] = session.get('username')
    dic['pat'] = request.args.get('pattern')
    ens = res['en']
    zhs = res['zh']
    sens = res['sen']
    en, zh, sen = [], [], []
    en = toList(ens)
    zh = toList(zhs)
    # dic['num'] = len(res['en'])
    # dic['show'] = random.randint(0, dic['num'] - 1)
    if res['sm']:
        sen = toList(sens)
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
    # dic = db.temp.find_one({'username': session.get('username')})
    # fir = ""
    # if dic['fir'][dic['en'][dic['show']]]:
    #     fir = "first time"
    if dic['pat'] == 'Learn meaning':
        return render_template('recite/recite_meaning.html',
                               t_username=session.get('username'),
                               t_en=en,
                               t_zh=zh,
                               # t_num=dic['num'],
                               # t_rem=dic['tong'][dic['en'][dic['show']]],
                               # t_fir=fir,
                               t_pat=dic['pat'],
                               t_sm=res['sm'],
                               t_sen=sen,
                               t_theme=get_theme(),
                               t_listname=res['listname'])
    else:
        return render_template('recite/recite_spelling.html',
                               t_username=session.get('username'),
                               t_en=en,
                               t_zh=zh,
                               # t_num=dic['num'],
                               # t_rem=dic['tong'][dic['en'][dic['show']]],
                               # t_fir=fir,
                               t_pat=dic['pat'],
                               t_sm=res['sm'],
                               t_sen=sen,
                               t_theme=get_theme(),
                               t_listname=res['listname'])

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
#                                t_theme=get_theme(),
#                                t_listname=dic['listname'])
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
#                                    t_theme=get_theme(),
#                                    t_listname=dic['listname'])
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
#                                    t_theme=get_theme(),
#                                    t_listname=dic['listname'])
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
#                                t_theme=get_theme(),
#                                t_listname=dic['listname'])
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
#                                t_theme=get_theme(),
#                                t_listname=dic['listname'])

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
    # wordlist = db.lists.find_one({'id': id})
    wordlist = dbConnecter.read_data('lists', 'id', id)[0]
    wordlist['en'] = toList(wordlist['en'])
    wordlist['zh'] = toList(wordlist['zh'])
    if wordlist['sm']:
        wordlist['sen'] = toList(wordlist['sen'])
    if session.get('username') == None:
        admin = False
    else:
        # admin = db.users.find_one({'username': session['username']})['admin']
        admin = dbConnecter.read_data('users', 'username', session['username'])[0]['admin']
    return render_template('recite/show_list.html',
                           t_username=session.get('username'),
                           t_wordlist=wordlist,
                           t_size=len(wordlist['en']),
                           t_sm=wordlist['sm'],
                           t_admin=admin,
                           t_theme=get_theme())

@recite_app.route('/check_del_list', methods=['GET'])
def check_del_list():
    if session.get('username') == None:
        return redirect('/login')
    id = request.args.get('id')
    return render_template('recite/check_del_list.html',
                           t_id=id,
                           t_username=session.get('username'),
                           t_theme=get_theme(),
                           # t_listname=db.lists.find_one({'id': id})['listname']
                           t_listname=dbConnecter.read_data('lists', 'id', id)[0]['listname']
                           )

@recite_app.route('/del_list', methods=['GET']) # 删除表格
def del_list():
    if session.get('username') == None:
        return redirect('/login')
    id = request.args.get('id')
    # userdic = db.users.find_one({'username': session['username']})
    userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
    # dic = db.lists.find_one({'id': id})
    dic = dbConnecter.read_data('lists', 'id', id)[0]
    if dic['username'] == session['username'] or userdic['admin']:
        # db.lists.delete_one({'id': id})
        dbConnecter.delete_data('lists', 'id', id)
        # dics = list(db.users.find())
        # for i in dics:
        #     for j in range(0, len(i['list_record'])):
        #         if i['list_record'][j]['id'] == id:
        #             del i['list_record'][j]
        #             break
        #     db.users.update({'username': i['username']}, i)
        return redirect('/lists')
    else:
        return 'No permission'

@recite_app.route('/modify_list', methods=['GET']) # provide modification page
def modify_list():
    if session.get('username') == None:
        return redirect('/login')
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    id = request.args.get('id')
    dic = dbConnecter.read_data('lists', 'id', id)[0]
    dic['en'] = toList(dic['en'])
    dic['zh'] = toList(dic['zh'])
    if (dic['sm']):
        dic['sen'] = toList(dic['sen'])
    # dic = db.lists.find_one({'id': id})
    # userdic = db.users.find_one({'username': session['username']})
    userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
    if dic['username'] == session['username'] or userdic['admin']:
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
                               t_username=session['username'],
                               t_theme=get_theme(),
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
    dic = dbConnecter.read_data('lists', 'id', id)[0]
    if o == 'y':
        o = True
    elif o == 'n':
        o = False
    else:
        o = dic['o']
    dic['listname'] = listname
    dic['difficulty'] = difficulty
    dic['en'] = toStr(en)
    dic['zh'] = toStr(zh)
    dic['o'] = o
    if sm:
        dic['sen'] = toStr(sen)
    else:
        dic['sen'] = ''
    dic['sm'] = sm
    # db.lists.update({'id': id}, dic)
    dbConnecter.delete_data('lists', 'id', id)
    dbConnecter.insert_data('lists',
                            '(id, username, listname, difficulty, en, zh, timef, o, sen, sm)',
                            (id, dic['username'], dic['listname'], dic['difficulty'], dic['en'], dic['zh'], dic['timef'], dic['o'], dic['sen'], dic['sm'])
                            )
    return redirect('/lists')

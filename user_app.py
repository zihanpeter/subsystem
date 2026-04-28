from flask import render_template, request, session, redirect, Blueprint, abort
import time
import markdown
import bleach
import re
import os
from lib import dbConnecter, defender

user_app = Blueprint('user_app', __name__)
user_app.secret_key = os.getenv('SECRET_KEY')
# client = pymongo.MongoClient()
# db = client.reciter

''''
    集合名users

    username 用户名
    password 密码
    timef 注册时间
    intro 个人简介
    theme 颜色主题
    admin 是否为管理员
    
    CREATE TABLE users (
        username VARCHAR(64), 
        password VARCHAR(64), 
        timef VARCHAR(64), 
        intro TEXT, 
        theme VARCHAR(64), 
        admin BOOL
    );
'''

def get_theme():
    theme = session.get('theme')
    if theme == None:
        theme = 'white'
    return theme

@user_app.route('/login') # 提供登录页面
def login():
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    return render_template('user/login.html',
                           t_theme=get_theme(),
                           t_captcha_image=captcha_image)

@user_app.route('/check_login', methods=['POST']) # 检查登录信息
def check_login():
    user_captcha = request.form.get('user_captcha').lower()
    if user_captcha != session['captcha']:
        captcha_text, captcha_image = defender.generate_captcha()
        session['captcha'] = captcha_text.lower()
        return render_template('user/login.html',
                               t_error='Wrong graph validate code',
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image)
    username = request.form['username']
    password = request.form['password']
    # res = db.users.find_one({'username': username, 'password': password})
    res = dbConnecter.read_data('users', 'username', username)
    if res == [] or res[0]['password'] != password or res[0]['username'] != username:
        captcha_text, captcha_image = defender.generate_captcha()
        session['captcha'] = captcha_text.lower()
        return render_template('user/login.html',
                               t_error='Wrong username or password.',
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image)
    else:
        session['username'] = username
        session['theme'] = res[0]['theme']
        return redirect('/')

@user_app.route('/register') # 提供注册页面
def register():
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    return render_template('user/register.html',
                           t_theme=get_theme(),
                           t_captcha_image=captcha_image)

@user_app.route('/check_register', methods=['POST']) # 处理注册信息
def check_register():
    user_captcha = request.form.get('user_captcha').lower()
    if user_captcha != session['captcha']:
        captcha_text, captcha_image = defender.generate_captcha()
        session['captcha'] = captcha_text.lower()
        return render_template('user/register.html',
                               t_error='Wrong graph validate code',
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image)
    username = request.form['username']
    password = request.form['password']
    password2 = request.form.get('password2')
    # res = db.users.find_one({'username': username})
    res = dbConnecter.read_data('users', 'username', username)
    now = time.localtime()
    now_temp = time.strftime("%Y-%m-%d %H:%M", now)
    if res == []:
        flag = True
        for i in username:
            if ('A' <= i <= 'Z') or ('a' <= i <= 'z') or ('0' <= i <= '9') or ('\u4e00' <= i <= '\u9fff'):
                continue
            else:
                captcha_text, captcha_image = defender.generate_captcha()
                session['captcha'] = captcha_text.lower()
                return render_template('user/register.html',
                                       t_error='The username is not allowed.',
                                       t_theme=get_theme(),
                                       t_captcha_image=captcha_image)
        if password2 != password:
            captcha_text, captcha_image = defender.generate_captcha()
            session['captcha'] = captcha_text.lower()
            return render_template('user/register.html',
                                   t_error='Two passwords are different.',
                                   t_theme=get_theme(),
                                   t_captcha_image=captcha_image)
        dbConnecter.insert_data('users', '(username, password, timef, intro, theme, admin)', (username, password, now_temp, 'Nothing', 'white', False))
        # db.users.insert_one({'username': username,
        #                      'password': password,
        #                      'timef': now_temp,
        #                      'list_record': [],
        #                      'intro': 'Nothing',
        #                      'theme': 'white',
        #                      'admin': False})
        session['username'] = username
        session['theme'] = 'white'
        return redirect('/')
    else:
        captcha_text, captcha_image = defender.generate_captcha()
        session['captcha'] = captcha_text.lower()
        return render_template('user/register.html',
                               t_error='The username is already exist.',
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image)

@user_app.route('/profile') # 提供用户信息页面
def profile():
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    username = request.args.get('username')
    # userdic = db.users.find_one({'username': username})
    # userlist = db.lists.find({'username': username})
    # print(username)
    userdic = dbConnecter.read_data('users', 'username', username)[0]
    # print(userdic)
    # userlist = list(userlist)
    # articleslist = list(db.articles.find({'username': username}))
    intro = userdic['intro']
    intro = markdown.markdown(intro, extensions=['markdown.extensions.fenced_code',
                                                 'markdown.extensions.codehilite',
                                                 'markdown.extensions.extra',
                                                 'markdown.extensions.toc',
                                                 'markdown.extensions.tables'])
    if session.get('username') == None:
        admin = False
    else:
        # admin = db.users.find_one({'username': session['username']})['admin']
        admin = dbConnecter.read_data('users', 'username', session['username'])[0]['admin']
    return render_template('user/profile.html', 
                           t_realname=session.get('username'),
                           t_username=username, 
                           t_timef=userdic['timef'], 
                           # t_userlist=userlist,
                           # t_list_record=userdic['list_record'],
                           # t_articleslist=articleslist,
                           t_intro=intro,
                           t_admin=admin,
                           t_theme=get_theme(),
                           t_captcha_image=captcha_image)

@user_app.route('/change_password', methods=['POST']) # 处理更改密码信息
def change_password():
    user_captcha = request.form.get('user_captcha').lower()
    if user_captcha != session['captcha']:
        captcha_text, captcha_image = defender.generate_captcha()
        session['captcha'] = captcha_text.lower()
        return render_template('user/profile.html',
                               t_error='Wrong graph validate code',
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image)
    resOld = request.form['old']
    resNew = request.form['new']
    new2 = request.form.get('new2')
    # userdic = db.users.find_one({'username': session['username']})
    userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
    if resNew != new2:
        return render_template('user/profile.html',
                               t_error='Two passwords are different.',
                               t_theme=get_theme())
    if resOld == userdic['password']:
        # userdic['password'] = resNew
        # db.users.update({'username': session['username']}, userdic)
        dbConnecter.update_data('users', 'username', session['username'], 'password', resNew)
        return redirect('/')
    else:
        return render_template('user/profile.html',
                               t_error='Your original password is wrong',
                               t_theme=get_theme())

@user_app.route('/change_theme', methods=['POST']) # 更改颜色主题
def change_theme():
    theme = request.form.get('theme')
    # dic = db.users.find_one({'username': session['username']})
    # dic = dbConnecter.read_data('users', 'username', session['username'])
    # dic['theme'] = theme
    session['theme'] = theme
    # db.users.update({'username': session['username']}, dic)
    dic = dbConnecter.update_data('users', 'username', session['username'], 'theme', theme)
    return redirect('/profile?username=' + session['username'])

@user_app.route('/userlist')
def userlist():
    # dics = list(db.users.find())
    dics = dbConnecter.read_data('users')
    dics.sort(key = lambda x: x['timef'])
    return render_template('user/userlist.html',
                           t_username=session.get('username'),
                           t_dics=dics,
                           t_theme=get_theme())

@user_app.route('/modify_intro', methods=['GET']) # 提供修改用户简介页面
def modify_intro():
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    username = request.args.get('username')
    # dic = db.users.find_one({'username': username})
    dic = dbConnecter.read_data('users', 'username', username)[0]
    if username == session['username'] or dic[session['username']]:
        # info = ''
        # for i in dic['intro']:
        #     info += i
        return render_template('user/modify_intro.html',
                               t_info=dic['intro'],
                               t_username=username,
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image)
    else:
        return 'No permission'

# 定义一个函数，用于提取Markdown中的代码块
def extract_code_blocks(text):
    code_blocks = {}
    # 使用正则表达式匹配Markdown代码块
    pattern = re.compile(r"(```[\s\S]*?```)|(\n    .*?\n)", re.MULTILINE)
    counter = 0
    for match in pattern.finditer(text):
        code = match.group(0)
        placeholder = f"{{{{BLEACH_CODE_BLOCK_{counter}}}}}"
        code_blocks[placeholder] = code
        text = text.replace(code, placeholder)
        counter += 1
    return text, code_blocks

# 定义一个函数，用于恢复代码块
def restore_code_blocks(text, code_blocks):
    for placeholder, code in code_blocks.items():
        text = text.replace(placeholder, code)
    return text

def attack_cleaner(con):
    # 提取代码块
    cleaned_markdown, code_blocks = extract_code_blocks(con)
    # 使用bleach清理Markdown内容，不包括代码块
    cleaned_markdown = bleach.clean(cleaned_markdown)
    # 恢复代码块
    con = restore_code_blocks(cleaned_markdown, code_blocks)
    return con

@user_app.route('/modifier_intro', methods=['POST'])
def modifier_intro():
    username = request.form.get('username')
    # dic = db.users.find_one({'username': username})
    dic = dbConnecter.read_data('users', 'username', username)[0]
    user_captcha = request.form.get('user_captcha').lower()
    if user_captcha != session['captcha']:
        captcha_text, captcha_image = defender.generate_captcha()
        session['captcha'] = captcha_text.lower()
        return render_template('user/modify_intro.html',
                               t_info=dic['intro'],
                               t_username=username,
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image,
                               t_error='Wrong graph validate code')
    intro = attack_cleaner(request.form.get('intro'))
    # dic = db.users.find_one({'username': username})
    # dic = dbConnecter.read_data('users', 'username', username)[0]
    # s = ''
    # info = []
    # for i in intro:
    #     if i == '\n':
    #         continue
    #     if i == '\r':
    #         info.append(s)
    #         s = ''
    #     else:
    #         s += i
    # info.append(s)
    # dic['intro'] = attack_cleaner(intro)
    # db.users.update({'username': username}, dic)
    dbConnecter.update_data('users', 'username', username, 'intro', intro)
    return redirect('/profile?username=' + username)

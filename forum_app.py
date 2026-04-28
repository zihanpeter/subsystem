from flask import render_template, request, session, redirect, Blueprint, abort
import uuid
import time
import markdown
import bleach
import re

from lib import dbConnecter, defender
import os


forum_app = Blueprint('forum_app', __name__)
forum_app.secret_key = os.getenv('SECRET_KEY')
# client = pymongo.MongoClient()
# db = client.reciter

'''
    集合名articles

    id 文章id
    username 用户名
    title 标题
    content 内容
    timef 发布时间
    top 是否置顶
    comment 评论: id username content timef to
    
    CREATE TABLE articles (
        id VARCHAR(128), 
        username VARCHAR(64), 
        title VARCHAR(128), 
        content TEXT, 
        timef VARCHAR(64), 
        top BOOL
    );
    
    CREATE TABLE comment (
        id VARCHAR(128), 
        commentid VARCHAR(128), 
        username VARCHAR(64), 
        content TEXT, 
        timef VARCHAR(128), 
        to1 VARCHAR(64)
    );    
'''

def get_theme():
    theme = session.get('theme')
    if theme == None:
        theme = 'white'
    return theme

@forum_app.route('/forum', methods=['GET']) # 展示讨论列表
def forum():
    key = request.args.get('key')
    if key == None or key == '':
        # list_top = list(db.articles.find({'top': True}))
        # list_cmn = list(db.articles.find({'top': False}))
        list_top = dbConnecter.read_data('articles', 'top', True)
        list_cmn = dbConnecter.read_data('articles', 'top', False)
    else:
        # list_top = list(db.articles.find({'top': True, 'title': key}))
        # list_cmn = list(db.articles.find({'top': False, 'title': key}))
        list_oo = dbConnecter.read_data('articles', 'title', key)
        list_top, list_cmn = [], []
        for i in list_oo:
            if i['top']:
                list_top.append(i)
            else:
                list_cmn.append(i)
    list_top.sort(key=lambda x: x['timef'], reverse=True)
    list_cmn.sort(key=lambda x: x['timef'], reverse=True)
    show_mode = request.args.get('show_mode')
    if show_mode == None:
        show_mode = 'top'
    return render_template('forum/forum.html',
                           t_username=session.get('username'),
                           t_list_top=list_top,
                           t_list_cmn=list_cmn,
                           t_theme=get_theme(),
                           t_show_mode=show_mode)

@forum_app.route('/create_articles', methods=['GET']) # 展示创建页面
def create_articles():
    if session.get('username') == None:
        return redirect('/login')
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    # userdic = db.users.find_one({'username': session['username']})
    userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
    return render_template('forum/create_articles.html',
                           t_username=session.get('username'),
                           t_admin=userdic['admin'],
                           t_theme=get_theme(),
                           t_captcha_image=captcha_image)

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

@forum_app.route('/check_articles', methods=['POST']) # 处理创建信息
def check_disucss():
    if session.get('username') == None:
        return redirect('/login')
    user_captcha = request.form.get('user_captcha').lower()
    if user_captcha != session['captcha']:
        captcha_text, captcha_image = defender.generate_captcha()
        session['captcha'] = captcha_text.lower()
        # userdic = db.users.find_one({'username': session['username']})
        userdic = dbConnecter.read_data('users', 'username', session['username'])[0]
        return render_template('forum/create_articles.html',
                               t_username=session.get('username'),
                               t_admin=userdic['admin'],
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image,
                               t_error='Wrong graph validate code')
    title = request.form.get('title')
    con = request.form.get('content')
    id = str(uuid.uuid1())
    now = time.localtime()
    now_temp = time.strftime("%Y-%m-%d %H:%M", now)
    top = request.form.get('top')
    if top == None or top == 'False':
        top2 = False
    else:
        top2 = True
    # con = []
    # s = ''
    # for i in content:
    #     if i == '\n':
    #         continue
    #     if i == '\r':
    #         con.append(s)
    #         s = ''
    #     else:
    #         s += i
    # con.append(s)
    con = attack_cleaner(con)
    dbConnecter.insert_data('articles',
                            '(id, username, title, content, timef, top)',
                            (id, session.get('username'), title, con, now_temp, top2))
    # db.articles.insert_one({'id': id,
    #                        'username': session.get('username'),
    #                        'title': title,
    #                        'content': con,
    #                        'timef': now_temp,
    #                        'comment': [],
    #                        'top': top2})
    return redirect('/forum')

@forum_app.route('/articles', methods=['GET']) # 展示articles
def articles():
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    iid = request.args.get('id')
    # dis = db.articles.find_one({'id': iid})
    dis = dbConnecter.read_data('articles', 'id', iid)[0]
    sorter = request.args.get('sorter')
    commentList = dbConnecter.read_data('comment', 'id', iid)
    if (sorter == None or sorter == 'inverted'):
        sorter = 'inverted'
        commentList.reverse()
    sizet = len(commentList)
    content = dis['content']
    dis['comment'] = commentList
    content = markdown.markdown(content, extensions=['markdown.extensions.fenced_code',
                                                     'markdown.extensions.codehilite',
                                                     'markdown.extensions.extra',
                                                     'markdown.extensions.toc',
                                                     'markdown.extensions.tables'])
    if session.get('username') == None:
        admin = False
    else:
        # admin = db.users.find_one({'username': session['username']})['admin']
        admin = dbConnecter.read_data('users', 'username', session['username'])[0]['admin']
    errorr = request.args.get('error')
    if errorr == None:
        errorr = ''
    return render_template('forum/articles.html',
                           t_dis=dis,
                           t_username=session.get('username'),
                           t_size=sizet,
                           t_admin=admin,
                           t_sorter=sorter,
                           t_theme=get_theme(),
                           t_content=content,
                           t_error=errorr,
                           t_captcha_image=captcha_image)

# @forum_app.route('/mod_top', methods=['POST']) # 更改置顶
# def mod_top():
#     id = request.form.get('id')
#     top = request.form.get('top')
#     dis_lib = db.articles.find_one({'id': id})
#     dis_lib['top'] = top == 'true'
#     db.articles.update({'id': id}, dis_lib)
#     return redirect('/forum')

@forum_app.route('/check_del_articles', methods=['GET']) # 确认删除
def check_del_articles():
    if session.get('username') == None:
        return redirect('/login')
    id = request.args.get('id')
    return render_template('forum/check_del_articles.html',
                           t_id=id,
                           t_username=session.get('username'),
                           t_theme=get_theme(),
                           # t_title=db.articles.find_one({'id': id})['title']
                           t_title=dbConnecter.read_data('articles', 'id', id)[0]['title']
                           )

@forum_app.route('/del_articles', methods=['GET']) # 删除讨论
def del_articles():
    if session.get('username') == None:
        return redirect('/login')
    id = request.args.get('id')
    # dic = db.articles.find_one({'id': id})
    dic = dbConnecter.read_data('articles', 'id', id)[0]
    if dic['username'] == session.get('username') or dbConnecter.read_data('users', 'username', session['username'])[0]['admin']:
        # db.articles.delete_one({'id': id})
        dbConnecter.delete_data('articles', 'id', id)
        dbConnecter.delete_data('comment', 'id', id)
        return redirect('/forum')
    else:
        return 'No permission'

def check_to(to):
    # dics = db.users.find()
    dics = dbConnecter.read_data('users')
    dics = list(dics)
    for i in dics:
        if i['username'] == to and to != session.get('username'):
            return False
    return True

@forum_app.route('/post_comment', methods=['POST']) # 发布评论
def post_comment():
    user_captcha = request.form.get('user_captcha').lower()
    iid = request.form.get('id')
    if user_captcha != session['captcha']:
        return redirect('/articles?id=' + iid + '&error=Wrong graph validation code')
    con = request.form.get('content')
    usr = request.form.get('username')
    # dis = db.articles.find_one({'id': iid})
    content = ''
    s = ''
    to = None
    flag = False
    for i in con:
        if i == '\n':
            continue
        if i == '\r':
            if flag == False and s[0] == '@':
                to = s[1: len(s)]
                flag = True
            else:
                content += s
            s = ''
        else:
            s += i
    content += s
    print(content)
    if to != None and s == '':
        return redirect('/articles?id=' + iid)
    if to != None:
        if check_to(to):
            to = None
    now = time.localtime()
    now_temp = time.strftime("%Y-%m-%d %H:%M", now)
    commentid = str(uuid.uuid1())
    dbConnecter.insert_data('comment',
                            '(id, commentid, username, content, timef, to1)',
                            (iid, commentid, usr, content, now_temp, to))
    # dis['comment'].append({'content': content,
    #                        'timef': now_temp,
    #                        'username': usr,
    #                        'to': to})
    # db.articles.update({'id': iid}, dis)
    # print("-------------")
    return redirect('/articles?id=' + iid)

@forum_app.route('/del_comment', methods=['GET']) # 删除评论
def del_comment():
    if session.get('username') == None:
        return redirect('/login')
    iid = request.args.get('id')
    num = int(request.args.get('num'))
    sorter = request.args.get('sorter')
    sum = int(request.args.get('sum'))
    # dis = db.articles.find_one({'id': iid})
    commentList = dbConnecter.read_data('comment', 'id', iid)
    dis = dbConnecter.read_data('articles', 'id', iid)[0]
    if dis['username'] == session.get('username') or dbConnecter.read_data('users', 'username', session['username'])[0]['admin']:
        if sorter == 'inverted':
            num = sum - 1 - num
        # dis = db.articles.find_one({'id': iid})
        dbConnecter.delete_data('comment', 'commentid', commentList[num]['commentid'])
        # del dis['comment'][num]
        # db.articles.update({'id': iid}, dis)
        return redirect('/articles?id=' + iid)
    else:
        return 'No permission'

@forum_app.route('/modify_articles', methods=['GET']) # provide the modifier page
def modify_articles():
    if session.get('username') == None:
        return redirect('/login')
    captcha_text, captcha_image = defender.generate_captcha()
    session['captcha'] = captcha_text.lower()
    iid = request.args.get('id')
    # dic = db.articles.find_one({'id': iid})
    dic = dbConnecter.read_data('articles', 'id', iid)[0]
    admin = dbConnecter.read_data('users', 'username', session['username'])[0]['admin']
    # admin = db.users.find_one({'username': session['username']})['admin']
    if dic['username'] == session.get('username') or admin:
        title = dic['title']
        # info = ''
        # for i in dic['content']:
        #     info += i + '\n'
        errorr = request.args.get('error')
        if errorr == None:
            errorr = ''
        return render_template('forum/modify_articles.html',
                               t_title=title,
                               t_info=dic['content'],
                               t_admin=admin,
                               t_id=iid,
                               t_username=session.get('username'),
                               t_theme=get_theme(),
                               t_captcha_image=captcha_image,
                               t_error=errorr)
    else:
        return 'No permission'

@forum_app.route('/modifier_articles', methods=['POST']) # check the modified information
def modifier_articles():
    if session.get('username') == None:
        return redirect('/login')
    user_captcha = request.form.get('user_captcha').lower()
    iid = request.form.get('id')
    if user_captcha != session['captcha']:
        return redirect('/modify_articles?id=' + iid + '&error=Wrong graph validate code')
    title = request.form.get('title')
    content = request.form.get('content')
    top = request.form.get('top')
    # dic = db.articles.find_one({'id': iid})
    dic = dbConnecter.read_data('articles', 'id', iid)[0]
    if top == 'False':
        top2 = False
    elif top == 'True':
        top2 = True
    else:
        top2 = dic['top']
    # con = []
    # s = ''
    # for i in content:
    #     if i == '\n':
    #         continue
    #     if i == '\r':
    #         con.append(s)
    #         s = ''
    #     else:
    #         s += i
    # con.append(s)
    dic['title'] = title
    dic['content'] = attack_cleaner(content)
    dic['top'] = top2
    dbConnecter.delete_data('articles', 'id', iid)
    dbConnecter.insert_data('articles',
                            '(id, username, title, content, timef, top)',
                            (iid, dic['username'], dic['title'], dic['content'], dic['timef'], dic['top']))
    # db.articles.update({'id': iid}, dic)
    return redirect('/forum')

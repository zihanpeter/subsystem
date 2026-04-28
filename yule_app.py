from flask import render_template, request, session, redirect, Blueprint, abort
import pymongo
import markdown
import os

from lib import dbConnecter

yule_app = Blueprint('yule_app', __name__)
yule_app.secret_key = os.getenv('SECRET_KEY')
# client = pymongo.MongoClient()
# db = client.reciter

'''
    集合名 yule

    name 游戏名
    hot 游戏热度
    path 游戏html文件路径
    intro 游戏介绍路径
    timef 创建时间
    creator 创建者
    
    CREATE TABLE yule (
        name VARCHAR(128), 
        hot INT, 
        path VARCHAR(256), 
        intro VARCHAR(256), 
        timef VARCHAR(64), 
        creator VARCHAR(128)
    );
'''

def get_theme():
    theme = session.get('theme')
    if theme == None:
        theme = 'white'
    return theme

@yule_app.route('/yule')
def yule():
    # dics = db.yule.find()
    # dics = list(dics)
    dics = dbConnecter.read_data('yule')
    dics.sort(key=lambda x: x['hot'], reverse=True)
    return render_template('yule/yule.html',
                           t_dics=dics,
                           t_theme=get_theme(),
                           t_username=session.get('username'))

@yule_app.route('/intro', methods=['GET'])
def intro():
    name = request.args.get('name')
    # dic = db.yule.find_one({'id': id})
    dic = dbConnecter.read_data('yule', 'name', name)[0]
    intro_path = dic['intro']
    print(intro_path)
    with open(intro_path, 'r', encoding='utf-8') as file:
        content = file.read()
    content = markdown.markdown(content, extensions=['markdown.extensions.fenced_code',
                                                     'markdown.extensions.codehilite',
                                                     'markdown.extensions.extra',
                                                     'markdown.extensions.toc',
                                                     'markdown.extensions.tables'])
    return render_template('yule/intro.html',
                           t_name=dic['name'],
                           t_intro=content,
                           t_username=session.get('username'),
                           t_theme=get_theme(),
                           t_timef=dic['timef'],
                           t_creator=dic['creator'],
                           t_hot=dic['hot'])

@yule_app.route('/games', methods=['GET'])
def games():
    if session.get('username') == None:
        return redirect('/login')
    name = request.args.get('name')
    r = dbConnecter.read_data('yule', 'name', name)[0]
    # r = db.yule.find_one({'id': id})
    r['hot'] += 1
    # db.yule.update({'id': id}, r)
    dbConnecter.update_data('yule', 'name', name, 'hot', r['hot'])
    return render_template(r['path'],
                           t_home='/yule',
                           t_username=session.get('username'))

@yule_app.route('/yulewordlist')
def get_wordlist():
    with open('static/source/wordlist.txt', 'r', encoding='utf-8') as file:
        return file.read()

@yule_app.route('/yulecsw22')
def get_csw22():
    with open('static/source/CSW22.txt', 'r', encoding='utf-8') as file:
        return file.read()

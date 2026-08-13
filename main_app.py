from flask import Flask, render_template, send_from_directory, session, request, abort
import markdown

from user_app import user_app
from recite_app import recite_app
from forum_app import forum_app
from yule_app import yule_app
from lib.config_loader import get_config


app = Flask(__name__)
app.secret_key = get_config('SECRET_KEY')
app.register_blueprint(user_app)
app.register_blueprint(recite_app)
app.register_blueprint(forum_app)
app.register_blueprint(yule_app)
# client = pymongo.MongoClient()
# db = client.reciter

@app.context_processor
def inject_layout_context(): # 布局(导航栏)所需的全局变量
    return {'current_user': session.get('username')}

@app.route('/favicon.ico') # 浏览器默认会请求根路径图标
def favicon():
    return send_from_directory('static/images', 'site-icon.ico',
                               mimetype='image/vnd.microsoft.icon')

@app.route('/')
def main():
    username = session.get('username')
    # s = 0
    # e = 5
    # lists = list(db.lists.find())
    # top = list(db.articles.find({'top': True}))
    # rec = list(db.articles.find({'top': False}))
    # lists.sort(key=lambda x: x['timef'], reverse=True)
    # rec.sort(key=lambda x: x['timef'], reverse=True)
    # top.sort(key=lambda x: x['timef'], reverse=True)
    # lists = lists[s: e]
    # rec = rec[s: e]
    with open('static/md/main/main.md', 'r', encoding='utf-8') as file:
        content = file.read()
    content = markdown.markdown(content, extensions=['markdown.extensions.fenced_code',
                                                     'markdown.extensions.codehilite',
                                                     'markdown.extensions.extra',
                                                     'markdown.extensions.toc',
                                                     'markdown.extensions.tables'])
    return render_template('main/main.html',
                           t_content=content,
                           t_username=username)

if __name__ == '__main__':
    app.run(debug=True, port=5050)

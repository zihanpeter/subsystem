import os
import sqlite3


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, 'cache', 'subsystem.db')

# users.username 用 NOCASE, 和原来 MySQL 一样不区分大小写, 注册时 Alice 和 alice 算同一个人
SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(64) COLLATE NOCASE,
    password VARCHAR(64),
    timef VARCHAR(64),
    intro TEXT,
    theme VARCHAR(64),
    admin BOOL
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

CREATE TABLE IF NOT EXISTS lists (
    id VARCHAR(128),
    username VARCHAR(64),
    listname VARCHAR(64),
    difficulty INT,
    en TEXT,
    zh TEXT,
    timef VARCHAR(64),
    o BOOL,
    sm BOOL,
    sen TEXT,
    priv BOOL NOT NULL DEFAULT 0,
    folder_id VARCHAR(128) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_lists_id ON lists (id);

CREATE TABLE IF NOT EXISTS folders (
    id VARCHAR(128) NOT NULL,
    foldername VARCHAR(64) NOT NULL,
    username VARCHAR(64) NOT NULL,
    timef VARCHAR(64) NOT NULL,
    scope VARCHAR(16) NOT NULL DEFAULT 'official',
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS word_progress (
    username VARCHAR(64) NOT NULL,
    list_id VARCHAR(128) NOT NULL,
    word VARCHAR(255) NOT NULL,
    level TINYINT NOT NULL DEFAULT 0,
    next_review DATE NOT NULL,
    seen INT NOT NULL DEFAULT 0,
    correct INT NOT NULL DEFAULT 0,
    wrong INT NOT NULL DEFAULT 0,
    PRIMARY KEY (username, list_id, word)
);
CREATE INDEX IF NOT EXISTS idx_due ON word_progress (username, list_id, next_review);

CREATE TABLE IF NOT EXISTS daily_task (
    username VARCHAR(64) NOT NULL,
    list_id VARCHAR(128) NOT NULL,
    day DATE NOT NULL,
    target_json TEXT NOT NULL,
    done_json TEXT NOT NULL,
    retry_json TEXT NOT NULL,
    PRIMARY KEY (username, list_id, day)
);

CREATE TABLE IF NOT EXISTS articles (
    id VARCHAR(128),
    username VARCHAR(64),
    title VARCHAR(128),
    content TEXT,
    timef VARCHAR(64),
    top BOOL
);
CREATE INDEX IF NOT EXISTS idx_articles_id ON articles (id);

CREATE TABLE IF NOT EXISTS comment (
    id VARCHAR(128),
    commentid VARCHAR(128),
    username VARCHAR(64),
    content TEXT,
    timef VARCHAR(128),
    to1 VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_comment_id ON comment (id);
CREATE INDEX IF NOT EXISTS idx_comment_commentid ON comment (commentid);

CREATE TABLE IF NOT EXISTS yule (
    name VARCHAR(128),
    hot INT,
    path VARCHAR(256),
    intro VARCHAR(256),
    timef VARCHAR(64),
    creator VARCHAR(128)
);
CREATE INDEX IF NOT EXISTS idx_yule_name ON yule (name);
'''

_schema_ready = False


def init_db(connection):
    connection.execute('PRAGMA journal_mode = WAL;') # gunicorn 多个 worker 同时读写时不互相卡住
    connection.executescript(SCHEMA)
    connection.commit()


def connect_to_db():
    global _schema_ready
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    if not _schema_ready: # 每个进程第一次连上时建表, 之后不再重复
        init_db(connection)
        _schema_ready = True
    return connection

def genPlaceholder(valuename):
    placeholder = '(?'
    cnt = 0
    for i in valuename:
       if i == ',':
           cnt += 1
    for i in range(cnt):
        placeholder += ', ?'
    placeholder += ')'
    return placeholder

def insert_data(listname, valuename, values): # str str tuple
    connection = connect_to_db()
    cursor = connection.cursor()
    try:
        placeholder = genPlaceholder(valuename)
        # print(placeholder)
        sql = 'INSERT INTO ' + listname + ' ' + valuename + ' VALUES ' + placeholder + ';'
        cursor.execute(sql, values)
        connection.commit()
        print(f"Inserted {cursor.rowcount} record(s).")
    except sqlite3.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def read_data(listname, con='', val=None):
    connection = connect_to_db()
    cursor = connection.cursor()
    try:
        if (con == ''):
            sql = 'SELECT * FROM ' + listname + ';'
            cursor.execute(sql)
        else:
            sql = 'SELECT * FROM ' + listname + ' WHERE ' + con + ' = ?;'
            cursor.execute(sql, (val,))
        results = [dict(row) for row in cursor.fetchall()]
        # for row in results:
        #     print(row)
        # print(results)
        return results
    except sqlite3.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def update_data(listname, con, val1, tar, val2):
    connection = connect_to_db()
    cursor = connection.cursor()
    try:
        sql = 'UPDATE ' + listname + ' SET ' + tar + ' = ? WHERE ' + con + ' = ?;'
        cursor.execute(sql, (val2, val1))
        connection.commit()
        print(f"Updated {cursor.rowcount} record(s).")
    except sqlite3.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def delete_data(listname, con, val):
    connection = connect_to_db()
    cursor = connection.cursor()
    try:
        sql = 'DELETE FROM ' + listname + ' WHERE ' + con + ' = ?;'
        cursor.execute(sql, (val,))
        connection.commit()
        print(f"Deleted {cursor.rowcount} record(s).")
    except sqlite3.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def deltete_list(listname):
    connection = connect_to_db()
    cursor = connection.cursor()
    try:
        sql = 'DROP TABLE IF EXISTS ' + listname + ';'
        cursor.execute(sql)
        connection.commit()
        print(f"Deleted {cursor.rowcount} record(s).")
    except sqlite3.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

# 调用函数测试
if __name__ == "__main__":
    # insert_data('test2', '(test1, test2)', ('["1", "2", "3"]', '["1", "2", "3"]'))
    # print(read_data('test2'))
    # print(list(read_data('test2')[0]['test1']))
    # print(read_data('test', 'timef', 2024))
    # update_data('test', 'username', 'hello', 'timef', 2088)
    # delete_data('test', 'timef', 2024)
    # print(read_data('test'))
    # a = ["1", "2", "3"]
    # print(str(a))
    # read_data()
    # insert_data('test3', '(h1, h2)', ('19238u8u2u4990', '2134532456453256y6432435676564'))
    read_data('yule', 'name', 'TwentyFortyEightGame')

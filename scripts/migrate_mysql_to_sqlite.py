#!/usr/bin/env python3
"""把 MySQL 里的 subsystem 库整库搬进 cache/subsystem.db (SQLite).

在服务器上(MySQL 所在机器)的项目根目录执行:
    .venv/bin/python scripts/migrate_mysql_to_sqlite.py

也可以在本地通过 SSH 隧道连服务器的 MySQL:
    ssh -N -L 3307:127.0.0.1:3306 user@your-server
    python scripts/migrate_mysql_to_sqlite.py --port 3307 --password '...'

只读 MySQL, 不会改动服务器上的原数据. 先写到临时文件, 全部校验通过后才替换目标文件.
"""
import argparse
import datetime
import decimal
import getpass
import os
import sqlite3
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from lib.config_loader import get_config  # noqa: E402
from lib.dbConnecter import DB_PATH, init_db  # noqa: E402

BATCH_SIZE = 1000


def parse_args():
    parser = argparse.ArgumentParser(description='Export MySQL data into the SQLite file used by the app.')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='root')
    parser.add_argument('--password', default=None,
                        help='默认读项目根目录 .env 里的 MYSQL_PASSWORD, 没有就交互输入')
    parser.add_argument('--database', default='subsystem')
    parser.add_argument('--output', default=DB_PATH, help='SQLite 文件路径, 默认 cache/subsystem.db')
    parser.add_argument('--force', action='store_true', help='目标文件已存在时覆盖(会先备份成 .bak)')
    return parser.parse_args()


def connect_mysql(args):
    try:
        import mysql.connector
    except ImportError:
        sys.exit('缺少 mysql-connector-python, 先执行: pip install mysql-connector-python')
    password = args.password
    if password is None:
        old_cwd = os.getcwd()
        os.chdir(ROOT_DIR) # config_loader 从当前目录找 .env
        try:
            password = get_config('MYSQL_PASSWORD')
        finally:
            os.chdir(old_cwd)
    if password is None:
        password = getpass.getpass('MySQL password for %s@%s: ' % (args.user, args.host))
    return mysql.connector.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=password,
        database=args.database,
        charset='utf8mb4',
    )


def to_sqlite_value(value):
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, datetime.timedelta): # MySQL TIME 列
        return str(value)
    if isinstance(value, decimal.Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            return bytes(value).decode('utf-8')
        except UnicodeDecodeError:
            return bytes(value)
    return value


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def sqlite_type(mysql_type): # enum('a','b') 之类的 MySQL 类型名 SQLite 不认, 换成同类的亲和类型
    t = mysql_type.lower()
    if 'int' in t or t.startswith(('bool', 'bit')):
        return 'INTEGER'
    if t.startswith(('float', 'double', 'real')):
        return 'REAL'
    if t.startswith(('decimal', 'numeric')):
        return 'NUMERIC'
    if 'blob' in t or 'binary' in t:
        return 'BLOB'
    return 'TEXT'


def mysql_columns(mysql_conn, table):
    cursor = mysql_conn.cursor()
    cursor.execute('SHOW COLUMNS FROM `%s`;' % table.replace('`', '``'))
    rows = cursor.fetchall()
    cursor.close()
    return [(to_sqlite_value(r[0]), to_sqlite_value(r[1])) for r in rows] # (列名, 类型)


def sqlite_columns(sqlite_conn, table):
    return [r[1] for r in sqlite_conn.execute('PRAGMA table_info(%s);' % quote(table))]


def prepare_table(sqlite_conn, table, src_cols):
    """保证 SQLite 里有这张表, 且源表的每一列都有地方放."""
    dst_cols = sqlite_columns(sqlite_conn, table)
    if not dst_cols: # 代码里没用到的表(比如测试表)也原样搬过来, 不丢数据
        print('  [提示] %s 不在应用的表结构里, 按源表列原样建表' % table)
        defs = ', '.join('%s %s' % (quote(name), sqlite_type(col_type)) for name, col_type in src_cols)
        sqlite_conn.execute('CREATE TABLE %s (%s);' % (quote(table), defs))
        return
    for name, col_type in src_cols:
        if name not in dst_cols:
            print('  [提示] %s.%s 不在应用的表结构里, 补上这一列' % (table, name))
            sqlite_conn.execute('ALTER TABLE %s ADD COLUMN %s %s;'
                                % (quote(table), quote(name), sqlite_type(col_type)))
    for name in dst_cols:
        if name not in [c[0] for c in src_cols]:
            print('  [提示] 源表 %s 没有 %s 列, 新库里用默认值' % (table, name))


def copy_table(mysql_conn, sqlite_conn, table):
    src_cols = mysql_columns(mysql_conn, table)
    prepare_table(sqlite_conn, table, src_cols)
    names = [c[0] for c in src_cols]
    select_sql = 'SELECT %s FROM `%s`;' % (', '.join('`%s`' % n.replace('`', '``') for n in names),
                                          table.replace('`', '``'))
    insert_sql = 'INSERT INTO %s (%s) VALUES (%s);' % (
        quote(table), ', '.join(quote(n) for n in names), ', '.join('?' * len(names)))
    # 不加 ORDER BY: 评论等表没有主键, 按 MySQL 原来的插入顺序搬, 页面上的顺序才不会变
    cursor = mysql_conn.cursor()
    cursor.execute(select_sql)
    copied = 0
    while True:
        rows = cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break
        sqlite_conn.executemany(insert_sql, [tuple(to_sqlite_value(v) for v in row) for row in rows])
        copied += len(rows)
    cursor.close()
    return copied


def count_mysql(mysql_conn, table):
    cursor = mysql_conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM `%s`;' % table.replace('`', '``'))
    n = cursor.fetchone()[0]
    cursor.close()
    return n


def main():
    args = parse_args()
    output = os.path.abspath(args.output)
    if os.path.exists(output) and not args.force:
        sys.exit('%s 已存在. 确认要用 MySQL 的数据覆盖它的话加 --force' % output)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    tmp_path = output + '.tmp'
    for suffix in ('', '-wal', '-shm'):
        if os.path.exists(tmp_path + suffix):
            os.remove(tmp_path + suffix)

    mysql_conn = connect_mysql(args)
    print('已连接 MySQL %s@%s:%s/%s' % (args.user, args.host, args.port, args.database))
    # 一致性快照: 迁移过程中网站还在写的话, 也能拿到同一时刻的数据
    mysql_conn.start_transaction(consistent_snapshot=True, readonly=True)

    cursor = mysql_conn.cursor()
    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE';")
    tables = [to_sqlite_value(r[0]) for r in cursor.fetchall()]
    cursor.close()
    print('要迁移的表: %s' % ', '.join(tables))

    sqlite_conn = sqlite3.connect(tmp_path)
    init_db(sqlite_conn)

    results = []
    try:
        for table in tables:
            print('-> %s' % table)
            copied = copy_table(mysql_conn, sqlite_conn, table)
            sqlite_conn.commit()
            expected = count_mysql(mysql_conn, table)
            actual = sqlite_conn.execute('SELECT COUNT(*) FROM %s;' % quote(table)).fetchone()[0]
            results.append((table, expected, actual))
            print('   %d 行' % copied)
    except Exception:
        sqlite_conn.close()
        os.remove(tmp_path)
        raise
    finally:
        mysql_conn.rollback()
        mysql_conn.close()

    sqlite_conn.close()

    print('\n%-20s %10s %10s' % ('table', 'mysql', 'sqlite'))
    bad = False
    for table, expected, actual in results:
        flag = '' if expected == actual else '  <-- 不一致'
        bad = bad or flag != ''
        print('%-20s %10d %10d%s' % (table, expected, actual, flag))
    if bad:
        os.remove(tmp_path)
        sys.exit('\n行数对不上, 没有写入 %s' % output)

    if os.path.exists(output):
        backup = output + '.bak'
        os.replace(output, backup)
        print('\n原来的 %s 已备份到 %s' % (output, backup))
    for suffix in ('-wal', '-shm'): # 旧库残留的 WAL 文件会被套到新库上, 必须清掉
        if os.path.exists(output + suffix):
            os.remove(output + suffix)
    os.replace(tmp_path, output)
    print('\n完成, 数据已写入 %s' % output)


if __name__ == '__main__':
    main()

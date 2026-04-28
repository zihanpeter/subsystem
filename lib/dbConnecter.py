import mysql.connector
import os


'''
// Create DATABASE
CREATE DATABASE database_name;


// Create TABLE
CREATE TABLE table_name (
    column1 datatype constraint,
    column2 datatype constraint,
    column3 datatype constraint,
    ...
);

'''

def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv('MYSQL_PASSWORD'),
        # password="my_password",
        database='subsystem'
    )

def genPlaceholder(valuename):
    placeholder = '(%s'
    cnt = 0
    for i in valuename:
       if i == ',':
           cnt += 1
    for i in range(cnt):
        placeholder += ', %s'
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
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def read_data(listname, con='', val=None):
    connection = connect_to_db()
    cursor = connection.cursor(dictionary=True)
    try:
        if (con == ''):
            sql = 'SELECT * FROM ' + listname + ';'
            cursor.execute(sql)
        else:
            sql = 'SELECT * FROM ' + listname + ' WHERE ' + con + ' = %s;'
            cursor.execute(sql, (val,))
        results = cursor.fetchall()
        # for row in results:
        #     print(row)
        # print(results)
        return results
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def update_data(listname, con, val1, tar, val2):
    connection = connect_to_db()
    cursor = connection.cursor()
    try:
        sql = 'UPDATE ' + listname + ' SET ' + tar + ' = %s WHERE ' + con + ' = %s;'
        cursor.execute(sql, (val2, val1))
        connection.commit()
        print(f"Updated {cursor.rowcount} record(s).")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def delete_data(listname, con, val):
    connection = connect_to_db()
    cursor = connection.cursor()
    try:
        sql = 'DELETE FROM ' + listname + ' WHERE ' + con + ' = %s;'
        cursor.execute(sql, (val,))
        connection.commit()
        print(f"Deleted {cursor.rowcount} record(s).")
    except mysql.connector.Error as err:
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
    except mysql.connector.Error as err:
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

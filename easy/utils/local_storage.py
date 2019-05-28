import json
from typing import Union
from easy.base.sqlite3_base import Sqlite3Base

# Fixed setting for localVar
local_db = 'local_storage.sqlite3'  # NO :memory: for persistence
local_table = 'local_storage_data_table'


def put(key, value: Union[int, str, dict], valid_seconds=3600, category='auto'):
    """
    :param key: key-str
    :param value: value-str or dict (json.loads()able)
    :param valid_seconds: 有效时长
    :param category: 类目，默认：auto
    :return:
    """
    assert isinstance(valid_seconds, int) and valid_seconds > 0, '有效时长秒数valid_seconds必须为正整数，如：3600'
    # 如果表「local_table」不存在则新建
    table_create = """CREATE TABLE IF NOT EXISTS %s (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                        key text NOT NULL,
                                        value text NOT NULL,                                        
										category TEXT DEFAULT 'auto',
										expired_at REAL NULL,
										created_at REAL DEFAULT (datetime('now','localtime')),
										UNIQUE(key,category)
                                    );""" % local_table

    # 如果数据不存在则插入，如果key/category存在则更新
    if isinstance(value, dict):
        value = json.dumps(value)
    else:
        value = str(value)

    sql_item = """INSERT OR REPLACE INTO {0} (key,value,category,expired_at) 
                    VALUES('{1}','{2}','{3}',datetime('now','localtime','+{4} seconds'));
                    """.format(local_table, key, value, category, valid_seconds)

    db = Sqlite3Base(database=local_db)
    db.execute_non_query(table_create)
    return db.execute_insert(sql_item)


def delete(key, category='auto'):
    sql_delete = """DELETE FROM %s WHERE key='%s' AND category='%s'""" % (local_table, key, category)

    db = Sqlite3Base(database=local_db)
    return db.execute_non_query(sql_delete)


def get(key, category='auto', default_value=None):
    sql_get = """SELECT value from %s WHERE key='%s'""" % (local_table, key)
    sql_get += """ AND expired_at>datetime('now','localtime')"""
    sql_get += """ AND category='%s'""" % category if category else ''

    db = Sqlite3Base(database=local_db)
    value = db.execute_query_one_value(sql_get)
    value = value or default_value
    return value


def unset_expired():
    sql_unset = """DELETE FROM %s WHERE expired_at<datetime('now','localtime')""" % local_table

    db = Sqlite3Base(database=local_db)
    return db.execute_non_query(sql_unset)


if __name__ == '__main__':
    put('key_a', 123)
    print(get('key_a'))
    delete('key_a', category='abc')
    delete('key_a')

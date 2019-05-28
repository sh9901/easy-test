import logging
import sqlite3
from collections.abc import Iterable


class Sqlite3Base(object):
    def __init__(self, database,
                 # timeout=None,
                 # detect_types=None,
                 # isolation_level=None,
                 # check_same_thread=None,
                 # factory=None,
                 # cached_statements=None,
                 # uri=None
                 ):
        assert database, 'database参数必须提供'
        self.db_config = {
            'database': database,
            # 'timeout': timeout,
            # 'detect_types': detect_types,
            # 'isolation_level': isolation_level,
            # 'check_same_thread': check_same_thread,
            # 'factory': factory,
            # 'cached_statements': cached_statements,
            # 'uri': uri
        }

    def execute_query_all(self, sql: str = None, args: Iterable = (), info=None, **db_config):
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(db_config)
        try:
            con = sqlite3.connect(**self.db_config)
            return con.cursor().execute(sql, args).fetchall()
        except Exception as e:
            logging.fatal('db查询失败,exception:[%s]，sql:[%s], connection:[%s]' % (e, sql, self.db_config))

    def execute_query_one(self, sql: str = None, args: Iterable = (), info=None, **db_config):
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(db_config)
        try:
            con = sqlite3.connect(**self.db_config)
            return con.cursor().execute(sql, args).fetchone()
        except Exception as e:
            logging.fatal('db查询失败,exception:[%s]，sql:[%s], connection:[%s]' % (e, sql, self.db_config))

    def execute_query_one_value(self, sql: str = None, args: Iterable = (), info=None, **db_config):
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(db_config)
        try:
            con = sqlite3.connect(**self.db_config)
            result = con.cursor().execute(sql, args).fetchone()
            if result:
                return result[0]
        except Exception as e:
            logging.fatal('db查询失败,exception:[%s]，sql:[%s], connection:[%s]' % (e, sql, self.db_config))

    def execute_non_query(self, sql: str = None, args: Iterable = (), info=None, **db_config):
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(db_config)
        try:
            con = sqlite3.connect(**self.db_config)
            rows_affected = con.cursor().execute(sql, args).rowcount
            con.commit()
            return rows_affected
        except Exception as e:
            logging.fatal('db查询失败,exception:[%s]，sql:[%s], connection:[%s]' % (e, sql, self.db_config))

    def execute_insert(self, sql: str = None, args: Iterable = (), info=None, **db_config):
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(db_config)
        try:
            con = sqlite3.connect(**self.db_config)
            cursor = con.cursor()
            cursor.execute(sql, args)
            con.commit()
            return cursor.lastrowid
        except Exception as e:
            logging.fatal('db查询失败,exception:[%s]，sql:[%s], connection:[%s]' % (e, sql, self.db_config))

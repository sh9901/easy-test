import pymysql
from pymysql.cursors import DictCursor
import logging

logger = logging.getLogger(__name__)


class MySQLDb(object):
    """MySQL 基本操作封装"""

    def __init__(self, host=None, user=None, password=None, database=None, port: int = 3306, cursor_class=DictCursor, connect_timeout=10, charset='utf8', autocommit=True):
        assert host is not None, 'db host is required'
        assert isinstance(port, int) and port > 0, 'port must be positive integer'
        assert user is not None, 'db user is required'
        assert password is not None, 'db password is required'

        self.db_config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'port': port,
            'cursorclass': cursor_class,
            'connect_timeout': connect_timeout,
            'charset': charset,
            'autocommit': autocommit
        }

        # print('Connect DB with:{0}'.format(self.__dict__))

    def execute_query_many(self, sql: str, args: list = None, info=None, **dbconfig_kwargs) -> list:
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(dbconfig_kwargs)
        connection = pymysql.connect(**self.db_config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, args)
                results = cursor.fetchall()
                return results
        except:
            raise
        finally:
            connection.close()  # pymysql <=0.9.2 context manager bug，不自动关闭connection-计划迁往0.9.3

    def execute_query_one(self, sql: str, args: list = None, info=None, **dbconfig_kwargs) -> dict:
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(dbconfig_kwargs)
        connection = pymysql.connect(**self.db_config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, args)
                result = cursor.fetchone()
                return result
        except:
            raise
        finally:
            connection.close()

    def execute_query_one_value(self, sql: str, args: list = None, info=None, **dbconfig_kwargs) -> object:
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(dbconfig_kwargs)
        assert self.db_config.get('cursorclass') == DictCursor, 'execute_query_one_value only support DictCursor!!!'
        connection = pymysql.connect(**self.db_config)
        try:
            with pymysql.connect(**self.db_config) as cursor:
                cursor.execute(sql, args)
                result = cursor.fetchone()
                if result:
                    return list(result.values())[0]
        except:
            raise
        finally:
            connection.close()

    def execute_non_query(self, sql: str, args: list = None, info=None, **dbconfig_kwargs):
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(dbconfig_kwargs)
        connection = pymysql.connect(**self.db_config)
        try:
            with pymysql.connect(**self.db_config) as cursor:
                rows_affected = cursor.execute(sql, args)
                return rows_affected
        except:
            raise
        finally:
            connection.close()

    def execute_insert(self, sql: str, args: list = None, info=None, **dbconfig_kwargs) -> int:
        logging.info('%sExecuting SQL:%s%s' % ('[%s]' % info if info else '', sql, ',PARAMS:%s' % str(args) if args else ''))
        self.db_config.update(dbconfig_kwargs)
        connection = pymysql.connect(**self.db_config)
        try:
            with pymysql.connect(**self.db_config) as cursor:
                cursor.execute(sql, args)
                return cursor.lastrowid
        except:
            raise
        finally:
            connection.close()

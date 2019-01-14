# import pymysql
# from pymysql.cursors import DictCursor
# import logging
#
# logger = logging.getLogger(__name__)
#
#
# class MySQLDb092(object):
#     """MySQL 基本操作封装"""
#
#     def __init__(self, host=None, user=None, password=None, database=None, port: int = 3306, cursor_class=DictCursor, connect_timeout=10, charset='utf8', autocommit=True):
#         assert host is not None, 'db host没有提供'
#         assert isinstance(port, int) and port > 0, 'port为大于0数值'
#         assert user is not None, 'db用户没有提供'
#         assert password is not None, 'db密码没有提供'
#
#         self.db_config = {
#             'host': host,
#             'user': user,
#             'password': password,
#             'database': database,
#             'port': port,
#             'cursorclass': cursor_class,
#             'connect_timeout': connect_timeout,
#             'charset': charset,
#             'autocommit': autocommit
#         }
#
#         # print('Connect DB with:{0}'.format(self.__dict__))
#
#     def execute_query_many(self, sql: str, args: list = None, info=None, **dbconfig_kwargs) -> list:
#         print('{0}执行SQL:{1}'.format('%s: ' % info if info else '', sql), '参数:%s' % str(args) if args else '')
#         self.db_config.update(dbconfig_kwargs)
#         with pymysql.connect(**self.db_config) as cursor:
#             cursor.execute(sql, args)
#             results = cursor.fetchall()
#             return results
#
#     def execute_query_one(self, sql: str, args: list = None, info=None, **dbconfig_kwargs) -> dict:
#         print('{0}执行SQL:{1}'.format('%s: ' % info if info else '', sql), '参数:%s' % str(args) if args else '')
#         self.db_config.update(dbconfig_kwargs)
#         with pymysql.connect(**self.db_config) as cursor:
#             cursor.execute(sql, args)
#             result = cursor.fetchone()
#             return result
#
#     def execute_query_one_value(self, sql: str, args: list = None, info=None, **dbconfig_kwargs) -> object:
#         print('{0}执行SQL:{1}'.format('%s: ' % info if info else '', sql), '参数:%s' % str(args) if args else '')
#         self.db_config.update(dbconfig_kwargs)
#         assert self.db_config.get('cursorclass') == DictCursor, 'execute_query_one_value只支持DictCursor'
#         with pymysql.connect(**self.db_config) as cursor:
#             cursor.execute(sql, args)
#             result = cursor.fetchone()
#             if result:
#                 return list(result.values())[0]
#
#     def execute_non_query(self, sql: str, args: list = None, info=None, **dbconfig_kwargs):
#         print('{0}执行SQL:{1}'.format('%s: ' % info if info else '', sql), '参数:%s' % str(args) if args else '')
#         self.db_config.update(dbconfig_kwargs)
#         with pymysql.connect(**self.db_config) as cursor:
#             rows_affected = cursor.execute(sql, args)
#             return rows_affected

import pymssql
import logging

logger = logging.getLogger(__name__)


class MSSQLDb(object):
    """MS SQL Server 基本操作封装"""

    def __init__(self, server=None, port: int = 1433, user=None, password=None, database=None, as_dict: bool = True, timeout: int = 0, charset='utf8',
                 autocommit: bool = True):
        self._server = server
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._as_dict = as_dict
        self._timeout = timeout
        self._charset = charset
        self._autocommit = autocommit

    def __valid_config(self):
        assert self._server is not None, 'server不可以为空'
        assert isinstance(self._port, int) and self._port > 0, 'port为大于0数值'
        assert self._user is not None, 'user不可以为空'
        assert self._password is not None, 'password不可以为空'

    def execute_query_many(self, sql: str, args: list = None) -> list:
        logging.info('执行SQL查询:{0}'.format(sql))
        self.__valid_config()
        with pymssql.connect(server=self._server, port=self._port, user=self._user, password=self._password, database=self._database, as_dict=self._as_dict,
                             timeout=self._timeout, charset=self._charset) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, args)
            results = cursor.fetchall()
            return results

    def execute_query_one(self, sql: str, args: list = None) -> dict:
        logging.info('执行SQL查询:{0}'.format(sql))
        with pymssql.connect(server=self._server, port=self._port, user=self._user, password=self._password, database=self._database, as_dict=self._as_dict,
                             timeout=self._timeout, charset=self._charset) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, args)
            results = cursor.fetchone()
            return results

    def execute_non_query(self, sql: str, args: list) -> int:
        logging.info('执行SQL:{0}'.format(sql))
        self.__valid_config()
        with pymssql.connect(server=self._server, port=self._port, user=self._user, password=self._password, database=self._database, as_dict=self._as_dict,
                             timeout=self._timeout, charset=self._charset, autocommit=self._autocommit) as conn:
            cursor = conn.curser()
            rows_affected = cursor.execute(sql, args)
            if not self._autocommit:
                conn.commit()
            return rows_affected

import sqlite3
# import apsw

class SqliteDAO:
    def __init__(self, path, use_cache):
        self.db_path = path
        self.use_cache = use_cache
        self.conn = None

    # def start_connect(self):
    #     # sqlite3.connect(self.db_path)
    #     self.conn = apsw.Connection(":memory:")
    #     connection=apsw.Connection(self.db_path)
    #     with self.conn.backup("main", connection, "main") as backup:
    #         backup.step() # copy whole database in one go

    def start_connect(self):
        self.conn = sqlite3.connect(self.db_path)

    def close_connect(self):
        if self.conn is not None:
            self.conn.close()

    @property
    def cursor(self):
        try:
            sql_cursor = self.conn.cursor()
        except:
            # self.closeconnect()
            self.startconnect()
            sql_cursor = self.conn.cursor()
        return sql_cursor

    def startconnect(self):
        self.conn = sqlite3.connect(self.db_path)

    def closeconnect(self):
        if self.conn is not None:
            self.conn.close()

    def __getstate__(self):
        state = dict(self.__dict__)
        state['conn'] = None
        return state

    def _select(self, sql, keys, params = ()):  # 执行查询语句
        sql_cursor = self.cursor

        rows = sql_cursor.execute(sql, params)
        result = list()
        for row in rows:
            cols = {_key: row[i] for i, _key in enumerate(keys)}
            result.append(cols)
        return result

    def _simple_select(self, sql, params = ()):
        sql_cursor = self.cursor
        rows = sql_cursor.execute(sql, params)
        return list(rows)

    def _execute(self, sql, params):  # 执行增删改语句
        conn = sqlite3.connect(self.db_path)
        sql_cursor = conn.cursor()
        rows = sql_cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return rows

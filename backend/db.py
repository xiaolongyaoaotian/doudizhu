#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""牌友斗地主 · 存储层
默认 JSON 文件；可选 SQLite（本地 SQL 文件）或 MySQL/PostgreSQL（连接串注入）。
选择方式（环境变量）：
    DDZ_DB=json                       → backend/data/db.json（默认）
    DDZ_DB=sqlite                     → backend/data/ddz.sqlite（可用 DDZ_SQLITE_PATH 覆盖）
    DDZ_DB_URL=mysql://user:pwd@host:3306/dbname   → MySQL（需 pip install pymysql）
    DDZ_DB_URL=postgres://user:pwd@host:5432/dbname → PostgreSQL（需 pip install psycopg2-binary）
所有后端共用 schema.sql 的两张表：ddz_users / ddz_meta，可直接用数据库工具查看或注入数据。
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
SCHEMA_SQL = """CREATE TABLE IF NOT EXISTS ddz_users (
  name VARCHAR(64) PRIMARY KEY,
  salt VARCHAR(32) NOT NULL,
  pass_hash VARCHAR(64) NOT NULL,
  coins INTEGER DEFAULT 0,
  points INTEGER DEFAULT 0,
  games INTEGER DEFAULT 0,
  wins INTEGER DEFAULT 0,
  last_checkin VARCHAR(10) DEFAULT '',
  banned INTEGER DEFAULT 0,
  created_at BIGINT DEFAULT 0,
  records_json TEXT,
  extras_json TEXT
);
CREATE TABLE IF NOT EXISTS ddz_meta (k VARCHAR(64) PRIMARY KEY, v TEXT);
"""


class JsonStore:
    """默认：backend/data/db.json"""
    def __init__(self, path=None):
        self.path = path or os.path.join(DATA_DIR, 'db.json')

    def load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def save(self, state):
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    def execute(self, sql):
        raise NotImplementedError('JSON 存储不支持执行 SQL；请切换 sqlite/mysql/postgres 后端')

    def init(self):
        pass


class SqlStoreBase:
    """SQL 公共逻辑（sqlite / mysql / postgres 子类只提供连接与占位符）"""
    placeholder = '?'

    def _connect(self):
        raise NotImplementedError

    def init(self):
        conn = self._connect()
        cur = conn.cursor()
        for stmt in SCHEMA_SQL.split(';'):
            if stmt.strip():
                cur.execute(stmt)
        conn.commit()
        cur.close()
        conn.close()

    def load(self):
        conn = self._connect()
        cur = conn.cursor()
        state = {'users': {}, 'tokens': {}, 'rooms': {}, 'queue': []}
        cur.execute('SELECT name, salt, pass_hash, coins, points, games, wins, last_checkin, banned, created_at, records_json, extras_json FROM ddz_users')
        for row in cur.fetchall():
            name, salt, ph, coins, points, games, wins, checkin, banned, created, rec_json, extras_json = row
            u = {'name': name, 'salt': salt, 'passHash': ph, 'coins': coins, 'points': points,
                 'games': games, 'wins': wins, 'lastCheckin': checkin or '', 'banned': bool(banned),
                 'createdAt': created, 'records': json.loads(rec_json or '[]')}
            u.update(json.loads(extras_json or '{}'))
            state['users'][name] = u
        cur.execute('SELECT k, v FROM ddz_meta')
        for k, v in cur.fetchall():
            state[k] = json.loads(v) if v else ({} if k != 'queue' else [])
        cur.close()
        conn.close()
        return state

    def save(self, state):
        conn = self._connect()
        cur = conn.cursor()
        ph = self.placeholder
        cur.execute('DELETE FROM ddz_users')
        for name, u in state['users'].items():
            base = {k: u[k] for k in ('name', 'salt', 'passHash', 'coins', 'points', 'games', 'wins', 'lastCheckin', 'createdAt')}
            extras = {k: v for k, v in u.items() if k not in base and k != 'records'}
            cur.execute(
                f'INSERT INTO ddz_users (name, salt, pass_hash, coins, points, games, wins, last_checkin, banned, created_at, records_json, extras_json) '
                f'VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})',
                (name, u['salt'], u['passHash'], u.get('coins', 0), u.get('points', 0), u.get('games', 0),
                 u.get('wins', 0), u.get('lastCheckin', ''), 1 if u.get('banned') else 0,
                 u.get('createdAt', 0), json.dumps(u.get('records', []), ensure_ascii=False),
                 json.dumps(extras, ensure_ascii=False)))
        for k, v in state.items():
            if k == 'users':
                continue
            cur.execute(f'DELETE FROM ddz_meta WHERE k = {ph}', (k,))
            cur.execute(f'INSERT INTO ddz_meta (k, v) VALUES ({ph},{ph})', (k, json.dumps(v, ensure_ascii=False)))
        conn.commit()
        cur.close()
        conn.close()

    def execute(self, sql):
        """管理接口：直接执行一条 SQL（仅限管理用途）"""
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall() if cur.description else []
        conn.commit()
        cur.close()
        conn.close()
        return [list(r) for r in rows]


class SqliteStore(SqlStoreBase):
    placeholder = '?'

    def __init__(self, path=None):
        self.path = path or os.path.join(DATA_DIR, 'ddz.sqlite')

    def _connect(self):
        import sqlite3
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(self.path)
        return conn


class MysqlStore(SqlStoreBase):
    placeholder = '%s'

    def __init__(self, url):
        import pymysql  # pip install pymysql
        m = re.match(r'mysql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(\w+)', url)
        if not m:
            raise ValueError('DDZ_DB_URL 格式: mysql://user:pwd@host:3306/dbname')
        self.cfg = dict(host=m.group(3), port=int(m.group(4) or 3306), user=m.group(1),
                        password=m.group(2), database=m.group(5), charset='utf8mb4',
                        autocommit=True)

    def _connect(self):
        import pymysql
        return pymysql.connect(**self.cfg)


class PostgresStore(SqlStoreBase):
    placeholder = '%s'

    def __init__(self, url):
        import psycopg2  # pip install psycopg2-binary
        self.dsn = url

    def _connect(self):
        import psycopg2
        return psycopg2.connect(self.dsn)


import re  # noqa: E402  (MysqlStore 解析用)

def make_store():
    kind = os.environ.get('DDZ_DB', 'json').lower()
    if kind == 'sqlite':
        s = SqliteStore(os.environ.get('DDZ_SQLITE_PATH'))
    elif kind == 'json':
        s = JsonStore()
    else:
        url = os.environ.get('DDZ_DB_URL', '')
        if url.startswith('mysql://'):
            s = MysqlStore(url)
        elif url.startswith(('postgres://', 'postgresql://')):
            s = PostgresStore(url)
        else:
            raise ValueError(f'未知存储配置: DDZ_DB={kind} DDZ_DB_URL={url}')
    try:
        s.init()
    except NotImplementedError:
        pass
    return s


def state_to_sql(state):
    """把内存状态导出为可执行的 SQL 文本（schema + INSERT），用于本地 SQL 备份/迁移"""
    def esc(v):
        if v is None:
            return 'NULL'
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, bool):
            return '1' if v else '0'
        return "'" + str(v).replace("'", "''") + "'"
    lines = [SCHEMA_SQL, 'DELETE FROM ddz_users;', 'DELETE FROM ddz_meta;']
    for name, u in state['users'].items():
        base = {k: u[k] for k in ('name', 'salt', 'passHash', 'coins', 'points', 'games', 'wins', 'lastCheckin', 'createdAt')}
        extras = {k: v for k, v in u.items() if k not in base and k != 'records'}
        lines.append(
            "INSERT INTO ddz_users (name, salt, pass_hash, coins, points, games, wins, last_checkin, banned, created_at, records_json, extras_json) VALUES ("
            + ', '.join(esc(x) for x in [name, u['salt'], u['passHash'], u.get('coins', 0), u.get('points', 0),
                                         u.get('games', 0), u.get('wins', 0), u.get('lastCheckin', ''),
                                         1 if u.get('banned') else 0, u.get('createdAt', 0),
                                         json.dumps(u.get('records', []), ensure_ascii=False),
                                         json.dumps(extras, ensure_ascii=False)]) + ');')
    for k, v in state.items():
        if k != 'users':
            lines.append(f"DELETE FROM ddz_meta WHERE k = {esc(k)};")
            lines.append(f"INSERT INTO ddz_meta (k, v) VALUES ({esc(k)}, {esc(json.dumps(v, ensure_ascii=False))});")
    return '\n'.join(lines) + '\n'

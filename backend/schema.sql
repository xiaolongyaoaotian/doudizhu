-- 牌友斗地主 · 数据库表结构（SQLite / MySQL / PostgreSQL 通用）
-- 建表后即可用外部数据库工具查看或注入数据；服务端按行读写。
CREATE TABLE IF NOT EXISTS ddz_users (
  name VARCHAR(64) PRIMARY KEY,          -- 账户名
  salt VARCHAR(32) NOT NULL,             -- 密码盐
  pass_hash VARCHAR(64) NOT NULL,        -- SHA-256(salt::password)
  coins INTEGER DEFAULT 0,               -- 金币余额
  points INTEGER DEFAULT 0,              -- 积分
  games INTEGER DEFAULT 0,               -- 总局数
  wins INTEGER DEFAULT 0,                -- 胜场
  last_checkin VARCHAR(10) DEFAULT '',   -- 最近签到日期 YYYY-MM-DD
  banned INTEGER DEFAULT 0,              -- 封禁标记
  created_at BIGINT DEFAULT 0,           -- 注册时间(ms)
  records_json TEXT,                     -- 对战记录 JSON 数组（服务端保留最近 100 条）
  extras_json TEXT                       -- 其它字段 JSON（订单/交易记录等）
);
CREATE TABLE IF NOT EXISTS ddz_meta (
  k VARCHAR(64) PRIMARY KEY,             -- tokens / rooms / queue 等运行时状态
  v TEXT
);

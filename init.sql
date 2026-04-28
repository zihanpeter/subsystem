-- Subsystem: MySQL schema init (derived from app comments)
-- Target DB: subsystem

CREATE DATABASE IF NOT EXISTS subsystem
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE subsystem;

CREATE TABLE IF NOT EXISTS users (
  username VARCHAR(64),
  password VARCHAR(64),
  timef VARCHAR(64),
  intro TEXT,
  theme VARCHAR(64),
  admin BOOL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lists (
  id VARCHAR(128),
  username VARCHAR(64),
  listname VARCHAR(64),
  difficulty INT,
  en TEXT,
  zh TEXT,
  timef VARCHAR(64),
  o BOOL,
  sm BOOL,
  sen TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS articles (
  id VARCHAR(128),
  username VARCHAR(64),
  title VARCHAR(128),
  content TEXT,
  timef VARCHAR(64),
  top BOOL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Note: `id` here is the article id (iid in code), `commentid` is the comment uuid.
CREATE TABLE IF NOT EXISTS comment (
  id VARCHAR(128),
  commentid VARCHAR(128),
  username VARCHAR(64),
  content TEXT,
  timef VARCHAR(128),
  to1 VARCHAR(64)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS yule (
  name VARCHAR(128),
  hot INT,
  path VARCHAR(256),
  intro VARCHAR(256),
  timef VARCHAR(64),
  creator VARCHAR(128)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

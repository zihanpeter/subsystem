# Subsystem 部署指南（Gunicorn + systemd）

本指南适用于 Ubuntu/Debian 服务器，部署当前项目的 Flask 应用。

## 1. 前置条件

- 服务器已安装 Python 3.10+、systemd
- 项目已放到目标目录（示例：`/opt/subsystem`）

> 说明：当前代码已改为 **只从项目根目录 `.env` 读取配置**，不会再从环境变量读取。

## 2. 创建虚拟环境并安装依赖

在服务器执行：

```bash
cd /opt/subsystem
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install flask gunicorn markdown bleach captcha
```

验证 Gunicorn：

```bash
.venv/bin/python -m gunicorn --version
```

## 3. 配置项目根目录 `.env`

在 `/opt/subsystem/.env` 写入：

```bash
SECRET_KEY=replace_with_a_strong_secret
```

建议权限收紧：

```bash
chmod 600 /opt/subsystem/.env
```

## 4. 数据存储（SQLite）

数据存在项目根目录下的 `cache/subsystem.db`（路径写在 `lib/dbConnecter.py` 的 `DB_PATH`）。

- 首次启动时会自动创建 `cache/` 目录和所有表，不需要手动建表。
- 建表语句集中在 `lib/dbConnecter.py` 的 `SCHEMA` 里。
- `cache/` 已加入 `.gitignore`，里面有用户密码，不要提交到仓库。

SQLite 需要在 `cache/` 目录里创建 `-wal`/`-shm` 临时文件，所以运行服务的用户（下面 systemd 里是 `www-data`）必须对**整个目录**有写权限：

```bash
sudo mkdir -p /opt/subsystem/cache
sudo chown -R www-data:www-data /opt/subsystem/cache
```

### 4.1 从旧的 MySQL 迁移数据（只需执行一次）

迁移脚本 `scripts/migrate_mysql_to_sqlite.py` 只读 MySQL，不会改动原数据；先写临时文件，逐表核对行数一致后才落到 `cache/subsystem.db`。

在服务器上（MySQL 所在机器）执行：

```bash
cd /opt/subsystem
sudo systemctl stop subsystem                       # 停服务, 避免迁移期间有新写入丢失
.venv/bin/python -m pip install mysql-connector-python   # 旧环境里一般已经有了
.venv/bin/python scripts/migrate_mysql_to_sqlite.py     # 默认 root@localhost/subsystem, 密码读 .env 的 MYSQL_PASSWORD
sudo chown -R www-data:www-data cache
sudo systemctl start subsystem
```

常用参数：

- `--user` / `--password` / `--database` / `--host` / `--port`：MySQL 连接信息。`.env` 里没有 `MYSQL_PASSWORD` 又没传 `--password` 时会交互输入。
- `--output`：SQLite 文件路径，默认 `cache/subsystem.db`。
- `--force`：目标文件已存在时覆盖，原文件会先改名为 `subsystem.db.bak`。

想在本地拿到一份数据，可以用 SSH 隧道连服务器上的 MySQL：

```bash
ssh -N -L 3307:127.0.0.1:3306 user@your-server      # 另开一个终端保持运行
python scripts/migrate_mysql_to_sqlite.py --port 3307 --password '你的MySQL密码'
```

也可以直接把服务器上迁好的 `cache/subsystem.db` 用 `scp` 拷下来（先停服务，或用 `sqlite3 cache/subsystem.db ".backup /tmp/subsystem.db"` 导出一份一致的副本）。

确认网站运行正常后，`.env` 里的 `MYSQL_PASSWORD` 和服务器上的 MySQL 就可以不要了。

## 5. 配置 systemd 服务

创建 `/etc/systemd/system/subsystem.service`：

```ini
[Unit]
Description=Subsystem Flask app via Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/subsystem
ExecStart=/opt/subsystem/.venv/bin/python -m gunicorn -w 2 -b 0.0.0.0:5050 main_app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

加载并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now subsystem
sudo systemctl status subsystem --no-pager -l
```

## 6. 健康检查

本机测试：

```bash
curl -i http://127.0.0.1:5050/
```

如果返回 `200` 或正常 HTML，说明应用已启动。

## 7. 常用运维命令

```bash
sudo systemctl restart subsystem
sudo systemctl stop subsystem
sudo systemctl status subsystem --no-pager -l
sudo journalctl -u subsystem -f
sudo journalctl -u subsystem -n 200 --no-pager
```

备份数据库（服务运行中也可以执行）：

```bash
sqlite3 /opt/subsystem/cache/subsystem.db ".backup /opt/subsystem/cache/backup-$(date +%F).db"
```

## 8. 常见问题排查

### 8.1 `No module named gunicorn`

原因：虚拟环境未安装 gunicorn。

```bash
cd /opt/subsystem
.venv/bin/python -m pip install gunicorn
```

### 8.2 `unable to open database file` / `attempt to write a readonly database`

原因：运行服务的用户对 `cache/` 目录或其中的文件没有写权限（迁移脚本用 root/sudo 跑过之后最常见）。

```bash
sudo chown -R www-data:www-data /opt/subsystem/cache
```

### 8.3 `curl 127.0.0.1:5050` 连接被拒绝

说明服务未监听端口，先看状态和日志：

```bash
sudo systemctl status subsystem --no-pager -l
sudo journalctl -u subsystem -n 200 --no-pager
```

## 9. 可选：Nginx 反向代理

生产环境建议让 Gunicorn 监听 `127.0.0.1:5050`，再由 Nginx 对外提供 80/443。
如需我补充 Nginx 配置模板，可直接加一节。

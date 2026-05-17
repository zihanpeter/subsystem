# Subsystem 部署指南（Gunicorn + systemd）

本指南适用于 Ubuntu/Debian 服务器，部署当前项目的 Flask 应用。

## 1. 前置条件

- 服务器已安装 Python 3.10+、MySQL、systemd
- 项目已放到目标目录（示例：`/opt/subsystem`）
- MySQL 中已创建数据库：`subsystem`

> 说明：当前代码已改为 **只从项目根目录 `.env` 读取配置**，不会再从环境变量读取。

## 2. 创建虚拟环境并安装依赖

在服务器执行：

```bash
cd /opt/subsystem
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install flask gunicorn markdown bleach mysql-connector-python
```

验证 Gunicorn：

```bash
.venv/bin/python -m gunicorn --version
```

## 3. 配置项目根目录 `.env`

在 `/opt/subsystem/.env` 写入：

```bash
SECRET_KEY=replace_with_a_strong_secret
MYSQL_PASSWORD=replace_with_mysql_password
```

建议权限收紧：

```bash
chmod 600 /opt/subsystem/.env
```

## 4. 准备 MySQL

代码当前连接配置在 `lib/dbConnecter.py` 中：

- host: `localhost`
- user: `root`
- database: `subsystem`
- password: 从 `.env` 中 `MYSQL_PASSWORD` 读取

请确认 `root@localhost` 可用该密码登录，且有 `subsystem` 库权限。

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

## 8. 常见问题排查

### 8.1 `No module named gunicorn`

原因：虚拟环境未安装 gunicorn。

```bash
cd /opt/subsystem
.venv/bin/python -m pip install gunicorn
```

### 8.2 `Access denied for user 'root'@'localhost'`

原因：`.env` 中 `MYSQL_PASSWORD` 与 MySQL 实际密码不一致。

排查：

```bash
cd /opt/subsystem
.venv/bin/python - <<'PY'
import mysql.connector
from lib.config_loader import get_config
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=get_config("MYSQL_PASSWORD"),
    database="subsystem",
)
print("connected ok")
conn.close()
PY
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

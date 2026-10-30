#!/usr/bin/env bash
# 在新服务器 (Ubuntu/Debian) 上一键安装环境、恢复数据、注册 systemd 服务:
#   sudo git clone https://github.com/zihanpeter/subsystem.git /opt/subsystem
#   sudo bash /opt/subsystem/scripts/setup_server.sh /tmp/subsystem-backup-xxx.tar.gz
#
# 不带备份包时按全新站点部署 (空数据库, 自动生成 SECRET_KEY).
# 可选环境变量:
#   BIND=127.0.0.1:5050   gunicorn 监听地址, 要和 Cloudflare Tunnel 里配置的服务地址一致
#   WORKERS=2             gunicorn worker 数
#   RUN_USER=www-data     运行服务的用户
#   FORCE=1               新服务器上已经有数据库时, 允许用备份包覆盖 (原文件会改名为 .bak)
set -euo pipefail

BACKUP="${1:-}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE=subsystem
BIND="${BIND:-127.0.0.1:5050}"
WORKERS="${WORKERS:-2}"
RUN_USER="${RUN_USER:-www-data}"
FORCE="${FORCE:-0}"
DB="$APP_DIR/cache/subsystem.db"

[ "$(id -u)" = 0 ] || { echo "请用 sudo 运行"; exit 1; }
if [ -n "$BACKUP" ]; then
    [ -f "$BACKUP" ] || { echo "找不到备份包 $BACKUP"; exit 1; }
    BACKUP="$(cd "$(dirname "$BACKUP")" && pwd)/$(basename "$BACKUP")"
    if [ -f "$DB" ] && [ "$FORCE" != 1 ]; then
        echo "$DB 已存在. 确认要用备份包覆盖的话: sudo FORCE=1 bash $0 $BACKUP"
        exit 1
    fi
fi

echo "==> 安装系统依赖"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv git sqlite3 curl
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' \
    || { echo "需要 Python 3.10+, 当前是 $(python3 --version)"; exit 1; }

echo "==> 创建虚拟环境并安装依赖"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install -U pip
"$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

mkdir -p "$APP_DIR/cache"
if systemctl is-active --quiet "$SERVICE"; then # 换数据库前先停, 免得进程还拿着旧文件
    systemctl stop "$SERVICE"
fi

if [ -n "$BACKUP" ]; then
    echo "==> 从备份包恢复数据"
    WORK="$(mktemp -d)"
    trap 'rm -rf "$WORK"' EXIT
    tar xzf "$BACKUP" -C "$WORK"
    for f in subsystem.db manifest.tsv .env; do
        [ -f "$WORK/$f" ] || { echo "备份包里缺少 $f"; exit 1; }
    done

    "$APP_DIR/.venv/bin/python" - "$WORK/subsystem.db" "$WORK/manifest.tsv" <<'PY'
import sqlite3
import sys

db_path, manifest_path = sys.argv[1:]
conn = sqlite3.connect(db_path)
result = conn.execute('PRAGMA integrity_check;').fetchone()[0]
if result != 'ok':
    sys.exit('数据库完整性检查失败: %s' % result)
bad = False
with open(manifest_path, encoding='utf-8') as f:
    for line in f:
        table, expected = line.rstrip('\n').rsplit('\t', 1)
        actual = conn.execute('SELECT COUNT(*) FROM "%s";' % table.replace('"', '""')).fetchone()[0]
        flag = '' if actual == int(expected) else '  <-- 和旧服务器不一致'
        bad = bad or flag != ''
        print('   %-20s %d 行%s' % (table, actual, flag))
conn.close()
if bad:
    sys.exit('行数对不上, 停止恢复')
PY

    if [ -f "$DB" ]; then
        mv "$DB" "$DB.bak"
        echo "   原来的数据库已改名为 $DB.bak"
    fi
    rm -f "$DB-wal" "$DB-shm" # 旧库残留的 WAL 文件会被套到新库上, 必须清掉
    cp "$WORK/subsystem.db" "$DB"

    if [ -f "$APP_DIR/.env" ] && ! cmp -s "$WORK/.env" "$APP_DIR/.env"; then
        mv "$APP_DIR/.env" "$APP_DIR/.env.bak"
        echo "   原来的 .env 已改名为 .env.bak"
    fi
    cp "$WORK/.env" "$APP_DIR/.env" # 沿用旧的 SECRET_KEY, 用户不会被强制登出
elif [ ! -f "$APP_DIR/.env" ]; then
    echo "==> 没有备份包, 生成新的 .env"
    printf 'SECRET_KEY=%s\n' "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > "$APP_DIR/.env"
fi

# 服务用户要能读 .env, 并且能在 cache/ 里创建 -wal/-shm 文件
chown "$RUN_USER:$RUN_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
chown -R "$RUN_USER:$RUN_USER" "$APP_DIR/cache"
chmod 700 "$APP_DIR/cache"

echo "==> 配置 systemd 服务"
cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=Subsystem Flask app via Gunicorn
After=network.target

[Service]
User=$RUN_USER
Group=$RUN_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -m gunicorn -w $WORKERS -b $BIND main_app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo "==> 健康检查 http://$BIND/"
for _ in $(seq 1 15); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://$BIND/")" = 200 ]; then
        echo
        echo "完成, 服务已在 $BIND 上运行"
        exit 0
    fi
    sleep 1
done
echo "服务没有正常响应, 查看日志: journalctl -u $SERVICE -n 100 --no-pager"
exit 1

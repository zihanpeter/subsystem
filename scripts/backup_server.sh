#!/usr/bin/env bash
# 在旧服务器上执行, 把数据库和 .env 打成一个包, 交给新服务器上的 setup_server.sh 恢复:
#   sudo systemctl stop subsystem          # 先停服务, 否则备份之后的新数据带不走
#   sudo bash scripts/backup_server.sh [项目目录, 默认 /opt/subsystem]
set -euo pipefail

APP_DIR="${1:-/opt/subsystem}"
DB="$APP_DIR/cache/subsystem.db"
[ -f "$DB" ] || { echo "找不到 $DB"; exit 1; }
[ -f "$APP_DIR/.env" ] || { echo "找不到 $APP_DIR/.env"; exit 1; }

PY="$APP_DIR/.venv/bin/python"
[ -x "$PY" ] || PY=python3

if systemctl is-active --quiet subsystem 2>/dev/null; then
    echo "[警告] subsystem 服务还在运行, 备份之后产生的新数据不会被带走"
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
OUT="/tmp/subsystem-backup-$(date +%Y%m%d-%H%M%S).tar.gz"

echo "==> 备份数据库"
"$PY" - "$DB" "$WORK/subsystem.db" "$WORK/manifest.tsv" <<'PY'
import sqlite3
import sys

src_path, dst_path, manifest_path = sys.argv[1:]
src = sqlite3.connect(src_path)
dst = sqlite3.connect(dst_path)
src.backup(dst) # 在线备份, WAL 里还没合并进主文件的数据也会带上
src.close()
dst.execute('PRAGMA journal_mode = DELETE;') # 落成单个文件
result = dst.execute('PRAGMA integrity_check;').fetchone()[0]
if result != 'ok':
    sys.exit('数据库完整性检查失败: %s' % result)
tables = [r[0] for r in dst.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;")]
with open(manifest_path, 'w', encoding='utf-8') as f:
    for t in tables:
        n = dst.execute('SELECT COUNT(*) FROM "%s";' % t.replace('"', '""')).fetchone()[0]
        f.write('%s\t%d\n' % (t, n))
        print('   %-20s %d 行' % (t, n))
dst.close()
PY

cp "$APP_DIR/.env" "$WORK/.env"
# 旧环境的依赖版本, 新服务器上出现版本兼容问题时可以对照
"$PY" -m pip freeze > "$WORK/old-pip-freeze.txt" 2>/dev/null || true
if COMMIT="$(git -C "$APP_DIR" rev-parse HEAD 2>/dev/null)"; then
    echo "$COMMIT" > "$WORK/old-git-commit.txt"
fi

(umask 077 && tar czf "$OUT" -C "$WORK" .) # 包里有密码和 SECRET_KEY, 只允许自己读
if [ -n "${SUDO_USER:-}" ]; then # 用 sudo 跑的, 交还给登录用户, 不然 scp 读不了
    chown "$SUDO_USER" "$OUT"
fi

echo
echo "完成: $OUT"
echo "传到新服务器, 例如在你自己电脑上执行:"
echo "  scp -3 旧服务器:$OUT 新服务器:/tmp/"

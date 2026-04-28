# Cloudflare Tunnel 部署说明（Ubuntu）

本说明用于在 Ubuntu 服务器部署本项目，通过 Cloudflare Tunnel 对外提供访问。

## 1. 安装依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
```

安装 cloudflared（官方仓库方式）：

```bash
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update
sudo apt install -y cloudflared
```

## 2. 准备项目

```bash
cd /path/to/subsystem
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

然后安装你项目所需依赖（按你的实际依赖安装）。

准备密钥文件：

- `secrets/flask_secret_key.txt`
- `secrets/mysql_password.txt`
- `secrets/cloudflared_token.txt`

## 3. 首次创建 Tunnel（一次即可）

```bash
cloudflared tunnel login
cloudflared tunnel create subsystem
cloudflared tunnel route dns subsystem app.your-domain.com
cloudflared tunnel token subsystem
```

将最后输出的 token 写入 `secrets/cloudflared_token.txt`。

## 4. 脚本方式启动（快速验证）

先给脚本执行权限：

```bash
chmod +x deploy/start_all.sh deploy/start_tunnel.sh
```

然后启动：

```bash
source .venv/bin/activate
./deploy/start_all.sh
```

这会先启动本地 Flask（`127.0.0.1:5050`），再启动 tunnel。

## 5. systemd 方式（生产推荐）

1) 准备 cloudflared 环境变量文件（存 token）：

`secrets/cloudflared.env`

```ini
TUNNEL_TOKEN=your_token_here
```

2) 基于模板生成服务文件并修改占位符：

- `deploy/systemd/subsystem-flask.service.example`
- `deploy/systemd/subsystem-cloudflared.service.example`

3) 复制到 systemd：

```bash
sudo cp deploy/systemd/subsystem-flask.service.example /etc/systemd/system/subsystem-flask.service
sudo cp deploy/systemd/subsystem-cloudflared.service.example /etc/systemd/system/subsystem-cloudflared.service
sudo systemctl daemon-reload
sudo systemctl enable --now subsystem-flask.service
sudo systemctl enable --now subsystem-cloudflared.service
```

4) 查看状态和日志：

```bash
sudo systemctl status subsystem-flask.service
sudo systemctl status subsystem-cloudflared.service
journalctl -u subsystem-flask.service -f
journalctl -u subsystem-cloudflared.service -f
```

## 6. 常见问题

- 域名访问 502：先检查 `127.0.0.1:5050` 是否已在监听
- cloudflared 启动失败：检查 token 是否正确、是否有 DNS 记录
- 数据库连接失败：检查 `secrets/mysql_password.txt` 和 MySQL 权限

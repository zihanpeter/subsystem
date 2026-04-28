# Ubuntu Docker 部署（Cloudflare Tunnel）

本方案使用 3 个容器：

- `app`: Flask/Gunicorn
- `mysql`: MySQL 8
- `cloudflared`: Cloudflare Tunnel

## 1) 安装 Docker

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

## 2) 准备密钥文件

在项目根目录创建以下文件：

- `secrets/flask_secret_key.txt`
- `secrets/mysql_password.txt`
- `secrets/cloudflared.env`

`secrets/cloudflared.env` 内容示例：

```ini
TUNNEL_TOKEN=your_cloudflare_tunnel_token
```

可选文件（不填则使用默认值）：

- `secrets/mysql_host.txt`（默认：容器内 `mysql`，非容器 `localhost`）
- `secrets/mysql_user.txt`（默认：`root`）
- `secrets/mysql_database.txt`（默认：`subsystem`）

## 3) 首次创建 Tunnel（一次即可）

在任意一台已登录 Cloudflare 的机器执行：

```bash
cloudflared tunnel login
cloudflared tunnel create subsystem
cloudflared tunnel route dns subsystem app.your-domain.com
cloudflared tunnel token subsystem
```

把最后输出 token 写入 `secrets/cloudflared.env` 的 `TUNNEL_TOKEN`。

## 4) 启动

```bash
cd /path/to/subsystem
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f cloudflared
```

## 5) 停止/重启

```bash
docker compose down
docker compose up -d
```

## 6) 说明

- MySQL 数据保存在 `mysql_data` volume，不会因容器重建丢失
- `init.sql` 仅在数据库首次初始化时执行
- 若你使用外部 MySQL，请在 `docker-compose.yml` 中移除 `mysql` 服务，并在 `secrets/mysql_host.txt` 写入外部地址

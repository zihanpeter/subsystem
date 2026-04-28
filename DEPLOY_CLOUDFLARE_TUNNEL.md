# Cloudflare Tunnel 部署说明（Windows）

本项目改为通过 Cloudflare Tunnel 暴露服务，不再要求服务器有公网 IP 或开放入站端口。

## 1. 前置条件

- 已安装 Python（可运行 `python` 命令）
- 已安装并可运行 `cloudflared`
- 已有 Cloudflare 账号和可管理的域名
- 已配置项目密钥文件：
  - `secrets/flask_secret_key.txt`
  - `secrets/mysql_password.txt`

## 2. 首次创建 Tunnel（一次即可）

在 PowerShell 中执行：

```powershell
cloudflared tunnel login
cloudflared tunnel create subsystem
cloudflared tunnel route dns subsystem app.your-domain.com
cloudflared tunnel token subsystem
```

最后一条命令会输出 token，把它保存到：

`secrets/cloudflared_token.txt`

> 该文件已被 `.gitignore` 忽略，不会进入 git。

## 3. 启动服务

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\start_all.ps1
```

这个脚本会：

1. 启动本地 Flask 服务（`127.0.0.1:5050`）
2. 启动 Cloudflare Tunnel，并将域名请求转发到本地服务

按 `Ctrl + C` 停止 tunnel 时，脚本会自动关闭本地 Flask 进程。

## 4. 仅启动 Tunnel（可选）

如果你已经单独启动了本地服务，可以只跑 tunnel：

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\start_tunnel.ps1
```

## 5. 命名 Tunnel 配置文件方式（可选）

如果你更想用 `config.yml` 而不是 token，可参考：

- 模板：`deploy/cloudflared/config.yml.example`

然后执行（示例）：

```powershell
cloudflared tunnel --config .\deploy\cloudflared\config.yml run
```

## 6. 常见问题

- `cloudflared not found`：先安装 cloudflared 并确认已加入 PATH
- `Token file not found`：创建 `secrets/cloudflared_token.txt`
- 访问域名 502：确认本地服务已监听 `127.0.0.1:5050`

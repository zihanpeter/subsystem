# Secret Files

Create these files before running the app:

- `secrets/flask_secret_key.txt`
- `secrets/mysql_password.txt`
- `secrets/cloudflared.env` (for Docker + tunnel)

Each file should contain only the corresponding secret value.

Optional files:

- `secrets/mysql_host.txt`
- `secrets/mysql_user.txt`
- `secrets/mysql_database.txt`

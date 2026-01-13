# 服务器从 GitHub 更新代码（SSH）

目标：服务器端从 `git@github.com:suchenyang0910-glitch/greensphere.git` 拉取最新代码并重启服务（Docker Compose）。

## 前置条件（服务器）
- Linux 服务器（Ubuntu/Debian/CentOS 均可）
- 已安装：`git`、`docker`、`docker compose`
- 已开放：80/443（反代/HTTPS），以及 8000（如直连调试）

## 1) 配置 GitHub SSH（推荐 Deploy Key）
在服务器生成 SSH Key：
- `ssh-keygen -t ed25519 -C "greensphere-deploy" -f ~/.ssh/greensphere_deploy -N ""`

写入 SSH 配置（让 git 自动使用该 key）：
- `cat >> ~/.ssh/config <<'EOF'\nHost github.com\n  IdentityFile ~/.ssh/greensphere_deploy\n  IdentitiesOnly yes\nEOF`

添加 known_hosts（避免首次交互）：
- `ssh-keyscan -t rsa,ed25519 github.com >> ~/.ssh/known_hosts`

把公钥内容复制到 GitHub 仓库的 Deploy Keys（Read-only）：
- `cat ~/.ssh/greensphere_deploy.pub`

验证连通性（预期显示成功信息）：
- `ssh -T git@github.com`

## 2) 首次部署（clone + 配置 + 启动）
建议目录：`/opt/greensphere`
- `sudo mkdir -p /opt/greensphere && sudo chown -R $USER:$USER /opt/greensphere`
- `cd /opt/greensphere`
- `git clone git@github.com:suchenyang0910-glitch/greensphere.git .`
- `cp .env.example .env` 并填好 token、admin key、webapp url 等
- `docker compose up -d --build`

## 3) 日常更新（pull + 重启）
方式 A：手动更新
- `cd /opt/greensphere`
- `git fetch --prune origin`
- `git checkout main`
- `git reset --hard origin/main`
- `docker compose up -d --build`

方式 B：用仓库脚本（推荐）
- `cd /opt/greensphere`
- `bash scripts/server_update.sh`

可选：指定分支或目录
- `APP_DIR=/opt/greensphere BRANCH=main bash scripts/server_update.sh`

## 注意事项
- `.env` 不要提交到仓库；更新时脚本会保留你的 `.env`
- SQLite DB（`greensphere_behavior.db`）建议持久化到磁盘，并在 compose 里做 volume 映射
- 生产建议开启：`GS_REQUIRE_TG_INIT_DATA=1`，避免接口被伪造请求刷数据


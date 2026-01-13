# 菜鸟一键部署（Ubuntu）

适用场景：一台全新 Ubuntu 服务器（root 或有 sudo 权限），希望“一条命令”完成 Docker 安装、拉取仓库、启动服务。

## 方式 A：已能 clone 仓库（推荐）
```bash
cd ~/greensphere
bash scripts/one_click_deploy_ubuntu.sh
```

## 方式 B：服务器还没有代码（真正一键）
```bash
APP_DIR=/opt/greensphere REPO_SSH=git@github.com:suchenyang0910-glitch/greensphere.git BRANCH=main \
bash -c "$(curl -fsSL https://raw.githubusercontent.com/suchenyang0910-glitch/greensphere/main/scripts/one_click_deploy_ubuntu.sh)"
```

说明：
- 如果仓库是私有的，raw URL 可能无法访问；此时请使用方式 A。

## 部署完成后必须做的事
第一次运行会自动生成 `.env`，你需要编辑并填写：
- `TG_COMMUNITY_BOT_TOKEN`
- `TG_MONITOR_BOT_TOKEN`、`TG_MONITOR_CHAT_ID`
- `ADMIN_API_KEY`
- `GS_API_BASE_URL=https://greensphere.earth`（生产）
- `GS_WEBAPP_URL=https://greensphere.earth/app`（生产）
- `GS_REQUIRE_TG_INIT_DATA=1`（生产建议开启）

然后执行：
```bash
cd /opt/greensphere
docker compose up -d --build
```


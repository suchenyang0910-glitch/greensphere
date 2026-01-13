# 部署指南（V1）

## 上线必备清单
- 一个可访问的域名（建议：`app.greensphere.world`）
- HTTPS 证书（Telegram WebApp 必须是 HTTPS；使用 Cloudflare 也可以满足）
- 服务器：1C2G 起步即可（初期足够）
- Telegram BotFather 配置：
  - Community Bot：设置 Web App URL（指向 `https://你的域名/app`）
  - 可选：设置命令 `/start` `/help`

## 域名使用 Cloudflare（推荐配置）
### 1) DNS 解析
- 在 Cloudflare DNS 添加记录（例：`app.greensphere.world`）
  - 类型：A（或 AAAA）
  - 内容：你的服务器公网 IP
  - Proxy status：开启（橙云）

### 2) SSL/TLS（强烈建议 Full (strict)）
- SSL/TLS 模式：`Full (strict)`
- Origin 证书（两种方式任选其一）：
  - 方式 A：在服务器用 Caddy / Nginx + Let's Encrypt 直接签发（最省心）
  - 方式 B：在 Cloudflare 生成 Origin Certificate，部署到服务器（更可控）

说明：
- Telegram WebApp 只要求“对用户是 HTTPS”，Cloudflare 橙云可以提供边缘 HTTPS；但为了避免回源被劫持/降级，仍建议 Full (strict)。

### 3) 缓存与安全规则（避免把 API 缓存了）
- 建议设置 Cache Rules / Page Rules：
  - `/api/*`：Cache = Bypass
  - `/admin*`：Cache = Bypass
  - `/app*`：Cache = Bypass（WebApp HTML 也建议不缓存，避免灰度/更新问题）
- WAF/安全：
  - 开启 Bot Fight Mode（如可用）
  - 开启 Rate Limiting（如可用），重点保护 `/api/init_user` `/api/complete` `/api/admin/*`
  - 只允许你的国家/地区（可选，视业务覆盖而定）

## 推荐部署方式：Docker Compose

### 1) 准备环境变量
复制 `.env.example` 为 `.env`，按需填写：
- `TG_COMMUNITY_BOT_TOKEN`
- `TG_MONITOR_BOT_TOKEN`、`TG_MONITOR_CHAT_ID`
- `ADMIN_API_KEY`（生产环境必须配置）
- `GS_WEBAPP_URL`（生产：`https://你的域名/app`）
- `GS_REQUIRE_TG_INIT_DATA=1`（生产建议开启）

### 2) 启动服务
在服务器上执行：
- `docker compose up -d --build`

服务说明：
- `api`：后端 + 官网 + WebApp + Admin
- `community_bot`：对外引导 Bot（轮询方式）
- `monitor_bot`：对内监控 Bot（轮询方式）

### 3) 反向代理与 HTTPS
建议用 Caddy 或 Nginx 做 TLS 终端，并反代到 `api:8000`。
- 反代路径：`/` → `http://127.0.0.1:8000`

关键要求：
- WebApp URL 必须是 HTTPS
- 需要放通 80/443

## 生产安全建议
- `ADMIN_API_KEY` 必须设置
- `GS_REQUIRE_TG_INIT_DATA=1` 强制校验 Telegram initData，避免伪造 user_id
- 服务器层做基础防护：限制异常流量、开启 WAF/Cloudflare（如可用）

## 服务器从 GitHub 更新
参考：[server_update_from_github.md](file:///d:/VScode/GreenSphere/greensphere/docs/server_update_from_github.md)

## 菜鸟一键部署
参考：[one_click_deploy.md](file:///d:/VScode/GreenSphere/greensphere/docs/one_click_deploy.md)


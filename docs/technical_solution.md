# GreenSphere 技术方案（V1）

## 目标
- 在 Telegram 内完成低门槛打卡（WebApp）与引导（Bot）
- 支持任务、积分（G-Points）、连续天数（Streak）、徽章（LeafPass）与个人档案
- 提供管理后台与监控Bot，覆盖注册、打卡、徽章解锁与基础数据看板
- 严格避免金融化：无Token、无交易、无碳交易/理财

## 系统组成
- 官网（Landing）
  - 入口：`GET /`（模板渲染）
  - 目标：品牌叙事、引导加入频道/社群、引导打开 WebApp
- Telegram WebApp（主交互）
  - 入口：`GET /app`
  - 目标：任务打卡、积分/连续天数、徽章展示
- 官方对外 Bot：@GreenSphereCommunity_Bot
  - 入口：`/start`
  - 目标：打开 WebApp、引导加入频道/社群
- 对内监控 Bot：@GreenSphereMonitor_Bot
  - 入口：`/stats`、`/logs`
  - 目标：拉取后端统计与日志；后端事件触发式推送到监控群组
- 管理后台（Admin Console）
  - 入口：`GET /admin`
  - 目标：查看今日数据、用户列表、任务配置、徽章列表、系统日志

## 后端服务
- 技术栈：Python + FastAPI
- 数据库：SQLite（行为层专用 `greensphere_behavior.db`，V1）+ SQLAlchemy（扩展表，如 waitlist）
- 服务端入口：`app/main.py`（根目录 `main.py` 兼容导出）

## 关键数据模型（行为层 SQLite）
- users：用户（telegram_id 为主键）
- tasks：任务配置（title/points）
- user_task_logs：打卡日志（去重规则：同用户同任务同日只计一次）
- badges：徽章定义（rule_type/threshold）
- user_badges：徽章解锁记录（唯一：user_id + badge_code）
- system_logs：系统事件（注册、打卡、重复、徽章解锁等）

## 关键 API（V1）
- WebApp
  - `POST /api/init_user`
  - `GET /api/tasks`
  - `POST /api/complete`
- Admin（Header：`X-Admin-Key`，当 `ADMIN_API_KEY` 配置时启用）
  - `GET /api/admin/daily-stats`
  - `GET /api/admin/users`
  - `GET /api/admin/tasks`、`POST/PUT/DELETE /api/admin/tasks/*`
  - `GET /api/admin/badges`
  - `GET /api/admin/logs`

## 事件与监控
- 后端写入 system_logs
- 触发 Telegram 推送（若配置）：
  - 新用户注册 → 监控群组
  - 徽章解锁 → 用户私聊 + 监控群组

## 配置
参考 `.env.example`

## 多语言（官网 & Telegram WebApp）
- 语言规则：中文（zh）、泰文（th）、高棉文/柬埔寨（km/kh）、越南语（vi），其它默认英语（en）
- 官网：前端基于浏览器语言自动切换
- Telegram WebApp：优先使用 Telegram `user.language_code`，并通过请求头 `X-GS-Lang` 传递给后端以返回对应任务文案

## 安全与防刷（V1）
- Admin API：支持 `X-Admin-Key`（配置 `ADMIN_API_KEY` 后启用）
- Telegram WebApp 鉴权：支持 `X-Telegram-Init-Data` 验签与身份提取；可通过 `GS_REQUIRE_TG_INIT_DATA=1` 强制开启
- 频控：基于 SQLite `rate_limits` 表对关键接口做 IP/用户限流（返回 429）
- 去重：`user_task_logs` 增加唯一索引，防止并发重复写入


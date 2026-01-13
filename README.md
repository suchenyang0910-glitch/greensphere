# GreenSphere · Small Actions. Real Impact.

GreenSphere 是一个围绕「日常绿色行为」的轻量打卡系统，通过每日任务、G-Points 积分和 LeafPass 徽章，帮助用户养成可持续生活习惯。  
本仓库包含：

- FastAPI 后端（行为打卡 + 统计 + Admin API）
- Telegram WebApp 前端（`https://app.greensphere.world/`）
- 官网（生产建议）：`https://greensphere.earth/`
- Telegram Bots
  - 社区 Bot：`@GreenSphereCommunity_Bot`
  - 监控 Bot：读取每日行为数据

---

## 1. 项目结构（服务器 / 本地）

```text
/opt/greensphere
├─ app/                    # 主应用（FastAPI, models, api routers 等）
├─ routes.py               # 行为打卡相关路由（/api/init_user, /api/tasks, /api/complete, /api/admin/daily-stats）
├─ gs_db.py                # 行为层 SQLite（greensphere_behavior.db）的初始化 & get_db
├─ models.py               # Pydantic 模型 & 统计函数（calculate_stats 等）
├─ telegram_utils.py       # 给用户发送打卡成功消息的工具函数
├─ bot.py                  # 社区 Bot（@GreenSphereCommunity_Bot）
├─ monitor_bot.py          # 监控 Bot（读取 /api/admin/daily-stats）
├─ templates/
│   └─ index.html          # Telegram WebApp 前端页面
├─ static/
│   ├─ style.css           # WebApp 样式
│   └─ og-greensphere.png  # 分享图（可选）
├─ robots.txt
├─ sitemap.xml
├─ requirements.txt        # Python 依赖列表（可选）
└─ README.md

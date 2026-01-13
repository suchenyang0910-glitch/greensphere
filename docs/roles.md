# 角色分工（V1）

## 产品经理（PM）
- 定义任务体系（任务库、频次、难度梯度、积分策略）
- 定义徽章体系（规则、阈值、文案、解锁节奏）
- 定义关键指标（D7/D30、周完成次数、平均Streak、回归率）
- 设计管理后台需求与监控事件规范

## UI 设计师（UI/UX）
- 官网：大气、科技感、主题绿色（Hero、价值点、CTA、社群入口）
- Telegram WebApp：移动端优先（任务列表、统计卡片、徽章墙、toast）
- 管理后台：暗色科技风（KPI、表格、操作区）
- 监控 Bot：信息结构与消息模板（注册、异常、汇总）

## 前端工程师（Web）
- Telegram WebApp（templates/index.html + static/style.css）交互与体验优化
- 官网页面与多语言/SEO（templates/home.html、site_base.html）
- 管理后台（templates/admin.html + static/admin.css）与 API 对接

## 后端工程师（API）
- FastAPI 路由与 DB 初始化（app/main.py、routes.py、gs_db.py）
- 行为层 API：任务、积分、连续天数、徽章解锁
- Admin API：统计、用户、任务、徽章、日志
- 事件与推送：监控群组与用户通知（telegram_utils.py）

## 测试（QA）
- 用例：注册、重复打卡、跨天Streak、徽章阈值、Admin鉴权
- 可靠性：网络失败不影响主流程（推送失败容错）
- 安全：Admin API Key 校验；敏感配置不落库不输出

## 运营（Ops）
- 频道：内容排期、增长活动、用户教育（怎么打卡/徽章意义）
- 社群：Pioneer挑战、任务主题周、UGC与引导分享档案页
- 监控：关注异常增长、重复请求、用户反馈与bug回收


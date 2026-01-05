# site_i18n.py
from dataclasses import dataclass
from typing import Dict

SUPPORTED_LANGS = ["zh", "en", "th", "vi", "km"]  # km = Khmer（柬埔寨）

@dataclass
class HomeText:
    lang: str
    title: str
    subtitle: str
    cta_use_bot: str
    cta_pioneer: str
    section_how_title: str
    section_how_steps: list
    section_why_title: str
    section_why_points: list
    section_for_title: str
    section_for_items: list
    footer_slogan: str

TEXTS: Dict[str, HomeText] = {}

# 简体中文
TEXTS["zh"] = HomeText(
    lang="zh",
    title="用日常小行动，积累真实的绿色影响力",
    subtitle="GreenSphere 通过每日任务、积分和 GreenSphere 徽章，帮你把绿色生活变成一种可以坚持的习惯。",
    cta_use_bot="在 Telegram 中开始打卡",
    cta_pioneer="了解 7 天 Pioneer 挑战",
    section_how_title="怎么使用 GreenSphere？",
    section_how_steps=[
        "在 Telegram 搜索 @GreenSphereCommunity_Bot，发送 /start。",
        "点击「打开 GreenSphere 小程序」，进入每日任务页面。",
        "每天完成 1–3 个绿色小行动，点一下「完成」就会记入积分和连续天数。",
    ],
    section_why_title="为什么是 GreenSphere？",
    section_why_points=[
        "足够简单：不用设备、不用上传证明，只需自我声明。",
        "有反馈：G-Points 积分 + 连续天数 + GreenSphere 徽章，看到自己的改变。",
        "可长期坚持：任务设计轻量，不制造额外焦虑和负担。",
    ],
    section_for_title="谁适合使用？",
    section_for_items=[
        "想开始更环保生活，但不想被复杂工具吓退的个人用户。",
        "喜欢打卡、收集徽章，希望把「做好事」也游戏化的人。",
        "关注 ESG / 可持续，希望体验行为层产品的研究者和从业者。",
    ],
    footer_slogan="Small Actions. Real Impact.",
)

# English (default)
TEXTS["en"] = HomeText(
    lang="en",
    title="Turn small daily actions into real green impact",
    subtitle="GreenSphere helps you build sustainable habits through simple daily quests, G-Points, and GreenSphere badges.",
    cta_use_bot="Start in Telegram",
    cta_pioneer="Join the 7-day Pioneer challenge",
    section_how_title="How does it work?",
    section_how_steps=[
        "Search for @GreenSphereCommunity_Bot in Telegram and send /start.",
        "Tap “Open GreenSphere WebApp” to see your daily green quests.",
        "Every day, complete 1–3 small green actions and tap “Complete” to earn points and build your streak.",
    ],
    section_why_title="Why GreenSphere?",
    section_why_points=[
        "Simple enough: no extra devices, no photo uploads, no complex carbon accounting.",
        "Meaningful feedback: G-Points, streaks, and GreenSphere badges show your real progress.",
        "Built for long-term use: light-weight tasks designed not to create extra anxiety.",
    ],
    section_for_title="Who is it for?",
    section_for_items=[
        "Individuals who care about sustainable living but don’t want heavy, complex tools.",
        "People who like habit tracking and collecting badges, and want “doing good” to feel rewarding.",
        "ESG / sustainability / Web3 explorers who want to experiment on the behavior layer.",
    ],
    footer_slogan="Small Actions. Real Impact.",
)

# Thai
TEXTS["th"] = HomeText(
    lang="th",
    title="เปลี่ยนการกระทำเล็ก ๆ ทุกวัน ให้กลายเป็นพลังสีเขียวที่จับต้องได้",
    subtitle="GreenSphere ช่วยสร้างนิสัยด้านสิ่งแวดล้อมผ่านภารกิจรายวัน คะแนน G-Points และเหรียญ GreenSphere",
    cta_use_bot="เริ่มใช้งานผ่าน Telegram",
    cta_pioneer="เข้าร่วมภารกิจ Pioneer 7 วัน",
    section_how_title="GreenSphere ใช้อย่างไร?",
    section_how_steps=[
        "ค้นหา @GreenSphereCommunity_Bot ใน Telegram และพิมพ์ /start",
        "กด “Open GreenSphere WebApp” เพื่อดูภารกิจสีเขียวประจำวัน",
        "ในแต่ละวัน เลือกทำ 1–3 พฤติกรรมสีเขียว และกด “Complete” เพื่อรับคะแนนและนับสถิติ",
    ],
    section_why_title="ทำไมต้อง GreenSphere?",
    section_why_points=[
        "ใช้งานง่าย: ไม่ต้องใช้อุปกรณ์เพิ่ม ไม่ต้องอัปโหลดรูปหลักฐาน",
        "เห็นผลลัพธ์ชัดเจน: คะแนน G-Points, สถิติการเข้าร่วม และเหรียญ GreenSphere",
        "ออกแบบเพื่อการใช้งานระยะยาว: ภารกิจเบา ๆ ไม่เพิ่มความเครียด",
    ],
    section_for_title="เหมาะกับใคร?",
    section_for_items=[
        "คนที่อยากเริ่มใช้ชีวิตอย่างยั่งยืน แต่ไม่อยากใช้เครื่องมือที่ซับซ้อน",
        "คนที่ชอบระบบ habit tracking และสะสมเหรียญ/Badge",
        "คนทำงานด้าน ESG / Sustainability / Web3 ที่อยากทดลองในมิติพฤติกรรม",
    ],
    footer_slogan="Small Actions. Real Impact.",
)

# Vietnamese
TEXTS["vi"] = HomeText(
    lang="vi",
    title="Biến những hành động nhỏ mỗi ngày thành tác động xanh thực sự",
    subtitle="GreenSphere giúp bạn xây dựng thói quen bền vững qua nhiệm vụ hằng ngày, điểm G-Points và huy hiệu GreenSphere.",
    cta_use_bot="Bắt đầu trên Telegram",
    cta_pioneer="Tham gia thử thách Pioneer 7 ngày",
    section_how_title="GreenSphere hoạt động như thế nào?",
    section_how_steps=[
        "Tìm @GreenSphereCommunity_Bot trên Telegram và gửi /start.",
        "Nhấn “Open GreenSphere WebApp” để xem nhiệm vụ xanh hằng ngày.",
        "Mỗi ngày, hoàn thành 1–3 hành động xanh nhỏ và nhấn “Complete” để nhận điểm và tăng streak.",
    ],
    section_why_title="Tại sao là GreenSphere?",
    section_why_points=[
        "Đơn giản: không cần thiết bị, không cần tải ảnh, không cần tính toán phức tạp.",
        "Phản hồi rõ ràng: điểm G-Points, chuỗi ngày tham gia và huy hiệu GreenSphere.",
        "Thiết kế cho việc sử dụng lâu dài: nhiệm vụ nhẹ nhàng, không gây áp lực.",
    ],
    section_for_title="Dành cho ai?",
    section_for_items=[
        "Những người quan tâm đến lối sống bền vững nhưng không muốn dùng công cụ rườm rà.",
        "Người thích theo dõi thói quen và sưu tầm huy hiệu.",
        "Người làm ESG / Sustainability / Web3 muốn thử nghiệm ở lớp hành vi.",
    ],
    footer_slogan="Small Actions. Real Impact.",
)

# Khmer (Cambodia) – 简化版（中英混合，避免机器翻译质量太差）
TEXTS["km"] = HomeText(
    lang="km",
    title="សកម្មភាព​តូចៗ ជារៀងរាល់ថ្ងៃ → បង្កើតឥទ្ធិពលបៃតងពិតប្រាកដ",
    subtitle="GreenSphere ជួយ​អ្នក​បង្កើត​ទម្លាប់ជីវិតបៃតង តាមរយៈភារកិច្ច​ប្រចាំថ្ងៃ ពិន្ទុ G-Points និង徽章 GreenSphere",
    cta_use_bot="ចាប់ផ្តើមក្នុង Telegram (Start in Telegram)",
    cta_pioneer="ស្គាល់បន្ថែមពីបញ្ហ challenge 7 ថ្ងៃ (7-day Pioneer)",
    section_how_title="របៀបប្រើប្រាស់ GreenSphere",
    section_how_steps=[
        "ស្វែងរក @GreenSphereCommunity_Bot ក្នុង Telegram ហើយផ្ញើ /start។",
        "ចុច “Open GreenSphere WebApp” ដើម្បីមើលភារកិច្ចបៃតងប្រចាំថ្ងៃ។",
        "រាល់ថ្ងៃ សូមជ្រើសរើសសកម្មភាពបៃតង 1–3 និងចុច “Complete” ដើម្បីទទួលពិន្ទុ និងគណនាលំដាប់ថ្ងៃ (streak)។",
    ],
    section_why_title="ហេតុអ្វីជ្រើសរើស GreenSphere?",
    section_why_points=[
        "ការប្រើប្រាស់សាមញ្ញ: មិនចាំបាច់មានឧបករណ៍បន្ថែម និងការផ្ទុករូបថត។",
        "មានប្រតិកម្មច្បាស់លាស់: ពិន្ទុ G-Points, streak និង徽章 GreenSphere",
        "រចនាឡើងសម្រាប់ការប្រើប្រាស់រយៈពេលវែង: ភារកិច្ចស្រាល មិនបង្កើតភាពតានតឹង។",
    ],
    section_for_title="សាកសមសម្រាប់អ្នកណា?",
    section_for_items=[
        "មនុស្សគ្រប់រូបដែលយកចិត្តទុកដាក់ពីជីវិតបៃតង ប៉ុន្តែមិនចង់ប្រើឧបករណ៍ស្មុគស្មាញ។",
        "អ្នកដែលចូលចិត្តការតាមដានទម្លាប់ និងប្រមូល徽章។",
        "អ្នកធ្វើការផ្នែក ESG / Sustainability / Web3 ដោយចង់សាកល្បងនៅជាន់ព្រីទ្ធិការប្រព្រឹត្ត។",
    ],
    footer_slogan="Small Actions. Real Impact.",
)


def detect_lang(accept_language: str | None) -> str:
    """
    从 Accept-Language 里猜测语言，返回 zh/en/th/vi/km 之一，其它默认 en。
    """
    if not accept_language:
        return "en"
    header = accept_language.lower()

    if "zh" in header:
        return "zh"
    if "th" in header:
        return "th"
    if "vi" in header:
        return "vi"
    # km = Khmer; 某些浏览器可能用 "km" 或 "kh"
    if "km" in header or "kh" in header:
        return "km"

    return "en"

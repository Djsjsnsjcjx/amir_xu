"""
Railway 3x-UI Deployer Telegram Bot
Deploy 4 instances of 3x-ui to Railway with node configuration
"""

import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from railway_client import RailwayClient
from xui_panel import XUIPanel, wait_for_panel

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
REPO = os.getenv("REPO", "Wiwwiwiwiwiwi/3XUI_AMIR")
PROJECT_NAME = os.getenv("PROJECT_NAME", "3x-ui-amir")

# Service definitions: (name, region, is_main)
SERVICES = [
    ("NL", "NL", True),      # Main panel
    ("US_V", "US-VA", False),
    ("SG", "SG", False),
    ("NL_MT", "NL-MT", False),
]

PANEL_PORT = 3000
PANEL_USER = "admin"
PANEL_PASS = "admin"

# User session storage
user_sessions: dict[int, dict] = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 شروع", callback_data="show_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 به ربات Railway 3x-UI Deployer خوش آمدید!\n\n"
        "4 نمونه پنل 3x-ui با قابلیت اتصال Node:\n\n"
        "📌 NL (اصلی) → US_V, SG, NL_MT\n\n"
        "برای شروع:\n"
        "<code>/connect YOUR_RAILWAY_TOKEN</code>",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 دستورات:\n\n"
        "/start - شروع\n"
        "/connect <token> - اتصال به Railway\n"
        "/deploy - دپلوی + اتصال نودها\n"
        "/disconnect - قطع اتصال",
        parse_mode="HTML",
    )


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ لطفاً توکن را وارد کنید:\n<code>/connect YOUR_TOKEN</code>",
            parse_mode="HTML",
        )
        return

    token = context.args[0]
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ در حال بررسی...")

    try:
        client = RailwayClient(token)
        user_info = client.get_me()

        workspace_id = None
        workspace_name = "شخصی"
        if user_info.get("workspaces"):
            ws = user_info["workspaces"][0]
            workspace_id = ws["id"]
            workspace_name = ws["name"]

        if not workspace_id:
            raise Exception("ورک‌اسپیسی یافت نشد")

        user_sessions[user_id] = {
            "client": client,
            "workspace_id": workspace_id,
        }

        name = user_info.get("name") or user_info.get("username", "N/A")
        await update.message.reply_text(
            f"✅ متصل شد!\n\n"
            f"👤 {name}\n"
            f"📧 {user_info.get('email', 'N/A')}\n"
            f"🏢 {workspace_name}\n\n"
            f"با /deploy شروع کنید!",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n<code>{e}</code>", parse_mode="HTML")


async def disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("🔌 قطع شد.")
    else:
        await update.message.reply_text("⚠️ متصل نیستید.")


async def deploy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ ابتدا /connect بزنید.")
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ دپلوی کن", callback_data="confirm_deploy"),
            InlineKeyboardButton("❌ لغو", callback_data="cancel_deploy"),
        ]
    ]
    await update.message.reply_text(
        "🚀 <b>آماده دپلوی!</b>\n\n"
        f"📦 پروژه: <code>{PROJECT_NAME}</code>\n"
        f"🔗 ریپو: <code>{REPO}</code>\n\n"
        "سرویس‌ها:\n"
        "━━━━━━━━━━━━━━━━\n"
        "⭐ NL (اصلی)\n"
        "🔗 US_V → NL\n"
        "🔗 SG → NL\n"
        "🔗 NL_MT → NL\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "پس از دپلوی، نودها به صورت خودکار متصل می‌شوند.\n"
        "تأیید می‌کنید؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id = update.effective_user.id
    data = query.data

    try:
        if data == "confirm_deploy":
            if user_id not in user_sessions:
                await query.edit_message_text("⚠️ اتصال منقضی شده. /connect کنید.")
                return
            session = user_sessions[user_id]
            await start_deployment(query, session["client"], session["workspace_id"])

        elif data == "cancel_deploy":
            await query.edit_message_text("❌ لغو شد.")

        elif data == "show_help":
            await query.edit_message_text(
                "📋 دستورات:\n\n"
                "/start - شروع\n"
                "/connect <token> - اتصال\n"
                "/deploy - دپلوی + اتصال نودها\n"
                "/disconnect - قطع اتصال",
            )
    except Exception as e:
        logger.error(f"Button error: {e}")
        try:
            await query.edit_message_text(f"❌ خطا: <code>{e}</code>", parse_mode="HTML")
        except Exception:
            pass


async def start_deployment(query, client: RailwayClient, workspace_id: str):
    status_msg = query.message

    # Step 1: Create project
    await status_msg.edit_text(
        "🔨 <b>مرحله ۱/۵:</b> ایجاد پروژه...",
        parse_mode="HTML",
    )
    try:
        project = client.create_project(PROJECT_NAME, workspace_id)
        project_id = project["id"]
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا:\n<code>{e}</code>", parse_mode="HTML")
        return

    # Get environments
    try:
        envs = client.get_environments(project_id)
        prod_env_id = None
        for env in envs:
            if env["node"]["name"] == "production":
                prod_env_id = env["node"]["id"]
                break
        if not prod_env_id and envs:
            prod_env_id = envs[0]["node"]["id"]
    except Exception:
        prod_env_id = None

    # Step 2: Create services
    await status_msg.edit_text(
        "🔨 <b>مرحله ۲/۵:</b> ایجاد سرویس‌ها...",
        parse_mode="HTML",
    )

    created_services = []
    for name, region, is_main in SERVICES:
        try:
            service = client.create_service_from_repo(
                name=f"3xui-{name}",
                project_id=project_id,
                repo=REPO,
            )
            created_services.append((name, region, service["id"], is_main))
            done = "\n".join([
                f"  {'⭐' if m else '🔗'} {n} ({r})"
                for n, r, _, m in created_services
            ])
            pending = "\n".join([
                f"  ⏳ {n} ({r})"
                for n, r, _ in SERVICES
                if n not in [s[0] for s in created_services]
            ])
            await status_msg.edit_text(
                f"✅ پروژه: <code>{PROJECT_NAME}</code>\n\n"
                f"🔨 <b>مرحله ۲/۵:</b> ایجاد سرویس‌ها...\n\n{done}\n{pending}",
                parse_mode="HTML",
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ خطا:\n<code>{e}</code>", parse_mode="HTML")
            return

    # Step 3: Create domains
    await status_msg.edit_text(
        "🔨 <b>مرحله ۳/۵:</b> ایجاد دامین‌ها (پورت 3000)...",
        parse_mode="HTML",
    )

    domains = {}
    for name, region, service_id, is_main in created_services:
        try:
            if prod_env_id:
                d = client.create_service_domain(service_id, prod_env_id, target_port=PANEL_PORT)
                domains[name] = d.get("domain", "")
                await status_msg.edit_text(
                    f"✅ <b>{name}</b>: 🌐 {domains[name]}",
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.warning(f"Domain failed {name}: {e}")
            domains[name] = ""

    # Step 4: Deploy all services
    await status_msg.edit_text(
        "🔨 <b>مرحله ۴/۵:</b> دپلوی...",
        parse_mode="HTML",
    )

    deployed = []
    for name, region, service_id, is_main in created_services:
        try:
            if prod_env_id:
                d = client.deploy_service(service_id, prod_env_id)
                deployed.append((name, region, service_id, is_main, d.get("id", "OK")))
            else:
                deployed.append((name, region, service_id, is_main, "CREATED"))
        except Exception as e:
            logger.warning(f"Deploy failed {name}: {e}")
            deployed.append((name, region, service_id, is_main, "FAILED"))

    # Step 5: Wait and configure nodes
    await status_msg.edit_text(
        "🔨 <b>مرحله ۵/۵:</b> انتظار برای آماده شدن پنل‌ها...\n\n"
        "⏳ حدود 2-3 دقیقه صبر کنید...",
        parse_mode="HTML",
    )

    # Wait for panels to be ready
    panel_urls = {}
    for name, domain in domains.items():
        if domain:
            panel_urls[name] = f"https://{domain}"

    ready_panels = {}
    for name, url in panel_urls.items():
        await status_msg.edit_text(
            f"⏳ بررسی <b>{name}</b>...\n"
            f"🌐 {url}",
            parse_mode="HTML",
        )
        for attempt in range(12):  # 2 minutes
            try:
                resp = await asyncio.to_thread(
                    lambda: __import__("requests").get(url, timeout=10, allow_redirects=True)
                )
                if resp.status_code == 200:
                    ready_panels[name] = url
                    break
            except Exception:
                pass
            await asyncio.sleep(10)

    # Configure nodes
    if ready_panels:
        main_url = ready_panels.get("NL")
        if main_url:
            await status_msg.edit_text(
                "🔗 <b>اتصال نودها به پنل اصلی (NL)...</b>",
                parse_mode="HTML",
            )
            # Collect panel info for all ready panels
            node_info = {}
            for name, url in ready_panels.items():
                if name != "NL":
                    try:
                        panel = XUIPanel(url)
                        if panel.login():
                            settings = panel.get_settings()
                            node_info[name] = {
                                "url": url,
                                "uuid": settings.get("subKey", "") or settings.get("uuid", ""),
                                "port": settings.get("port", 2053),
                            }
                    except Exception as e:
                        logger.warning(f"Panel info error {name}: {e}")

    # Final summary
    summary = (
        "🎉 <b>انجام شد!</b>\n\n"
        f"📦 <code>{PROJECT_NAME}</code>\n"
        f"🆔 <code>{project_id}</code>\n"
        "━━━━━━━━━━━━━━━━\n\n"
    )

    for name, region, sid, is_main, did in deployed:
        icon = "⭐" if is_main else "🔗"
        dom = domains.get(name, "N/A")
        status = "✅" if did != "FAILED" else "❌"
        summary += f"{icon} {status} <b>{name}</b> ({region})\n"
        if dom:
            summary += f"   🌐 <a href='https://{dom}/managepanel/'>{dom}</a>\n"
        summary += "\n"

    summary += (
        "━━━━━━━━━━━━━━━━\n\n"
        "📌 <b>نکات:</b>\n"
        "• پنل NL اصلی است\n"
        "• پسورد پیش‌فرض: <code>admin/admin</code>\n"
        "• حتماً پسورد را تغییر دهید!\n"
        "• آدرس پنل: <code>دامنه/managepanel/</code>\n\n"
        f"🔗 <a href='https://railway.com/project/{project_id}'>باز کردن در Railway</a>"
    )
    await status_msg.edit_text(summary, parse_mode="HTML", disable_web_page_preview=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 /start بزنید.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("disconnect", disconnect))
    app.add_handler(CommandHandler("deploy", deploy))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

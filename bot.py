"""
Railway 3x-UI Deployer Telegram Bot
Deploy 4 instances of 3x-ui with automatic node connection
"""

import os
import logging
import asyncio
import requests as req
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
from xui_panel import XUIPanel, wait_for_panel, setup_all_nodes

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
REPO = os.getenv("REPO", "Wiwwiwiwiwiwi/3XUI_AMIR")
PROJECT_NAME = os.getenv("PROJECT_NAME", "3x-ui-amir")

# Service definitions: (name, region, is_main)
SERVICES = [
    ("NL", "NL", True),
    ("US_V", "US-VA", False),
    ("SG", "SG", False),
    ("NL_MT", "NL-MT", False),
]

PANEL_PORT = 3000

user_sessions: dict[int, dict] = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 شروع", callback_data="show_help")]]
    await update.message.reply_text(
        "👋 خوش آمدید!\n\n"
        "⭐ NL (اصلی) → 🔗 US_V, SG, NL_MT\n\n"
        "<code>/connect YOUR_RAILWAY_TOKEN</code>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 دستورات:\n\n"
        "/connect <token>\n"
        "/deploy\n"
        "/disconnect",
    )


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ /connect YOUR_TOKEN")
        return

    token = context.args[0]
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ بررسی...")

    try:
        client = RailwayClient(token)
        user_info = client.get_me()
        ws = user_info["workspaces"][0]
        user_sessions[user_id] = {"client": client, "workspace_id": ws["id"]}
        await update.message.reply_text(
            f"✅ متصل! {user_info.get('username','')}\n\n/deploy بزنید"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("🔌 قطع شد")


async def deploy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("⚠️ /connect بزنید")
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ دپلوی", callback_data="confirm_deploy"),
            InlineKeyboardButton("❌ لغو", callback_data="cancel_deploy"),
        ]
    ]
    await update.message.reply_text(
        "🚀 <b>آماده دپلوی + اتصال نودها</b>\n\n"
        "⭐ NL (اصلی)\n🔗 US_V, SG, NL_MT\n\n"
        "تأیید؟",
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
                await query.edit_message_text("⚠️ /connect کنید")
                return
            session = user_sessions[user_id]
            await start_deployment(query, session["client"], session["workspace_id"])
        elif data == "cancel_deploy":
            await query.edit_message_text("❌ لغو شد")
        elif data == "show_help":
            await query.edit_message_text("📋 /connect → /deploy → /disconnect")
    except Exception as e:
        logger.error(f"Button error: {e}")
        try:
            await query.edit_message_text(f"❌ {e}")
        except Exception:
            pass


async def start_deployment(query, client: RailwayClient, workspace_id: str):
    msg = query.message

    # 1. Create project
    await msg.edit_text("🔨 ۱/۵ ایجاد پروژه...", parse_mode="HTML")
    try:
        project = client.create_project(PROJECT_NAME, workspace_id)
        project_id = project["id"]
    except Exception as e:
        await msg.edit_text(f"❌ {e}")
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

    # 2. Create services
    await msg.edit_text("🔨 ۲/۵ ایجاد سرویس‌ها...", parse_mode="HTML")
    created = []
    for name, region, is_main in SERVICES:
        try:
            svc = client.create_service_from_repo(
                name=f"3xui-{name}", project_id=project_id, repo=REPO
            )
            created.append((name, region, svc["id"], is_main))
            done = "\n".join([f"  {'⭐' if m else '🔗'} {n}" for n, _, _, m in created])
            await msg.edit_text(f"🔨 ۲/۵ سرویس‌ها...\n\n{done}", parse_mode="HTML")
        except Exception as e:
            await msg.edit_text(f"❌ {name}: {e}")
            return

    # 3. Create domains
    await msg.edit_text("🔨 ۳/۵ ایجاد دامین‌ها...", parse_mode="HTML")
    domains = {}
    for name, region, svc_id, is_main in created:
        try:
            d = client.create_service_domain(svc_id, prod_env_id, target_port=PANEL_PORT)
            domains[name] = d.get("domain", "")
        except Exception as e:
            logger.warning(f"Domain failed {name}: {e}")

    # 4. Deploy
    await msg.edit_text("🔨 ۴/۵ دپلوی...", parse_mode="HTML")
    for name, region, svc_id, is_main in created:
        try:
            client.deploy_service(svc_id, prod_env_id)
        except Exception as e:
            logger.warning(f"Deploy failed {name}: {e}")

    # 5. Wait + Connect nodes
    await msg.edit_text(
        "🔨 ۵/۵ انتظار برای آماده شدن پنل‌ها...\n"
        "⏳ حدود 2-3 دقیقه",
        parse_mode="HTML",
    )

    # Build URLs
    main_domain = domains.get("NL", "")
    main_url = f"https://{main_domain}" if main_domain else ""
    node_urls = {}
    for name, domain in domains.items():
        if name != "NL" and domain:
            node_urls[name] = f"https://{domain}"

    if not main_url:
        await msg.edit_text("❌ دامین NL ایجاد نشد")
        return

    # Wait for main panel
    await msg.edit_text(f"⏳ بررسی NL...\n🌐 {main_url}", parse_mode="HTML")
    ready = await asyncio.to_thread(wait_for_panel, main_url, 180, 10)
    if not ready:
        await msg.edit_text(f"❌ پنل NL آماده نشد\n{main_url}")
        return

    # Wait for other panels
    ready_nodes = {}
    for name, url in node_urls.items():
        await msg.edit_text(f"⏳ بررسی {name}...\n🌐 {url}", parse_mode="HTML")
        ready = await asyncio.to_thread(wait_for_panel, url, 180, 10)
        if ready:
            ready_nodes[name] = url

    # Configure nodes
    await msg.edit_text("🔗 اتصال نودها...", parse_mode="HTML")

    # Login to main panel
    main_panel = await asyncio.to_thread(XUIPanel, main_url)
    if not await asyncio.to_thread(main_panel.login):
        await msg.edit_text("❌ خطا در ورود به پنل اصلی NL")
        return

    # Get info from all panels
    panel_info = {}
    for name, url in {"NL": main_url, **ready_nodes}.items():
        panel = await asyncio.to_thread(XUIPanel, url)
        if await asyncio.to_thread(panel.login):
            settings = await asyncio.to_thread(panel.get_settings)
            panel_info[name] = {
                "url": url,
                "uuid": settings.get("subKey", "") or settings.get("uuid", ""),
                "port": settings.get("port", 2053),
            }

    # Summary
    summary = (
        "🎉 <b>انجام شد!</b>\n\n"
        f"📦 <code>{PROJECT_NAME}</code>\n"
        f"🆔 <code>{project_id}</code>\n"
        "━━━━━━━━━━━━━━━━\n\n"
    )

    for name, region, sid, is_main in created:
        icon = "⭐" if is_main else "🔗"
        dom = domains.get(name, "N/A")
        info = panel_info.get(name, {})
        status = "✅" if name in panel_info else "⏳"
        summary += f"{icon} {status} <b>{name}</b> ({region})\n"
        if dom:
            summary += f"   🌐 <a href='https://{dom}/managepanel/'>{dom}</a>\n"
        if info.get("uuid"):
            summary += f"   🆔 <code>{info['uuid'][:12]}...</code>\n"
        summary += "\n"

    summary += (
        "━━━━━━━━━━━━━━━━\n\n"
        "📌 <b>نودها را دستی متصل کنید:</b>\n"
        "1. وارد پنل NL شوید\n"
        "2. بخش Settings → Multi-Server\n"
        "3. آدرس و پورت هر پنل را اضافه کنید\n\n"
        "🔑 پسورد پیش‌فرض: <code>admin/admin</code>\n"
        f"🔗 <a href='https://railway.com/project/{project_id}'>Railway</a>"
    )
    await msg.edit_text(summary, parse_mode="HTML", disable_web_page_preview=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 /start بزنید")


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

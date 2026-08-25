"""
Railway 3x-UI Deployer Telegram Bot
Deploy 4 instances of 3x-ui with automatic node connection
"""

import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from railway_client import RailwayClient
from xui_panel import XUIPanel, wait_for_panel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
REPO_NAME = os.getenv("REPO_NAME", "Wiwwiwiwiwiwi/3XUI_AMIR")
PROJECT_NAME = os.getenv("PROJECT_NAME", "3x-ui-amir")

# Service definitions: (name, region)
SERVICES = [
    ("NL", "NL"),
    ("US_V", "US-VA"),
    ("SG", "SG"),
    ("NL_MT", "NL-MT"),
]

# Node connection settings
MAIN_PANEL = "NL"  # Main panel name
XUI_USERNAME = os.getenv("XUI_USERNAME", "admin")
XUI_PASSWORD = os.getenv("XUI_PASSWORD", "admin")


def format_status(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 شروع", callback_data="start_deploy")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="show_help")],
    ]
    await update.message.reply_text(
        "🎉 <b>Railway 3x-UI Deployer</b>\n\n"
        "با استفاده از این ربات می‌تونی 4 پنل 3x-ui روی Railway بسازی و خودکار به هم وصلشون کنی.\n\n"
        "📌 برای شروع /connect بزن.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def cmd_connect(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Store user's Railway API token"""
    if not ctx.args:
        await update.message.reply_text(
            "🔑 <b>اتصال به Railway</b>\n\n"
            "توکن API خودت رو بفرست:\n"
            "<code>/connect YOUR_TOKEN</code>\n\n"
            "📌 از Railway Dashboard > Settings > Tokens بگیر.",
            parse_mode="HTML",
        )
        return

    token = ctx.args[0]
    ctx.user_data["railway_token"] = token
    await update.message.reply_text("✅ توکن ذخیره شد! حالا /deploy بزن.", parse_mode="HTML")


async def cmd_deploy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Deploy 4 services and connect nodes"""
    token = ctx.user_data.get("railway_token")
    if not token:
        await update.message.reply_text("❌ اول /connect بزن و توکنت رو بفرست.", parse_mode="HTML")
        return

    status_msg = await update.message.reply_text("⏳ شروع...", parse_mode="HTML")
    client = RailwayClient(token)

    # Step 1: Get user info
    await status_msg.edit_text("🔍 <b>مرحله ۱/۵:</b> بررسی اکانت...", parse_mode="HTML")
    user_info = client.get_me()
    if not user_info:
        await status_msg.edit_text("❌ خطا در اتصال به Railway API", parse_mode="HTML")
        return

    workspace_id = None
    if user_info.get("workspaces"):
        ws = user_info["workspaces"][0]
        workspace_id = ws["id"]
    
    if not workspace_id:
        await status_msg.edit_text("❌ Workspace پیدا نشد", parse_mode="HTML")
        return

    # Step 2: Create project
    await status_msg.edit_text("✅ اکانت متصل شد\n\n🔨 <b>مرحله ۲/۵:</b> ایجاد پروژه...", parse_mode="HTML")
    project = client.create_project(PROJECT_NAME, workspace_id)
    if not project:
        await status_msg.edit_text("❌ خطا در ایجاد پروژه", parse_mode="HTML")
        return

    project_id = project["id"]
    environment_id = project.get("environmentId", "")
    if not environment_id:
        envs = client.get_environments(project_id)
        environment_id = envs[0]["id"] if envs else ""

    # Step 3: Create services
    await status_msg.edit_text(
        f"✅ پروژه ایجاد شد\n\n🔨 <b>مرحله ۳/۵:</b> ایجاد 4 سرویس...",
        parse_mode="HTML",
    )
    created = []
    for name, region in SERVICES:
        svc = client.create_service_from_repo(project_id, REPO_NAME, name)
        if svc:
            created.append((name, region, svc["id"]))
            await status_msg.edit_text(
                f"✅ پروژه ایجاد شد\n\n"
                f"🔨 <b>مرحله ۳/۵:</b> سرویس {name} ✅",
                parse_mode="HTML",
            )

    # Step 4: Deploy
    await status_msg.edit_text(
        f"✅ {len(created)} سرویس ایجاد شد\n\n🚀 <b>مرحله ۴/۵:</b> دپلوی...",
        parse_mode="HTML",
    )
    for name, region, svc_id in created:
        client.deploy_service(svc_id, environment_id)

    # Step 5: Wait and connect nodes
    await status_msg.edit_text(
        f"✅ {len(created)} سرویس دپلوی شد\n\n⏳ <b>مرحله ۵/۵:</b> انتظار برای آماده شدن پنل‌ها...",
        parse_mode="HTML",
    )

    # Collect service info
    service_info = []
    for name, region, svc_id in created:
        domains_data = client.get_service_domains(svc_id)
        domain = domains_data.get("domain", "") if domains_data else ""
        service_info.append({
            "name": name,
            "region": region,
            "id": svc_id,
            "domain": domain,
            "url": f"https://{domain}" if domain else "",
        })

    # Wait for panels to be ready
    ready_panels = {}
    for svc in service_info:
        if svc["url"]:
            await status_msg.edit_text(
                f"⏳ بررسی {svc['name']}...",
                parse_mode="HTML",
            )
            if await asyncio.to_thread(wait_for_panel, svc["url"], 180):
                ready_panels[svc["name"]] = svc
                await status_msg.edit_text(
                    f"✅ {svc['name']} آماده شد! ({len(ready_panels)}/{len(service_info)})",
                    parse_mode="HTML",
                )

    # Connect nodes automatically
    if MAIN_PANEL in ready_panels and len(ready_panels) > 1:
        await status_msg.edit_text("🔗 اتصال خودکار نودها...", parse_mode="HTML")

        main_svc = ready_panels[MAIN_PANEL]
        main_panel = XUIPanel(main_svc["url"], XUI_USERNAME, XUI_PASSWORD)
        
        if await asyncio.to_thread(main_panel.login):
            # Login to main panel and get UUID
            main_uuid = await asyncio.to_thread(main_panel.get_uuid)

            for svc_name, svc_data in ready_panels.items():
                if svc_name == MAIN_PANEL:
                    continue

                await status_msg.edit_text(f"🔗 اتصال {svc_name}...", parse_mode="HTML")

                node_panel = XUIPanel(svc_data["url"], XUI_USERNAME, XUI_PASSWORD)
                if await asyncio.to_thread(node_panel.login):
                    node_uuid = await asyncio.to_thread(node_panel.get_uuid)
                    node_token = await asyncio.to_thread(node_panel.create_api_token)

                    result = await asyncio.to_thread(
                        main_panel.add_node, svc_name, svc_data["url"], node_uuid, node_token
                    )

                    if result.get("success"):
                        await status_msg.edit_text(
                            f"✅ {svc_name} متصل شد!",
                            parse_mode="HTML",
                        )
                    else:
                        await status_msg.edit_text(
                            f"⚠️ خطا اتصال {svc_name}: {result.get('msg', '')[:100]}",
                            parse_mode="HTML",
                        )
                else:
                    await status_msg.edit_text(
                        f"❌ ورود به {svc_name} ناموفق",
                        parse_mode="HTML",
                    )

    # Final summary
    summary = (
        "🎉 <b>انجام شد!</b>\n\n"
        f"📦 <code>{PROJECT_NAME}</code>\n"
        f"🆔 <code>{project_id}</code>\n"
        "━━━━━━━━━━━━━━━━\n\n"
    )
    for svc in service_info:
        status = "✅" if svc["name"] in ready_panels else "⏳"
        summary += f"{status} <b>{svc['name']}</b> ({svc['region']})\n"
        if svc["url"]:
            summary += f"   🌐 <a href=\"{svc['url']}/managepanel/\">{svc['url']}</a>\n"
        summary += "\n"

    if MAIN_PANEL in ready_panels:
        main_panel = XUIPanel(ready_panels[MAIN_PANEL]["url"], XUI_USERNAME, XUI_PASSWORD)
        if await asyncio.to_thread(main_panel.login):
            nodes = await asyncio.to_thread(main_panel.get_nodes)
            if nodes:
                summary += "🔗 <b>نودهای متصل:</b>\n"
                for n in nodes:
                    summary += f"  ✅ {n.get('name')}: {n.get('status')}\n"

    summary += (
        "\n━━━━━━━━━━━━━━━━\n"
        f"🔑 پیش‌فرض: <code>admin</code> / <code>admin</code>\n"
        f"📊 اینباندها: 4"
    )

    await status_msg.edit_text(summary, parse_mode="HTML")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show status of services"""
    token = ctx.user_data.get("railway_token")
    if not token:
        await update.message.reply_text("❌ اول /connect بزن.", parse_mode="HTML")
        return

    client = RailwayClient(token)
    user_info = client.get_me()
    if not user_info:
        await update.message.reply_text("❌ خطا در اتصال", parse_mode="HTML")
        return

    projects = client.list_projects()
    if not projects:
        await update.message.reply_text("📭 پروژه‌ای وجود نداره.", parse_mode="HTML")
        return

    summary = "📊 <b>وضعیت سرویس‌ها</b>\n\n"
    for proj in projects:
        services = client.get_services(proj["id"])
        summary += f"📦 <b>{proj['name']}</b>\n"
        for svc in services:
            summary += f"  🔹 {svc['name']}\n"
        summary += "\n"

    await update.message.reply_text(summary, parse_mode="HTML")


async def cmd_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Delete a project"""
    token = ctx.user_data.get("railway_token")
    if not token:
        await update.message.reply_text("❌ اول /connect بزن.", parse_mode="HTML")
        return

    client = RailwayClient(token)
    projects = client.list_projects()
    if not projects:
        await update.message.reply_text("📭 پروژه‌ای وجود نداره.", parse_mode="HTML")
        return

    keyboard = [
        [InlineKeyboardButton(p["name"], callback_data=f"delete:{p['id']}")]
        for p in projects
    ]
    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="cancel")])

    await update.message.reply_text(
        "🗑️ کدوم پروژه رو حذف کنم؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()

    if query.data == "start_deploy":
        await query.edit_message_text("🚀 /deploy بزن تا شروع کنی!", parse_mode="HTML")
    elif query.data == "show_help":
        await query.edit_message_text(
            "ℹ️ <b>راهنما</b>\n\n"
            "1. /connect TOKEN - اتصال به Railway\n"
            "2. /deploy - ساخت 4 پنل + اتصال نودها\n"
            "3. /status - بررسی وضعیت\n"
            "4. /delete - حذف پروژه\n\n"
            "📌 نود اصلی: NL",
            parse_mode="HTML",
        )
    elif query.data.startswith("delete:"):
        project_id = query.data.split(":")[1]
        client = RailwayClient(ctx.user_data.get("railway_token", ""))
        result = client.delete_project(project_id)
        if result:
            await query.edit_message_text("✅ پروژه حذف شد!", parse_mode="HTML")
        else:
            await query.edit_message_text("❌ خطا در حذف", parse_mode="HTML")
    elif query.data == "cancel":
        await query.edit_message_text("❌ لغو شد.", parse_mode="HTML")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("connect", cmd_connect))
    app.add_handler(CommandHandler("deploy", cmd_deploy))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CallbackQueryHandler(cb_handler))

    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()

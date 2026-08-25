"""
Railway 3x-UI Deployer Telegram Bot
Deploy 5 instances of 3x-ui to Railway with a single command
"""

import os
import logging
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

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
REPO_IMAGE = os.getenv(
    "REPO_IMAGE", "ghcr.io/wiwwiwiwiwiwi/3x_ui_amir:latest"
)
PROJECT_NAME = os.getenv("PROJECT_NAME", "3x-ui-amir")

# Service definitions: (name, region hint for env vars)
SERVICES = [
    ("NL", "NL"),
    ("US_C", "US-CA"),
    ("US_V", "US-VA"),
    ("SG", "SG"),
    ("NL_MT", "NL-MT"),
]

# User session storage
user_sessions: dict[int, dict] = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    keyboard = [
        [InlineKeyboardButton("🚀 شروع", callback_data="show_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 به ربات Railway 3x-UI Deployer خوش آمدید!\n\n"
        "این ربات به شما امکان می‌دهد 5 نمونه از پنل 3x-ui را "
        "به صورت خودکار روی Railway دپلوی کنید.\n\n"
        "📌 مناطق: NL | US_C | US_V | SG | NL_MT\n\n"
        "برای شروع، توکن API Railway خود را ارسال کنید:\n"
        "<code>/connect YOUR_TOKEN</code>",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    await update.message.reply_text(
        "📋 دستورات ربات:\n\n"
        "/start - شروع مجدد\n"
        "/connect <token> - اتصال به Railway با توکن API\n"
        "/deploy - دپلوی 5 نمونه 3x-ui\n"
        "/status - بررسی وضعیت دپلوی\n"
        "/disconnect - قطع اتصال از Railway\n\n"
        "🔑 برای دریافت توکن API:\n"
        "1. به dashboard.railway.com بروید\n"
        "2. Account Settings > Tokens\n"
        "3. یک توکن جدید بسازید\n"
        "4. توکن را با /connect ارسال کنید",
        parse_mode="HTML",
    )


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Connect to Railway with API token"""
    if not context.args:
        await update.message.reply_text(
            "❌ لطفاً توکن API را وارد کنید:\n"
            "<code>/connect YOUR_TOKEN</code>",
            parse_mode="HTML",
        )
        return

    token = context.args[0]
    user_id = update.effective_user.id

    await update.message.reply_text("⏳ در حال بررسی توکن...")

    try:
        client = RailwayClient(token)
        user_info = client.get_me()
        
        workspace_name = " شخصی"
        workspace_id = None
        if user_info.get("workspaces"):
            ws = user_info["workspaces"][0]
            workspace_name = ws["name"]
            workspace_id = ws["id"]

        user_sessions[user_id] = {
            "client": client,
            "workspace_id": workspace_id,
        }

        await update.message.reply_text(
            f"✅ با موفقیت متصل شد!\n\n"
            f"👤 نام: {user_info.get('name') or user_info.get('username', 'N/A')}\n"
            f"📧 ایمیل: {user_info.get('email', 'N/A')}\n"
            f"🏢 ورک‌اسپیس: {workspace_name}\n\n"
            f"حالا می‌توانید با /deploy شروع به دپلوی کنید!",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در اتصال:\n<code>{str(e)}</code>",
            parse_mode="HTML",
        )


async def disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disconnect from Railway"""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("🔌 اتصال قطع شد.")
    else:
        await update.message.reply_text("⚠️ شما از قبل متصل نیستید.")


async def deploy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deploy 5 instances of 3x-ui"""
    user_id = update.effective_user.id

    if user_id not in user_sessions:
        await update.message.reply_text(
            "⚠️ ابتدا باید به Railway متصل شوید.\n"
            "از دستور <code>/connect YOUR_TOKEN</code> استفاده کنید.",
            parse_mode="HTML",
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ بله، دپلوی کن", callback_data="confirm_deploy"),
            InlineKeyboardButton("❌ لغو", callback_data="cancel_deploy"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🚀 <b>آماده دپلوی!</b>\n\n"
        f"📦 پروژه: <code>{PROJECT_NAME}</code>\n"
        f"🐳 تصویر: <code>{REPO_IMAGE}</code>\n\n"
        "سرویس‌هایی که ساخته می‌شوند:\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🇳🇱 NL\n"
        "🇺🇸 US_C\n"
        "🇺🇸 US_V\n"
        "🇸🇬 SG\n"
        "🇳🇱 NL_MT\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "آیا مطمئن هستید؟",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard buttons"""
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
                await query.edit_message_text(
                    "⚠️ اتصال منقضی شده. دوباره /connect کنید."
                )
                return

            session = user_sessions[user_id]
            await start_deployment(query, session["client"], session.get("workspace_id"))

        elif data == "cancel_deploy":
            await query.edit_message_text("❌ دپلوی لغو شد.")

        elif data == "show_help":
            await query.edit_message_text(
                "📋 دستورات ربات:\n\n"
                "/start - شروع مجدد\n"
                "/connect <token> - اتصال به Railway\n"
                "/deploy - دپلوی 5 نمونه 3x-ui\n"
                "/status - بررسی وضعیت\n"
                "/disconnect - قطع اتصال",
            )

    except Exception as e:
        logger.error(f"Button handler error: {e}")
        try:
            await query.edit_message_text(
                f"❌ خطا: <code>{str(e)}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass


async def start_deployment(query, client: RailwayClient, workspace_id: str = None):
    """Execute the deployment process"""
    status_msg = query.message

    # Step 1: Create project
    await status_msg.edit_text(
        "🔨 <b>مرحله ۱ از ۳:</b> ایجاد پروژه...\n\n"
        f"📦 نام پروژه: <code>{PROJECT_NAME}</code>",
        parse_mode="HTML",
    )

    try:
        project = client.create_project(PROJECT_NAME, workspace_id)
        project_id = project["id"]
    except Exception as e:
        await status_msg.edit_text(
            f"❌ خطا در ایجاد پروژه:\n<code>{str(e)}</code>",
            parse_mode="HTML",
        )
        return

    # Get environments (to find production environment ID)
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

    await status_msg.edit_text(
        f"✅ پروژه ایجاد شد: <code>{PROJECT_NAME}</code>\n"
        f"🆔 ID: <code>{project_id}</code>\n\n"
        "🔨 <b>مرحله ۲ از ۳:</b> ایجاد سرویس‌ها...",
        parse_mode="HTML",
    )

    # Step 2: Create services
    created_services = []
    for name, region in SERVICES:
        try:
            service = client.create_service_from_image(
                name=f"3x-ui-{name}",
                project_id=project_id,
                image=REPO_IMAGE,
                environment_id=prod_env_id,
            )
            created_services.append((name, region, service["id"]))
            await status_msg.edit_text(
                f"✅ پروژه: <code>{PROJECT_NAME}</code>\n\n"
                f"🔨 <b>مرحله ۲ از ۳:</b> ایجاد سرویس‌ها...\n\n"
                + "\n".join([f"  ✅ {n} ({r})" for n, r, _ in created_services])
                + "\n"
                + "\n".join(
                    [
                        f"  ⏳ {n} ({r})"
                        for n, r in SERVICES
                        if n not in [s[0] for s in created_services]
                    ]
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            await status_msg.edit_text(
                f"❌ خطا در ایجاد سرویس {name}:\n<code>{str(e)}</code>",
                parse_mode="HTML",
            )
            return

    # Step 3: Trigger deployments
    await status_msg.edit_text(
        f"✅ پروژه: <code>{PROJECT_NAME}</code>\n"
        f"✅ سرویس‌ها: {len(created_services)} سرویس ایجاد شد\n\n"
        "🔨 <b>مرحله ۳ از ۳:</b> شروع دپلوی...",
        parse_mode="HTML",
    )

    deployed = []
    for name, region, service_id in created_services:
        try:
            if prod_env_id:
                deployment = client.deploy_service(service_id, prod_env_id)
                deployed.append((name, region, service_id, deployment.get("id", "OK")))
            else:
                deployed.append((name, region, service_id, "CREATED"))
        except Exception as e:
            logger.warning(f"Deployment failed for {name}: {e}")
            deployed.append((name, region, service_id, "FAILED"))

    # Final summary
    summary = (
        "🎉 <b>دپلوی با موفقیت انجام شد!</b>\n\n"
        f"📦 پروژه: <code>{PROJECT_NAME}</code>\n"
        f"🆔 Project ID: <code>{project_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for name, region, service_id, deploy_id in deployed:
        status = "✅" if deploy_id != "FAILED" else "❌"
        summary += f"{status} <b>{name}</b> ({region})\n"
        summary += f"   🆔 Service: <code>{service_id}</code>\n"
        summary += f"   🚀 Deploy: <code>{deploy_id}</code>\n\n"

    summary += (
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ دپلوی ممکن است چند دقیقه طول بکشد.\n"
        "🔗 داشبورد: "
        f"<a href='https://railway.com/project/{project_id}'>باز کردن در Railway</a>"
    )

    await status_msg.edit_text(summary, parse_mode="HTML", disable_web_page_preview=True)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check deployment status"""
    user_id = update.effective_user.id

    if user_id not in user_sessions:
        await update.message.reply_text(
            "⚠️ ابتدا با /connect متصل شوید.",
        )
        return

    await update.message.reply_text("⏳ در حال بررسی وضعیت...")
    # TODO: implement status check
    await update.message.reply_text(
        "📊 وضعیت دپلوی از طریق لینک زیر قابل بررسی است:\n"
        f"<a href='https://railway.com'>باز کردن Railway</a>",
        parse_mode="HTML",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown messages"""
    await update.message.reply_text(
        "🤔 دستور نامشخص. از /start برای شروع استفاده کنید."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling update: {context.error}")


def main():
    """Start the bot"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN environment variable is not set!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("disconnect", disconnect))
    app.add_handler(CommandHandler("deploy", deploy))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("🤖 Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

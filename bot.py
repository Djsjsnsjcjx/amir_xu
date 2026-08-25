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
    ConversationHandler,
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

# Conversation states
WAITING_TOKEN = 1

# User session storage (token per user)
user_sessions: dict[int, RailwayClient] = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- Handlers ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    keyboard = [
        [InlineKeyboardButton("🚀 شروع", callback_data="help")],
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
        user_sessions[user_id] = client

        team_name = " شخصی"
        if user_info.get("teams", {}).get("edges"):
            team_name = user_info["teams"]["edges"][0]["node"]["name"]

        await update.message.reply_text(
            f"✅ با موفقیت متصل شد!\n\n"
            f"👤 نام: {user_info.get('name', 'N/A')}\n"
            f"📧 ایمیل: {user_info.get('email', 'N/A')}\n"
            f"🏢 تیم: {team_name}\n\n"
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

    client = user_sessions[user_id]

    # Confirmation keyboard
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
    await query.answer()

    user_id = update.effective_user.id

    if query.data == "confirm_deploy":
        if user_id not in user_sessions:
            await query.edit_message_text("⚠️ اتصال منقضی شده. دوباره /connect کنید.")
            return

        client = user_sessions[user_id]
        await start_deployment(query, client)

    elif query.data == "cancel_deploy":
        await query.edit_message_text("❌ دپلوی لغو شد.")

    elif query.data == "help":
        await query.edit_message_text(
            "📋 دستورات ربات:\n\n"
            "/start - شروع مجدد\n"
            "/connect <token> - اتصال به Railway\n"
            "/deploy - دپلوی 5 نمونه 3x-ui\n"
            "/status - بررسی وضعیت\n"
            "/disconnect - قطع اتصال",
            parse_mode="HTML",
        )


async def start_deployment(query, client: RailwayClient):
    """Execute the deployment process"""
    status_msg = query.message

    # Step 1: Create project
    await status_msg.edit_text(
        "🔨 <b>مرحله ۱ از ۳:</b> ایجاد پروژه...\n\n"
        f"📦 نام پروژه: <code>{PROJECT_NAME}</code>",
        parse_mode="HTML",
    )

    try:
        project = client.create_project(PROJECT_NAME)
        project_id = project["id"]
    except Exception as e:
        await status_msg.edit_text(
            f"❌ خطا در ایجاد پروژه:\n<code>{str(e)}</code>",
            parse_mode="HTML",
        )
        return

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
            )
            created_services.append((name, region, service["id"]))
            await status_msg.edit_text(
                f"✅ پروژه: <code>{PROJECT_NAME}</code>\n\n"
                f"🔨 <b>مرحله ۲ از ۳:</b> ایجاد سرویس‌ها...\n\n"
                + "\n".join(
                    [
                        f"  ✅ {n} ({r})"
                        for n, r, _ in created_services
                    ]
                )
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
            deployment = client.trigger_deployment(service_id)
            deployed.append((name, region, service_id, deployment.get("id", "N/A")))
        except Exception as e:
            logger.warning(f"Deployment trigger failed for {name}: {e}")
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
        "از /status برای بررسی وضعیت استفاده کنید.\n\n"
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
            parse_mode="HTML",
        )
        return

    client = user_sessions[user_id]

    await update.message.reply_text("⏳ در حال بررسی وضعیت...")

    try:
        # Get user info to find projects
        user_info = client.get_me()
        team_edges = user_info.get("teams", {}).get("edges", [])

        if not team_edges:
            await update.message.reply_text("⚠️ تیمی یافت نشد.")
            return

        team_id = team_edges[0]["node"]["id"]

        # Query projects
        query = """
        query {
            projects {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
        """
        data = client._query(query)
        projects = data.get("projects", {}).get("edges", [])

        # Find our project
        target_project = None
        for p in projects:
            if p["node"]["name"] == PROJECT_NAME:
                target_project = p["node"]
                break

        if not target_project:
            await update.message.reply_text(
                f"⚠️ پروژه <code>{PROJECT_NAME}</code> یافت نشد.\n"
                "اول /deploy را اجرا کنید.",
                parse_mode="HTML",
            )
            return

        # Get services in project
        svc_query = """
        query($projectId: String!) {
            services(input: {projectId: $projectId}) {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
        """
        svc_data = client._query(svc_query, {"projectId": target_project["id"]})
        services = svc_data.get("services", {}).get("edges", [])

        if not services:
            await update.message.reply_text("⚠️ سرویسی یافت نشد.")
            return

        msg = f"📊 <b>وضعیت پروژه {PROJECT_NAME}</b>\n\n"

        for svc in services:
            svc_id = svc["node"]["id"]
            svc_name = svc["node"]["name"]

            try:
                deploy = client.get_deployment_status(svc_id)
                status_text = deploy.get("status", "UNKNOWN")
                status_icon = {
                    "SUCCESS": "✅",
                    "ACTIVE": "🟢",
                    "INITIALIZING": "🔄",
                    "BUILDING": "🔨",
                    "DEPLOYING": "🚀",
                    "REMOVING": "🗑️",
                    "FAILED": "❌",
                    "REMOVED": "❌",
                    "CRASHED": "💥",
                }.get(status_text, "❓")

                msg += f"{status_icon} <b>{svc_name}</b>: {status_text}\n"
            except Exception:
                msg += f"❓ <b>{svc_name}</b>: UNKNOWN\n"

        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در بررسی وضعیت:\n<code>{str(e)}</code>",
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
    if update and hasattr(update, "message") and update.message:
        await update.message.reply_text(
            "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید."
        )


def main():
    """Start the bot"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN environment variable is not set!")
        print("Set it in Railway dashboard > Variables")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("disconnect", disconnect))
    app.add_handler(CommandHandler("deploy", deploy))
    app.add_handler(CommandHandler("status", status))

    # Callback query handler for inline buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Fallback message handler
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Error handler
    app.add_error_handler(error_handler)

    print("🤖 Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

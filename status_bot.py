import os
import sys
import json
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import CommandStart, Command
from aiogram.client.default import DefaultBotProperties

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = '\033[91m'; GREEN = '\033[92m'; YELLOW = '\033[93m'
        BLUE = '\033[94m'; MAGENTA = '\033[95m'; CYAN = '\033[96m'
        WHITE = '\033[97m'; RESET = '\033[0m'
    class Style:
        RESET_ALL = '\033[0m'; BRIGHT = '\033[1m'

import config

STATE_FILE = "bot_state.json"

DEFAULT_STATE = {
    "owner_chat_id": None,
    "total_reports": 0,
    "rounds_completed": 0,
    "accounts_logged_in": 0,
    "total_accounts": len(getattr(config, "PHONE_NUMBERS", [])),
    "proofs_sent": 0,
    "last_activity": None,
    "start_time": datetime.now().isoformat(),
    "errors": [],
    "target": getattr(config, "TARGET_USERNAME", "unknown"),
    "target_display": getattr(config, "TARGET_DISPLAY_NAME", ""),
    "scammer_phone": getattr(config, "SCAMMER_REAL_PHONE", ""),
}


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": Fore.WHITE, "SUCCESS": Fore.GREEN, "WARN": Fore.YELLOW,
              "ERROR": Fore.RED, "STEP": Fore.CYAN, "BOT": Fore.MAGENTA}
    color = colors.get(level, Fore.WHITE)
    print(f"{color}[{ts}] [{level}] {msg}{Style.RESET_ALL}")


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
                for k, v in DEFAULT_STATE.items():
                    s.setdefault(k, v)
                return s
        except Exception:
            return dict(DEFAULT_STATE)
    return dict(DEFAULT_STATE)


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


STATE = load_state()


def get_uptime(start_iso):
    try:
        start = datetime.fromisoformat(start_iso)
    except Exception:
        start = datetime.now()
    diff = datetime.now() - start
    days, rem = divmod(int(diff.total_seconds()), 86400)
    hrs, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hrs: parts.append(f"{hrs}h")
    if mins: parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def status_text():
    extras = getattr(config, "EXTRA_TARGETS", [])
    up = get_uptime(STATE.get("start_time", datetime.now().isoformat()))
    last = STATE.get("last_activity") or "—"
    errs = STATE.get("errors") or []
    errs_txt = "\n".join([f"  • {e}" for e in errs[-5:]]) if errs else "  — (none)"
    return f"""📊 <b>Status Report</b>

🎯 <b>Target:</b> {STATE.get('target_display')}
   ID: <code>{STATE.get('target')}</code>
   Phone: <code>{STATE.get('scammer_phone')}</code>

📈 <b>Progress:</b>
   • Reports Sent: <b>{STATE.get('total_reports')}</b>
   • Rounds Completed: <b>{STATE.get('rounds_completed')}</b>
   • Proofs Submitted: <b>{STATE.get('proofs_sent')}</b>

👥 <b>Accounts:</b>
   • Logged in: {STATE.get('accounts_logged_in')} / {STATE.get('total_accounts')}

🎯 <b>Extra Targets ({len(extras)}):</b>
{chr(10).join(['   • ' + x for x in extras]) if extras else '   —'}

⏱️ <b>Uptime:</b> {up}
🕐 <b>Last Activity:</b> {last}

⚠️ <b>Recent Errors:</b>
{errs_txt}

📡 Bot is LIVE. Use commands below.
"""


if not getattr(config, "BOT_TOKEN", None):
    log("BOT_TOKEN not set in config.py. Add bot token first.", "ERROR")
    sys.exit(1)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if owner is None:
        STATE["owner_chat_id"] = user_id
        save_state(STATE)
        await message.answer(f"✅ <b>Owner registered!</b>\n\nYour chat ID: <code>{user_id}</code>\n"
                             f"Use /status for live stats, /help for commands.")
        log(f"Owner registered via /start: chat_id={user_id}", "BOT")
    elif owner == user_id:
        await message.answer("👋 Welcome back, owner! Use /status for live stats, /help for commands.")
    else:
        await message.answer("⛔ <b>Access Denied.</b>\nThis status bot is private.")
        log(f"Unauthorized /start from user_id={user_id}", "WARN")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if owner and message.from_user.id != owner:
        return await message.answer("⛔ Access Denied.")
    await message.answer(
        "📋 <b>Commands:</b>\n\n"
        "/start - Register as owner / start\n"
        "/status - Live stats dashboard\n"
        "/target - View target scammer details\n"
        "/accounts - Account login status\n"
        "/notify on/off - Enable/disable round alerts\n"
        "/reset - Reset all counters\n"
        "/help - This menu\n"
    )


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if owner and message.from_user.id != owner:
        return await message.answer("⛔ Access Denied.")
    await message.answer(status_text(), disable_web_page_preview=True)


@dp.message(Command("target"))
async def cmd_target(message: types.Message):
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if owner and message.from_user.id != owner:
        return await message.answer("⛔ Access Denied.")
    extras = getattr(config, "EXTRA_TARGETS", [])
    txt = (f"🎯 <b>Scammer Info:</b>\n\n"
           f"Display Name: {STATE.get('target_display')}\n"
           f"Main Username: <code>{STATE.get('target')}</code>\n"
           f"Real Phone: <code>{STATE.get('scammer_phone')}</code>\n\n"
           f"<b>Extra Targets:</b>\n"
           f"{chr(10).join(['• ' + x for x in extras]) if extras else '—'}\n\n"
           f"<b>Summary:</b> Scammer extorted ₹3000 via UPI (Suraj Chanda / Assam), "
           f"sent family threats including 'Chod dalunga' (rape threat), "
           f"fakes Russia location but is from Assam.")
    await message.answer(txt, disable_web_page_preview=True)


@dp.message(Command("accounts"))
async def cmd_accounts(message: types.Message):
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if owner and message.from_user.id != owner:
        return await message.answer("⛔ Access Denied.")
    phones = getattr(config, "PHONE_NUMBERS", [])
    sessions_dir = "sessions"
    lines = ["👥 <b>Account Status:</b>\n"]
    for p in phones:
        fname = p.replace("+", "") + ".session"
        exists = os.path.exists(os.path.join(sessions_dir, fname))
        icon = "✅" if exists else "❌"
        lines.append(f"   {icon} <code>{p}</code>  {'Logged in' if exists else 'Need login'}")
    lines.append(f"\n   Total: {STATE.get('accounts_logged_in')} / {STATE.get('total_accounts')}")
    await message.answer("\n".join(lines))


@dp.message(Command("notify"))
async def cmd_notify(message: types.Message):
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if owner and message.from_user.id != owner:
        return await message.answer("⛔ Access Denied.")
    args = message.text.strip().split()
    if len(args) < 2 or args[1] not in ("on", "off"):
        cur = STATE.get("notify", True)
        return await message.answer(f"ℹ️ Notifications are currently <b>{'ON' if cur else 'OFF'}</b>.\nUse /notify on  or  /notify off")
    STATE["notify"] = (args[1] == "on")
    save_state(STATE)
    await message.answer(f"🔔 Notifications <b>{'ENABLED' if STATE['notify'] else 'DISABLED'}</b>.")


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if owner and message.from_user.id != owner:
        return await message.answer("⛔ Access Denied.")
    STATE["total_reports"] = 0
    STATE["rounds_completed"] = 0
    STATE["proofs_sent"] = 0
    STATE["start_time"] = datetime.now().isoformat()
    STATE["errors"] = []
    STATE["last_activity"] = "RESET: " + datetime.now().strftime("%H:%M:%S")
    save_state(STATE)
    await message.answer("♻️ Counters reset.")


async def notify_owner(msg):
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if not owner:
        return
    if not STATE.get("notify", True):
        return
    try:
        await bot.send_message(owner, msg, disable_web_page_preview=True)
    except Exception as e:
        log(f"notify_owner failed: {e}", "WARN")


async def bot_worker(q: asyncio.Queue):
    while True:
        try:
            item = await q.get()
            if not item:
                continue
            typ = item.get("type")
            data = item.get("data", {})

            if typ == "reports":
                n = data.get("reports", 0)
                round_num = data.get("round", 0)
                STATE["total_reports"] += n
                STATE["rounds_completed"] = round_num
                STATE["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_state(STATE)
                await notify_owner(
                    f"✅ <b>Round #{round_num} Complete</b>\n"
                    f"Reports sent this round: <b>{n}</b>\n"
                    f"Total reports so far: <b>{STATE['total_reports']}</b>"
                )

            elif typ == "accounts":
                STATE["accounts_logged_in"] = data.get("active", 0)
                STATE["total_accounts"] = data.get("total", len(getattr(config, "PHONE_NUMBERS", [])))
                save_state(STATE)

            elif typ == "proofs":
                STATE["proofs_sent"] += data.get("count", 0)
                STATE["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_state(STATE)
                await notify_owner(
                    f"📎 <b>Proofs Submitted</b>\n"
                    f"Proofs sent: <b>{data.get('count', 0)}</b> x {data.get('accounts', 0)} accounts\n"
                    f"Targets: {', '.join(getattr(config, 'REPORT_USERNAMES', []))}\n"
                    f"Total proofs so far: <b>{STATE['proofs_sent']}</b>"
                )

            elif typ == "error":
                err = data.get("msg", "unknown error")
                STATE.setdefault("errors", []).append(f"{datetime.now().strftime('%H:%M')} — {err}")
                if len(STATE["errors"]) > 20:
                    STATE["errors"] = STATE["errors"][-20:]
                save_state(STATE)

            elif typ == "status_request":
                chat_id = data.get("chat_id")
                if chat_id:
                    try:
                        await bot.send_message(chat_id, status_text(), disable_web_page_preview=True)
                    except Exception:
                        pass
        except Exception as e:
            log(f"bot_worker error: {e}", "ERROR")
        finally:
            try:
                q.task_done()
            except Exception:
                pass


async def run_bot_server(q: asyncio.Queue):
    log(f"Bot starting (token: {config.BOT_TOKEN[:10]}...)", "BOT")
    log(f"Bot ready. Send /start to your bot in Telegram to register as owner.", "BOT")
    worker_task = asyncio.create_task(bot_worker(q))
    try:
        await dp.start_polling(bot, handle_signals=False)
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        try:
            await bot.session.close()
        except Exception:
            pass


def run_in_background():
    """Returns (loop, queue). Caller should start loop."""
    q = asyncio.Queue()
    return q, run_bot_server(q)


if __name__ == "__main__":
    log("Launching Status Bot...", "STEP")
    log(f"Open Telegram, find your bot ({config.BOT_TOKEN.split(':')[0]}), send /start", "INFO")
    try:
        q_main = asyncio.Queue()
        asyncio.run(run_bot_server(q_main))
    except KeyboardInterrupt:
        log("Bot stopped.", "WARN")
        sys.exit(0)
    except Exception as e:
        log(f"Bot crashed: {e}", "ERROR")

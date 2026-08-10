import os
import sys
import time
import json
import asyncio
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties

from telethon import TelegramClient
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import InputReportReasonSpam, InputReportReasonViolence, \
    InputReportReasonPornography, InputReportReasonChildAbuse, \
    InputReportReasonCopyright, InputReportReasonFake, \
    InputReportReasonGeoIrrelevant, InputReportReasonIllegalDrugs, \
    InputReportReasonPersonalDetails
from telethon.errors import FloodWaitError, PhoneNumberUnoccupiedError, \
    SessionPasswordNeededError, PhoneCodeInvalidError, AuthBytesInvalidError

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
from health_server import start_health_server

if not getattr(config, "API_ID", 0) or not getattr(config, "API_HASH", ""):
    print("ERROR: API_ID/API_HASH missing. Set environment variables API_ID and API_HASH.")
    sys.exit(1)

SESSIONS_DIR = "sessions"
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

PROOFS_DIR = config.PROOFS_FOLDER
if not os.path.exists(PROOFS_DIR):
    os.makedirs(PROOFS_DIR)

REASON_MAP = {
    "spam": InputReportReasonSpam,
    "violence": InputReportReasonViolence,
    "pornography": InputReportReasonPornography,
    "child_abuse": InputReportReasonChildAbuse,
    "copyright": InputReportReasonCopyright,
    "fake": InputReportReasonFake,
    "geo_irrelevant": InputReportReasonGeoIrrelevant,
    "illegal_drugs": InputReportReasonIllegalDrugs,
    "personal_details": InputReportReasonPersonalDetails,
}

STATE_FILE = "master_state.json"


def default_state():
    return {
        "owner_chat_id": getattr(config, "BOT_OWNER_CHAT_ID", None),
        "clients": {},
        "otp_pending": {},
        "twofa_pending": {},
        "login_stage": None,
        "pending_phones": [],
        "reporting_running": False,
        "report_task": None,
        "total_reports": 0,
        "rounds_completed": 0,
        "proofs_sent": 0,
        "start_time": datetime.now().isoformat(),
        "last_round_at": None,
    }


STATE = default_state()
STATE_FILE_LOCK = threading.Lock()


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": Fore.WHITE, "SUCCESS": Fore.GREEN, "WARN": Fore.YELLOW,
              "ERROR": Fore.RED, "STEP": Fore.CYAN, "BOT": Fore.MAGENTA, "LOGIN": Fore.BLUE}
    color = colors.get(level, Fore.WHITE)
    print(f"{color}[{ts}] [{level}] {msg}{Style.RESET_ALL}")


def save_state():
    try:
        with STATE_FILE_LOCK:
            data = {
                "owner_chat_id": STATE["owner_chat_id"],
                "reporting_running": STATE["reporting_running"],
                "total_reports": STATE["total_reports"],
                "rounds_completed": STATE["rounds_completed"],
                "proofs_sent": STATE["proofs_sent"],
                "start_time": STATE["start_time"],
                "last_round_at": STATE["last_round_at"],
                "otp_pending": STATE.get("otp_pending") or {},
                "twofa_pending": STATE.get("twofa_pending") or {},
                "login_stage": STATE.get("login_stage"),
                "pending_phones": STATE.get("pending_phones") or [],
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    except Exception:
        pass


def load_state():
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k in STATE:
                STATE[k] = v
    except Exception:
        pass


load_state()


def get_uptime(start_iso=None):
    start = datetime.fromisoformat(start_iso or STATE.get("start_time") or datetime.now().isoformat())
    diff = datetime.now() - start
    d, rem = divmod(int(diff.total_seconds()), 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    return f"{d}d {h}h {m}m {s}s"


def get_detailed_report_message(reason_key):
    target = config.TARGET_USERNAME or str(config.TARGET_USER_ID)
    name = config.TARGET_DISPLAY_NAME or "Scammer"
    phone = getattr(config, "SCAMMER_REAL_PHONE", "+919395921365")
    base = (
        f"URGENT: {target} ({name}) = DANGEROUS SCAMMER + FAMILY THREATS. "
        f"HIS REAL TELEGRAM PHONE NUMBER: {phone}. "
        f"ALIAS: @nikalgarib / https://t.me/nikalgarib "
        f"CONFESSION IN OWN MSGS: 'Idhar scam ho rha', '2k Scam ktk gaya'. "
        f"UPI PAYMENT Rs 3,000 (Suraj Chanda, Assam Gramin Vikash Bank). "
        f"FURTHER DEMAND: 'aur 2k 3k fund krwa de'. "
        f"FAMILY THREATS: 'Tere family power dikhna mai dikhunga apna', "
        f"'Jo ukhad sakta ukhad lena', 'Chod dalunga' (RAPE THREAT), 'Gand. Mat gisa'. "
        f"GAALI: Madarchod, Mc.1, Re bsdk, Jhat, Salo, Dehadi nahi krta, Bahg. "
        f"LOCATION: BIO SHOWS FAKE RUSSIA, BUT HE ADMITS 'Assam sw hu' "
        f"+ UPI Bank + Apple Maps = ASSAM, INDIA. Phone {phone} also Indian. "
        f"ALIASES: @nikalgarib @NahhQT @diboed. "
        f"GROUPS: t.me/TEAMSTICKYONTOP + t.me/nikalgarib. "
        f"BANNERS: @Sexiestbanner @rarestbanner. PINNED: 15147444. "
        f"Evidence: 8+ screenshots + full video (IMG_3916.MP4) + UPI proof. "
        f"PLEASE PERMANENT BAN ALL ACCOUNTS + BLOCK PHONE {phone} + LEGAL ACTION."
    )
    specific = {
        "spam": f"SPAM/SCAM RING. {name} uses group TEAMSTICKYONTOP + alias @nikalgarib to scam via fake 'work/agent fees'. Phone {phone}. {base}",
        "fake": f"FAKE IDENTITY + FAKE LOCATION. {name} lies about Russia location (real Assam), multi-aliases: @tradaxin @nikalgarib @NahhQT @diboed. Phone {phone}. {base}",
        "violence": f"THREAT TO LIFE, FAMILY & RAPE. {name} threatens: 'Chod dalunga' (rape/assault), 'family power dikhunga', 'Jo ukhad sakta ukhad lena'. Victim terrified. Phone {phone}. {base}",
        "personal_details": f"VICTIM DOXXING + UPI LEAK. {name} demanded victim's location, used fake Russia location vs real phone {phone}. Suraj Chanda UPI leaked. @nikalgarib alias. {base}",
        "illegal_drugs": f"EXTORTION / ORGANIZED FINANCIAL FRAUD. Rs 3000 taken, 2-3k extra demand. Multi-account group scam. Phone {phone}. @nikalgarib + TEAMSTICKYONTOP. {base}",
        "geo_irrelevant": f"LOCATION FRAUD EXPOSED: {name} bio claims Russia but OWN MSG 'Assam sw hu' + UPI Bank (Assam Gramin Vikash) + phone {phone} = ASSAM, INDIA. Group t.me/nikalgarib. {base}",
    }
    return specific.get(reason_key, base)


async def is_owner(chat_id: int) -> bool:
    owner = STATE.get("owner_chat_id") or getattr(config, "BOT_OWNER_CHAT_ID", None)
    if owner is None:
        return False
    return int(owner) == int(chat_id)


async def notify_owner(text: str, bot: Bot, parse_mode: str = "HTML"):
    owner = STATE.get("owner_chat_id")
    if not owner:
        return
    try:
        await bot.send_message(owner, text, parse_mode=parse_mode, disable_web_page_preview=True)
    except Exception as e:
        log(f"notify_owner failed: {e}", "ERROR")


def is_image(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic"]


def is_video(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]


def is_audio(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".ogg", ".mp3", ".wav", ".amr", ".aac"]


def collect_proofs():
    out = []
    if not os.path.exists(PROOFS_DIR):
        return out
    for fn in sorted(os.listdir(PROOFS_DIR)):
        fp = os.path.join(PROOFS_DIR, fn)
        ext = os.path.splitext(fn)[1].lower()
        if os.path.isfile(fp) and ext in config.PROOF_EXTENSIONS:
            size_mb = os.path.getsize(fp) / (1024 * 1024)
            if size_mb > 2000:
                continue
            out.append(fp)
    return out


class BotFSM(StatesGroup):
    waiting_otp_phone = State()
    waiting_otp_code = State()
    waiting_2fa = State()
    waiting_owner_confirm = State()


if not getattr(config, "BOT_TOKEN", None):
    log("ERROR: BOT_TOKEN missing in config.py", "ERROR")
    sys.exit(1)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


CLIENT_LOCK = asyncio.Lock()


async def get_telethon_client(phone: str, create_new: bool = True):
    async with CLIENT_LOCK:
        if phone in STATE["clients"]:
            return STATE["clients"][phone]
        if not create_new:
            return None
        session_path = os.path.join(SESSIONS_DIR, phone.replace("+", ""))
        client = TelegramClient(session_path, config.API_ID, config.API_HASH)
        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                log(f"Session restored: {phone} -> @{me.username}", "SUCCESS")
                STATE["clients"][phone] = client
                return client
            else:
                return client
        except Exception as e:
            log(f"Session connect failed for {phone}: {e}", "ERROR")
            return client


async def disconnect_all_clients():
    for phone, client in list(STATE["clients"].items()):
        try:
            await client.disconnect()
            log(f"Disconnected {phone}", "INFO")
        except Exception:
            pass
    STATE["clients"] = {}


def session_exists(phone: str) -> bool:
    path = os.path.join(SESSIONS_DIR, phone.replace("+", "") + ".session")
    return os.path.exists(path)


async def report_one_target(client, phone_display, entity, reasons, label):
    total = 0
    entity_desc = f"@{entity.username}" if getattr(entity, "username", None) else f"ID {entity.id}"
    for reason_key in reasons:
        reason_cls = REASON_MAP.get(reason_key)
        if not reason_cls:
            continue
        try:
            msg = get_detailed_report_message(reason_key)
            log(f"[{phone_display}] {label} {entity_desc} -> {reason_key}", "STEP")
            result = await client(ReportPeerRequest(peer=entity, reason=reason_cls(message=msg)))
            if result:
                log(f"[{phone_display}]   ✓ OK ({reason_key})", "SUCCESS")
                total += 1
            else:
                log(f"[{phone_display}]   ⚠ empty ({reason_key})", "WARN")
            await asyncio.sleep(4)
        except FloodWaitError as e:
            log(f"[{phone_display}] FloodWait {e.seconds}s on {label}", "WARN")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            log(f"[{phone_display}]   ✗ failed ({reason_key}): {e}", "ERROR")
    return total


async def get_target_entity(client):
    try:
        if config.TARGET_USER_ID:
            return await client.get_entity(config.TARGET_USER_ID)
    except Exception:
        pass
    try:
        if config.TARGET_USERNAME:
            return await client.get_entity(config.TARGET_USERNAME)
    except Exception:
        pass
    return None


async def do_report_round(reasons, bot_ref):
    log("Starting report round...", "STEP")
    targets_reported = set()
    total_this_round = 0

    clients = list(STATE["clients"].values())
    if not clients:
        log("No logged in clients for round", "ERROR")
        await notify_owner("❌ <b>No logged-in accounts!</b> Run /login first.", bot_ref)
        return 0

    main_entity = None
    for c in clients:
        main_entity = await get_target_entity(c)
        if main_entity:
            break

    if not main_entity:
        log("Target entity could not be resolved", "ERROR")
        await notify_owner("❌ Could not resolve target. Check TARGET_USERNAME in config.py.", bot_ref)
        return 0

    for client_idx, client in enumerate(clients):
        me = await client.get_me()
        phone_disp = f"+{me.phone}" if me.phone else f"@{me.username}"

        main_reports = await report_one_target(client, phone_disp, main_entity, reasons, "MAIN")
        total_this_round += main_reports

        extras = getattr(config, "EXTRA_TARGETS", [])
        for eid in extras:
            try:
                extra_ent = await client.get_entity(eid)
                await asyncio.sleep(3)
                er = await report_one_target(client, phone_disp, extra_ent, reasons, f"EX:{eid}")
                total_this_round += er
            except Exception:
                pass

        if client_idx < len(clients) - 1:
            log(f"Sleeping {config.DELAY_BETWEEN_ACCOUNTS}s...", "INFO")
            await asyncio.sleep(config.DELAY_BETWEEN_ACCOUNTS)

    STATE["total_reports"] += total_this_round
    STATE["rounds_completed"] += 1
    STATE["last_round_at"] = datetime.now().isoformat()
    save_state()
    log(f"Round #{STATE['rounds_completed']} DONE. Reports this round: {total_this_round}. Total: {STATE['total_reports']}", "SUCCESS")
    return total_this_round


async def send_proofs_all(bot_ref):
    proofs = collect_proofs()
    if not proofs:
        await notify_owner("⚠️ No proof files found in <code>proofs/</code> folder.", bot_ref)
        return 0

    clients = list(STATE["clients"].values())
    if not clients:
        await notify_owner("❌ No logged-in accounts. Use /login first.", bot_ref)
        return 0

    report_users = getattr(config, "REPORT_USERNAMES", ["@Notoscam", "@Support", "@Telegram"])
    summary = config.REPORT_MESSAGE_SUMMARY.format(
        target=config.TARGET_USERNAME or str(config.TARGET_USER_ID),
        display_name=config.TARGET_DISPLAY_NAME
    )

    total_sent = 0
    for client in clients:
        me = await client.get_me()
        disp = f"+{me.phone}" if me.phone else f"@{me.username}"
        for ru in report_users:
            try:
                ent = await client.get_entity(ru)
                try:
                    await client.send_message(ent, summary)
                    await asyncio.sleep(2)
                except Exception:
                    pass

                image_proofs = [p for p in proofs if is_image(p)]
                other_proofs = [p for p in proofs if not is_image(p)]

                if len(image_proofs) >= 1:
                    MAX_ALBUM = 10
                    for ci in range(0, len(image_proofs), MAX_ALBUM):
                        chunk = image_proofs[ci:ci + MAX_ALBUM]
                        try:
                            if len(chunk) == 1:
                                await client.send_file(ent, chunk[0], caption=f"Proof vs {config.TARGET_USERNAME} — Scam+Threats"[:1000])
                            else:
                                caps = [f"Proof #{ci+i+1} vs @tradaxin — Scam / Threats / Family Danger" for i in range(len(chunk))]
                                await client.send_file(ent, chunk, caption=caps[-1][:1000])
                            total_sent += len(chunk)
                            await asyncio.sleep(5)
                        except FloodWaitError as e:
                            await asyncio.sleep(e.seconds + 10)
                        except Exception as e:
                            log(f"Album failed, fallback individual: {e}", "WARN")
                            for i, p in enumerate(chunk):
                                try:
                                    await client.send_file(ent, p, caption=f"Proof #{ci+i+1} vs @tradaxin"[:1000])
                                    total_sent += 1
                                    await asyncio.sleep(3)
                                except Exception:
                                    pass

                for idx, p in enumerate(other_proofs):
                    fname = os.path.basename(p)
                    overall_idx = len(image_proofs) + idx + 1
                    try:
                        if is_video(p):
                            await client.send_file(ent, p, supports_streaming=True, caption=f"Video Proof #{overall_idx} vs @tradaxin"[:1000])
                        elif is_audio(p):
                            await client.send_file(ent, p, caption=f"Audio Proof #{overall_idx}"[:1000])
                        else:
                            await client.send_file(ent, p, force_document=True, caption=f"Proof #{overall_idx}: {fname}"[:1000])
                        total_sent += 1
                        await asyncio.sleep(4)
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 10)
                    except Exception as e:
                        log(f"Failed {fname}: {e}", "ERROR")

                log(f"[{disp}] -> {ru}: proofs submitted", "SUCCESS")
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as e:
                log(f"Target {ru} failed: {e}", "WARN")

    STATE["proofs_sent"] += total_sent
    save_state()
    log(f"Total proof units sent: {total_sent}", "SUCCESS")
    await notify_owner(
        f"📎 <b>Proofs Submitted</b>\n\n"
        f"Proof files: <b>{len(proofs)}</b>\n"
        f"Accounts used: <b>{len(clients)}</b>\n"
        f"Targets: {', '.join(report_users)}\n"
        f"Total items delivered: <b>{total_sent}</b>\n"
        f"All-time proofs: {STATE['proofs_sent']}",
        bot_ref
    )
    return total_sent


async def report_loop(bot_ref):
    reasons = [r for r in config.SELECTED_REASONS if r in REASON_MAP]
    if not reasons:
        reasons = ["spam", "fake", "violence"]

    while STATE["reporting_running"]:
        STATE["last_round_at"] = datetime.now().isoformat()
        reports = await do_report_round(reasons, bot_ref)
        await notify_owner(
            f"✅ <b>Round #{STATE['rounds_completed']} Complete</b>\n\n"
            f"Reports (this round): <b>{reports}</b>\n"
            f"Total reports: <b>{STATE['total_reports']}</b>\n"
            f"Rounds: {STATE['rounds_completed']}\n"
            f"Accounts: {len(STATE['clients'])}\n\n"
            f"Next round in {config.DELAY_BETWEEN_ROUNDS}s...",
            bot_ref
        )
        delay = config.DELAY_BETWEEN_ROUNDS
        while STATE["reporting_running"] and delay > 0:
            step = min(delay, 10)
            await asyncio.sleep(step)
            delay -= step


async def start_reports_internal(bot_ref):
    if STATE["reporting_running"]:
        return False, "already_running"
    if len(STATE["clients"]) == 0:
        return False, "no_clients"
    STATE["reporting_running"] = True
    save_state()
    task = asyncio.create_task(report_loop(bot_ref))
    STATE["report_task"] = task
    log("Reporting loop STARTED", "SUCCESS")
    return True, None


@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    cid = msg.chat.id
    existing_owner = STATE.get("owner_chat_id")
    if existing_owner is None:
        STATE["owner_chat_id"] = cid
        save_state()
        await msg.answer(
            "🎉 <b>Owner Registered!</b>\n\n"
            f"Your chat ID: <code>{cid}</code>\n\n"
            "Setup complete. Use these commands:\n"
            "/login - Add & login Telegram accounts (phone + OTP)\n"
            "/accounts - View logged in accounts\n"
            "/start_reports - Start continuous reporting loop\n"
            "/stop_reports - Stop reporting loop\n"
            "/send_proofs - Send ALL proof files to @Notoscam/@Support/@Telegram\n"
            "/status - Live dashboard\n"
            "/target - Scammer details\n"
            "/logout_all - Logout ALL accounts\n"
            "/help - This menu\n\n"
            "⚡ Start with <b>/login</b> to add accounts."
        )
        log(f"Owner registered: chat_id={cid}", "BOT")
    elif int(existing_owner) == int(cid):
        await msg.answer("👋 Welcome back owner! Use /help for menu. Use <b>/login</b> to add accounts.")
    else:
        await msg.answer("⛔ Access Denied.")
        log(f"Unauthorized /start from {cid}", "WARN")


@dp.message(Command("help"))
async def cmd_help(msg: types.Message):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    await msg.answer(
        "📋 <b>Master Bot Commands</b>\n\n"
        "<b>Setup:</b>\n"
        "/login — Login new Telegram account(s)\n"
        "/accounts — Show logged-in status\n"
        "/logout_all — Logout & disconnect ALL accounts\n\n"
        "<b>Operations:</b>\n"
        "/start_reports — 🔁 Start infinite reporting loop\n"
        "/stop_reports — ⏹️ Stop reporting loop\n"
        "/send_proofs — 📎 Send proof pics/video to @Notoscam/@Support/@Telegram\n\n"
        "<b>Info:</b>\n"
        "/status — Live dashboard (total reports, uptime, etc)\n"
        "/target — Scammer profile (IDs, phone, UPI, threats)\n\n"
        "<b>Flow:</b> <i>/login → /accounts → /send_proofs → /start_reports → /status</i>"
    )


@dp.message(Command("login"))
async def cmd_login(msg: types.Message, state: FSMContext):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    await state.set_state(BotFSM.waiting_otp_phone)
    STATE["login_stage"] = "waiting_phone"
    STATE["pending_phones"] = []
    save_state()
    await msg.answer(
        "📱 <b>Login Account</b>\n\n"
        "Send me the phone number with country code.\n"
        "Example: <code>+919876543210</code>\n\n"
        "Or send MULTIPLE numbers separated by newlines:\n"
        "<code>+919876543210\n+919123456789</code>\n\n"
        "After you receive OTP, you can send just the code (example: <code>44196</code>)\n"
        "OR <code>PHONE:OTP</code>\n\n"
        "/cancel to abort."
    )


@dp.message(Command("cancel"))
async def cmd_cancel(msg: types.Message, state: FSMContext):
    await state.clear()
    STATE["login_stage"] = None
    STATE["pending_phones"] = []
    save_state()
    await msg.answer("♻️ Cancelled.")


@dp.message()
async def fallback_login_inputs(msg: types.Message, state: FSMContext):
    if not await is_owner(msg.chat.id):
        return
    text = (msg.text or "").strip()
    if not text or text.startswith("/"):
        return
    try:
        cur_state = await state.get_state()
    except Exception:
        cur_state = None
    if cur_state in (
        getattr(BotFSM.waiting_otp_phone, "state", None),
        getattr(BotFSM.waiting_otp_code, "state", None),
        getattr(BotFSM.waiting_2fa, "state", None),
    ):
        return
    stage = STATE.get("login_stage")
    otp_pending = STATE.get("otp_pending") or {}
    twofa_pending = STATE.get("twofa_pending") or {}

    if stage is None:
        if twofa_pending:
            stage = "waiting_2fa"
        elif otp_pending:
            stage = "waiting_otp"

    if stage is None:
        return

    if stage == "waiting_phone":
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        valid = []
        for ln in lines:
            ln2 = ln.strip().replace(" ", "")
            if ln2.startswith("+") and len(ln2) >= 10 and ln2[1:].isdigit():
                valid.append(ln2)
        if not valid:
            return await msg.answer("❌ Phone format galat. Example: <code>+91XXXXXXXXXX</code>")

        pending = []
        for phone in valid:
            client = await get_telethon_client(phone, create_new=True)
            try:
                if await client.is_user_authorized():
                    continue
                sent = await client.send_code_request(phone)
                STATE["otp_pending"][phone] = {"phone_code_hash": sent.phone_code_hash, "client_ref": True}
                pending.append(phone)
            except PhoneNumberUnoccupiedError:
                await msg.answer(f"❌ Phone <code>{phone}</code> not registered on Telegram.")
                try:
                    await client.disconnect()
                except Exception:
                    pass
                STATE["clients"].pop(phone, None)
                STATE["otp_pending"].pop(phone, None)
            except FloodWaitError as e:
                await msg.answer(f"⏱️ FloodWait on <code>{phone}</code>: {e.seconds}s. Try later.")
                STATE["clients"].pop(phone, None)
                STATE["otp_pending"].pop(phone, None)
            except Exception as e:
                await msg.answer(f"❌ Error for {phone}: {e}")
                STATE["clients"].pop(phone, None)
                STATE["otp_pending"].pop(phone, None)

        STATE["pending_phones"] = pending
        STATE["login_stage"] = "waiting_otp" if pending else None
        save_state()
        if not pending:
            return await msg.answer("✅ Ye phone already logged in lag rahe hain. /accounts check karo.")
        if len(pending) == 1:
            return await msg.answer(f"🔐 OTP aa gaya to sirf code bhejo (example: <code>44196</code>)\nPhone: <code>{pending[0]}</code>")
        return await msg.answer("🔐 OTP aa gaya to sirf code bhejo (example: <code>44196</code>) ya <code>PHONE:OTP</code>")

    if stage == "waiting_otp":
        raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        pairs = {}
        for ln in raw_lines:
            if ":" in ln:
                ph, val = ln.split(":", 1)
                ph = ph.strip().replace(" ", "")
                val = val.strip()
                if ph and val:
                    pairs[ph] = val
        if not pairs:
            otp = "".join(ch for ch in text if ch.isdigit())
            if not otp:
                return
            phone = None
            if STATE.get("pending_phones"):
                phone = STATE["pending_phones"][0]
            elif otp_pending:
                phone = list(otp_pending.keys())[0]
            if not phone:
                return
            pairs = {phone: otp}

        handled_any = False
        for phone, otp in pairs.items():
            if phone not in otp_pending:
                continue
            if phone not in STATE.get("clients", {}):
                await get_telethon_client(phone, create_new=True)
            client = STATE.get("clients", {}).get(phone)
            if not client:
                continue
            try:
                await msg.answer("⏳ OTP check ho raha hai...")
                phone_code_hash = otp_pending.get(phone, {}).get("phone_code_hash")
                if phone_code_hash:
                    await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
                else:
                    await client.sign_in(phone, otp)
                me = await client.get_me()
                STATE["otp_pending"].pop(phone, None)
                if phone in (STATE.get("pending_phones") or []):
                    STATE["pending_phones"] = [p for p in STATE["pending_phones"] if p != phone]
                handled_any = True
                await msg.answer(f"✅ <b>Logged In</b>\nPhone: <code>{phone}</code>\nUsername: @{me.username}\nID: <code>{me.id}</code>")
            except SessionPasswordNeededError:
                STATE["twofa_pending"][phone] = True
                STATE["login_stage"] = "waiting_2fa"
                save_state()
                handled_any = True
                await msg.answer(f"🔐 2FA required.\nSend password only (example: <code>mypassword</code>)\nOR <code>{phone}:PASSWORD</code>")
            except PhoneCodeInvalidError:
                handled_any = True
                await msg.answer("❌ OTP galat ya expire. /login karke fresh OTP lo.")
            except FloodWaitError as e:
                handled_any = True
                await msg.answer(f"⏱️ FloodWait: {e.seconds}s. Try later.")
            except Exception as e:
                handled_any = True
                await msg.answer(f"❌ Login failed <code>{phone}</code>: {e}")

        if handled_any:
            if not STATE.get("otp_pending") and not STATE.get("twofa_pending"):
                STATE["login_stage"] = None
                STATE["pending_phones"] = []
            save_state()
            if getattr(config, "AUTO_START_REPORTS_AFTER_LOGIN", False) and not STATE.get("otp_pending") and not STATE.get("twofa_pending"):
                started, _ = await start_reports_internal(bot)
                if started:
                    await msg.answer("🚀 Auto-started reporting. Use /status for live stats. /stop_reports to halt.")
        return

    if stage == "waiting_2fa":
        raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        pairs = {}
        for ln in raw_lines:
            if ":" in ln:
                ph, val = ln.split(":", 1)
                ph = ph.strip().replace(" ", "")
                val = val.strip()
                if ph and val:
                    pairs[ph] = val
        if not pairs:
            pwd = text
            phone = None
            if twofa_pending:
                phone = list(twofa_pending.keys())[0]
            if not phone:
                return
            pairs = {phone: pwd}

        handled_any = False
        for phone, pwd in pairs.items():
            if phone not in twofa_pending:
                continue
            if phone not in STATE.get("clients", {}):
                await get_telethon_client(phone, create_new=True)
            client = STATE.get("clients", {}).get(phone)
            if not client:
                continue
            try:
                await msg.answer("⏳ 2FA check ho raha hai...")
                await client.sign_in(password=pwd)
                me = await client.get_me()
                STATE["twofa_pending"].pop(phone, None)
                STATE["otp_pending"].pop(phone, None)
                handled_any = True
                await msg.answer(f"✅ 2FA OK: <code>{phone}</code> → @{me.username}")
            except Exception as e:
                handled_any = True
                await msg.answer(f"❌ 2FA failed <code>{phone}</code>: {e}")

        if handled_any:
            if not STATE.get("otp_pending") and not STATE.get("twofa_pending"):
                STATE["login_stage"] = None
                STATE["pending_phones"] = []
            save_state()
            if getattr(config, "AUTO_START_REPORTS_AFTER_LOGIN", False) and not STATE.get("otp_pending") and not STATE.get("twofa_pending"):
                started, _ = await start_reports_internal(bot)
                if started:
                    await msg.answer("🚀 Auto-started reporting. Use /status for live stats. /stop_reports to halt.")
        return


@dp.message(BotFSM.waiting_otp_phone)
async def otp_phone_received(msg: types.Message, state: FSMContext):
    raw = msg.text.strip()
    if not raw:
        return await msg.answer("❌ Please send a phone number (e.g. +919876543210)")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    valid = []
    for ln in lines:
        ln2 = ln.strip().replace(" ", "")
        if ln2.startswith("+") and len(ln2) >= 10 and ln2[1:].isdigit():
            valid.append(ln2)
    if not valid:
        return await msg.answer("❌ Invalid format. Send +91XXXXXXXXXX")
    pending = []
    for phone in valid:
        client = await get_telethon_client(phone, create_new=True)
        if phone in STATE["clients"] and await client.is_user_authorized():
            continue
        try:
            if await client.is_user_authorized():
                me = await client.get_me()
                STATE["clients"][phone] = client
                continue
            log(f"Sending code request to {phone}", "LOGIN")
            sent = await client.send_code_request(phone)
            STATE["otp_pending"][phone] = {"phone_code_hash": sent.phone_code_hash, "client_ref": True}
            pending.append(phone)
        except PhoneNumberUnoccupiedError:
            await msg.answer(f"❌ Phone <code>{phone}</code> not registered on Telegram.")
            try:
                await client.disconnect()
            except Exception:
                pass
            STATE["clients"].pop(phone, None)
            STATE["otp_pending"].pop(phone, None)
            continue
        except FloodWaitError as e:
            await msg.answer(f"⏱️ FloodWait on <code>{phone}</code>: {e.seconds}s. Try later.")
            STATE["clients"].pop(phone, None)
            STATE["otp_pending"].pop(phone, None)
            continue
        except Exception as e:
            await msg.answer(f"❌ Error for {phone}: {e}")
            STATE["clients"].pop(phone, None)
            STATE["otp_pending"].pop(phone, None)
            continue

    await state.update_data(pending_phones=pending)
    if not pending:
        await state.clear()
        await msg.answer("✅ All provided accounts already logged in! Use /accounts to verify.")
        if getattr(config, "AUTO_START_REPORTS_AFTER_LOGIN", False):
            started, _ = await start_reports_internal(bot)
            if started:
                await msg.answer("🚀 Auto-started reporting. Use /status for live stats. /stop_reports to halt.")
        return

    await state.set_state(BotFSM.waiting_otp_code)
    first_phone = pending[0]
    await msg.answer(
        f"🔐 <b>Enter OTP</b>\n\n"
        f"Pending phones: {len(pending)}\n"
        f"<code>{chr(10).join(pending)}</code>\n\n"
        f"First phone: <code>{first_phone}</code>\n\n"
        f"Reply with OTP code. Format:\n"
        f"<code>PHONE:OTP</code> (or send OTPs line by line)\n\n"
        f"Example:\n"
        f"<code>{first_phone}:12345</code>\n\n"
        f"Note: OTP comes in TELEGRAM APP (not SMS)."
    )


@dp.message(BotFSM.waiting_otp_code)
async def otp_code_received(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    pending_phones = data.get("pending_phones") or list(STATE["otp_pending"].keys())
    if not pending_phones:
        await state.clear()
        return await msg.answer("❌ No pending phones.")
    raw_lines = [ln.strip() for ln in msg.text.strip().splitlines() if ln.strip()]
    codes = {}
    for ln in raw_lines:
        if ":" in ln:
            phone, otp = ln.split(":", 1)
            codes[phone.strip().replace(" ", "")] = otp.strip()
        else:
            otp = "".join(ch for ch in ln if ch.isdigit())
            for ph in pending_phones:
                if ph not in codes:
                    codes[ph] = otp
                    break
    if not codes:
        return await msg.answer("❌ OTP not detected. Send in format <code>+91...:OTP</code>")

    remaining = []
    need_2fa = []
    for phone, otp in codes.items():
        if phone not in STATE["clients"]:
            continue
        client = STATE["clients"][phone]
        try:
            phone_code_hash = None
            try:
                phone_code_hash = (STATE.get("otp_pending") or {}).get(phone, {}).get("phone_code_hash")
            except Exception:
                phone_code_hash = None
            if phone_code_hash:
                await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
            else:
                await client.sign_in(phone, otp)
            me = await client.get_me()
            log(f"Login OK: {phone} -> @{me.username} ({me.first_name})", "SUCCESS")
            STATE["otp_pending"].pop(phone, None)
            await msg.answer(
                f"✅ <b>Logged In</b>\n\n"
                f"Phone: <code>{phone}</code>\n"
                f"Username: @{me.username}\n"
                f"Name: {me.first_name} {me.last_name or ''}\n"
                f"ID: <code>{me.id}</code>"
            )
        except SessionPasswordNeededError:
            STATE["twofa_pending"][phone] = True
            need_2fa.append(phone)
        except PhoneCodeInvalidError:
            remaining.append(phone)
            await msg.answer(f"❌ Wrong OTP for <code>{phone}</code>. Send correct OTP. Re-try:")
        except FloodWaitError as e:
            await msg.answer(f"⏱️ FloodWait {phone}: {e.seconds}s. Try later.")
            STATE["otp_pending"].pop(phone, None)
        except Exception as e:
            await msg.answer(f"❌ Login failed {phone}: {e}")
            STATE["otp_pending"].pop(phone, None)
    still_pending = [p for p in pending_phones if p in STATE["otp_pending"] or p in need_2fa]
    if need_2fa:
        await state.update_data(pending_phones=still_pending, twofa_phones=need_2fa)
        await state.set_state(BotFSM.waiting_2fa)
        await msg.answer(
            f"🔐 <b>2FA Password Required</b>\n\n"
            f"These accounts have 2-Factor Authentication enabled:\n"
            f"<code>{chr(10).join(need_2fa)}</code>\n\n"
            f"Reply with: <code>PHONE:PASSWORD</code>\n"
            f"Example: <code>{need_2fa[0]}:MyPassword123</code>"
        )
        return
    if still_pending:
        await state.update_data(pending_phones=still_pending)
        return
    await state.clear()
    active = len(STATE["clients"])
    total = len(getattr(config, "PHONE_NUMBERS", []))
    save_state()
    await msg.answer(
        f"✅ <b>Login Process Complete!</b>\n"
        f"Active sessions: <b>{active}</b>\n\n"
        "Next steps:\n"
        "• /accounts — verify all sessions\n"
        "• /send_proofs — upload proof files to Telegram team\n"
        "• /start_reports — begin the continuous reporting loop"
    )
    if getattr(config, "AUTO_START_REPORTS_AFTER_LOGIN", False):
        started, reason = await start_reports_internal(bot)
        if started:
            await msg.answer("🚀 Auto-started reporting. Use /status for live stats. /stop_reports to halt.")
        elif reason == "already_running":
            await msg.answer("ℹ️ Reporting already running. Use /status.")


@dp.message(BotFSM.waiting_2fa)
async def twofa_received(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    twofa_phones = data.get("twofa_phones") or list(STATE["twofa_pending"].keys())
    lines = [ln.strip() for ln in msg.text.strip().splitlines() if ln.strip()]
    passwords = {}
    for ln in lines:
        if ":" in ln:
            ph, pwd = ln.split(":", 1)
            passwords[ph.strip().replace(" ", "")] = pwd.strip()
    if not passwords:
        return await msg.answer("❌ Send <code>PHONE:PASSWORD</code>")
    for phone, pwd in passwords.items():
        if phone not in STATE["clients"]:
            continue
        client = STATE["clients"][phone]
        try:
            await client.sign_in(password=pwd)
            me = await client.get_me()
            log(f"2FA Login OK: {phone} -> @{me.username}", "SUCCESS")
            STATE["twofa_pending"].pop(phone, None)
            STATE["otp_pending"].pop(phone, None)
            await msg.answer(f"✅ 2FA OK: <code>{phone}</code> → @{me.username}")
        except Exception as e:
            await msg.answer(f"❌ 2FA failed {phone}: {e}")
    remaining = [p for p in twofa_phones if p in STATE["twofa_pending"]]
    if remaining:
        await state.update_data(twofa_phones=remaining)
        return
    active = len(STATE["clients"])
    save_state()
    await state.clear()
    await msg.answer(
        f"✅ All logins complete!\n\n"
        f"Active: <b>{active}</b>\n\n"
        "Next: /send_proofs → /start_reports → /status"
    )
    if getattr(config, "AUTO_START_REPORTS_AFTER_LOGIN", False):
        started, reason = await start_reports_internal(bot)
        if started:
            await msg.answer("🚀 Auto-started reporting. Use /status for live stats. /stop_reports to halt.")
        elif reason == "already_running":
            await msg.answer("ℹ️ Reporting already running. Use /status.")


@dp.message(Command("accounts"))
async def cmd_accounts(msg: types.Message):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    lines = ["👥 <b>Account Status</b>\n"]
    active_phones = []
    for phone in list(STATE["clients"].keys()):
        client = STATE["clients"][phone]
        try:
            me = await client.get_me()
            icon = "✅"
            active_phones.append(phone)
            lines.append(f"   {icon} <code>{phone}</code>  →  @{me.username} ({me.first_name})")
        except Exception:
            lines.append(f"   ⚠️ <code>{phone}</code>  →  disconnected")
    config_phones = getattr(config, "PHONE_NUMBERS", [])
    for ph in config_phones:
        if ph not in active_phones:
            exists = session_exists(ph)
            lines.append(f"   {'💤' if exists else '❌'} <code>{ph}</code>  →  {'session exists but not loaded' if exists else 'needs login (/login)'}")
    total_count = len(set(list(STATE["clients"].keys()) + config_phones))
    lines.append(f"\n   Active sessions: <b>{len(active_phones)} / {total_count}</b>")
    await msg.answer("\n".join(lines))


@dp.message(Command("status"))
async def cmd_status(msg: types.Message):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    extras = getattr(config, "EXTRA_TARGETS", [])
    last = STATE.get("last_round_at")
    if last:
        try:
            dt = datetime.fromisoformat(last)
            last_str = dt.strftime("%H:%M:%S %d %b")
        except Exception:
            last_str = str(last)
    else:
        last_str = "—"
    lines = [
        "📊 <b>Live Dashboard</b>\n",
        f"🎯 <b>Target:</b> {config.TARGET_DISPLAY_NAME}",
        f"   Username: <code>{config.TARGET_USERNAME}</code>",
        f"   Scammer phone: <code>{getattr(config, 'SCAMMER_REAL_PHONE', 'N/A')}</code>\n",
        f"📈 <b>Progress:</b>",
        f"   • Total reports: <b>{STATE['total_reports']}</b>",
        f"   • Rounds done: <b>{STATE['rounds_completed']}</b>",
        f"   • Proofs submitted: <b>{STATE['proofs_sent']}</b>\n",
        f"👥 <b>Accounts:</b>",
        f"   • Active: <b>{len(STATE['clients'])}</b> / {len(getattr(config,'PHONE_NUMBERS',[]))}\n",
        f"🎯 <b>Extra Targets ({len(extras)}):</b>",
    ]
    for e in extras:
        lines.append(f"   • {e}")
    lines += [
        f"\n⏱️ <b>Uptime:</b> {get_uptime()}",
        f"🕐 <b>Last round:</b> {last_str}",
        f"🔁 <b>Loop running:</b> {'✅ YES' if STATE['reporting_running'] else '⏸️ NO'}",
    ]
    await msg.answer("\n".join(lines), disable_web_page_preview=True)


@dp.message(Command("target"))
async def cmd_target(msg: types.Message):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    extras = getattr(config, "EXTRA_TARGETS", [])
    txt = (
        "🎯 <b>Scammer Profile</b>\n\n"
        f"Display: {config.TARGET_DISPLAY_NAME}\n"
        f"Main username: <code>{config.TARGET_USERNAME}</code>\n"
        f"Real phone: <code>{getattr(config, 'SCAMMER_REAL_PHONE','N/A')}</code>\n\n"
        f"<b>All IDs to Ban:</b>\n"
        f"• {config.TARGET_USERNAME} (main)\n"
        + "\n".join([f"• {x}" for x in extras])
        + "\n\n<b>Crimes & Evidence:</b>\n"
          "• ₹3,000 UPI payment (Suraj Chanda / Assam Gramin Vikash Bank)\n"
          "'2k 3k fund aur chahiye' further extortion\n"
          "Scammer's own confession: 'Idhar scam ho rha', '2k Scam ktk gaya'\n"
          "Rape/Assault threat: 'Chod dalunga'\n"
          "Family threat: 'Tere family power dikhunga'\n"
          "Abuse: Madarchod, bsdk, jhat, Mc.1, salo\n"
          "Location lie: Russia bio vs OWN MSG 'Assam sw hu' + UPI from Assam\n"
          "Fake groups: TEAMSTICKYONTOP, nikalgarib\n"
          "Banner aliases: @Sexiestbanner @rarestbanner\n"
    )
    await msg.answer(txt, disable_web_page_preview=True)


@dp.message(Command("start_reports"))
async def cmd_start_reports(msg: types.Message):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    started, reason = await start_reports_internal(bot)
    if not started and reason == "already_running":
        return await msg.answer("⚠️ Reporting already running!")
    if not started and reason == "no_clients":
        return await msg.answer("❌ No logged-in accounts. Run /login first.")
    await msg.answer(
        "🚀 <b>Reporting Loop STARTED</b>\n\n"
        f"Accounts: <b>{len(STATE['clients'])}</b>\n"
        f"Delay between accounts: <b>{config.DELAY_BETWEEN_ACCOUNTS}s</b>\n"
        f"Delay between rounds: <b>{config.DELAY_BETWEEN_ROUNDS}s</b>\n"
        f"Reasons: {', '.join(config.SELECTED_REASONS)}\n\n"
        "You will get notification after every round.\n"
        "/status for live stats. /stop_reports to halt."
    )


@dp.message(Command("stop_reports"))
async def cmd_stop_reports(msg: types.Message):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    if not STATE["reporting_running"]:
        return await msg.answer("ℹ️ Reporting was not running.")
    STATE["reporting_running"] = False
    t = STATE.get("report_task")
    if t and not t.done():
        t.cancel()
        try:
            await t
        except Exception:
            pass
    STATE["report_task"] = None
    save_state()
    log("Reporting loop STOPPED", "WARN")
    await msg.answer(
        f"⏹️ <b>Reporting Stopped</b>\n\n"
        f"Total rounds: {STATE['rounds_completed']}\n"
        f"Total reports: {STATE['total_reports']}\n"
        "/start_reports to resume."
    )


@dp.message(Command("send_proofs"))
async def cmd_send_proofs(msg: types.Message):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    if len(STATE["clients"]) == 0:
        return await msg.answer("❌ No logged-in accounts. Run /login first.")
    proofs = collect_proofs()
    await msg.answer(
        f"📎 <b>Sending Proofs</b>\n\n"
        f"Files found: <b>{len(proofs)}</b>\n"
        f"Accounts: <b>{len(STATE['clients'])}</b>\n"
        f"Targets: {', '.join(getattr(config, 'REPORT_USERNAMES', []))}\n\n"
        "Please wait — uploading takes time...",
    )
    count = await send_proofs_all(bot)
    await msg.answer(f"✅ Proofs done. Files delivered this run: <b>{count}</b>. All-time: {STATE['proofs_sent']}")


@dp.message(Command("logout_all"))
async def cmd_logout_all(msg: types.Message):
    if not await is_owner(msg.chat.id):
        return await msg.answer("⛔ Access Denied.")
    STATE["reporting_running"] = False
    t = STATE.get("report_task")
    if t and not t.done():
        t.cancel()
        try:
            await t
        except Exception:
            pass
    await disconnect_all_clients()
    STATE["otp_pending"] = {}
    STATE["twofa_pending"] = {}
    save_state()
    await msg.answer("👋 <b>All accounts logged out & disconnected.</b>\nRun /login again to start.")


async def on_startup():
    log("=== MASTER BOT STARTING ===", "BOT")
    log(f"API_ID: {config.API_ID}  |  API_HASH: {config.API_HASH[:8]}...", "INFO")
    log(f"Bot token: {config.BOT_TOKEN[:10]}...", "BOT")
    log(f"Target: {config.TARGET_USERNAME} / {getattr(config,'SCAMMER_REAL_PHONE','')}", "INFO")
    existing_sessions = 0
    for phone in getattr(config, "PHONE_NUMBERS", []):
        if session_exists(phone):
            try:
                await get_telethon_client(phone, create_new=True)
                if phone in STATE["clients"]:
                    existing_sessions += 1
            except Exception:
                pass
    log(f"Auto-restored sessions: {existing_sessions}", "SUCCESS")
    owner = STATE.get("owner_chat_id")
    if owner:
        try:
            await bot.send_message(
                owner,
                f"🟢 <b>Master Bot Online</b>\n\n"
                f"Accounts restored: <b>{existing_sessions}</b>\n"
                f"Uptime started: {get_uptime()}\n"
                f"Total reports saved: {STATE['total_reports']}\n"
                f"Rounds saved: {STATE['rounds_completed']}\n\n"
                f"Use <b>/login</b> if you need to add more accounts.\n"
                f"Else run <b>/send_proofs</b> → <b>/start_reports</b> → <b>/status</b>.",
                disable_web_page_preview=True,
            )
        except Exception:
            pass


async def on_shutdown():
    STATE["reporting_running"] = False
    await disconnect_all_clients()
    try:
        await bot.session.close()
    except Exception:
        pass


if __name__ == "__main__":
    banner_text = f"""{Fore.MAGENTA}{Style.BRIGHT}
╔═══════════════════════════════════════════════════════════════╗
║          TELEGRAM SCAM BUSTER — MASTER CONTROL BOT            ║
║              Single-command Login + Reports + Proofs          ║
╚═══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner_text)
    log("Open Telegram, find your bot, send /start", "INFO")
    log("Bot commands: /login → /send_proofs → /start_reports → /status", "INFO")
    try:
        start_health_server()
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        asyncio.run(dp.start_polling(bot, handle_signals=True))
    except KeyboardInterrupt:
        log("Shutdown via Ctrl+C", "WARN")
        sys.exit(0)
    except Exception as e:
        log(f"Master bot crashed: {e}", "ERROR")
        sys.exit(1)

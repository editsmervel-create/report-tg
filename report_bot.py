import os
import sys
import time
import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import InputReportReasonSpam, InputReportReasonViolence, \
    InputReportReasonPornography, InputReportReasonChildAbuse, \
    InputReportReasonCopyright, InputReportReasonFake, \
    InputReportReasonGeoIrrelevant, InputReportReasonIllegalDrugs, \
    InputReportReasonPersonalDetails
from telethon.errors import FloodWaitError, PhoneNumberUnoccupiedError, \
    SessionPasswordNeededError, PhoneCodeInvalidError

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

STATUS_QUEUE = None


def banner():
    print(f"""{Fore.CYAN}{Style.BRIGHT}
╔═══════════════════════════════════════════════════════════════╗
║     Telegram Multi-Account Report Tool v1.2 (Scam Buster)     ║
║     + Aiogram Status Bot Integration (Live Notifications)     ║
╚═══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}""")
    print(f"{Fore.YELLOW}[!] IMPORTANT: Use this tool ONLY for LEGITIMATE reports against")
    print(f"    scammers, abusers, or users violating Telegram ToS.")
    print(f"    False reporting may result in YOUR accounts being banned.\n")


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": Fore.WHITE, "SUCCESS": Fore.GREEN, "WARN": Fore.YELLOW,
              "ERROR": Fore.RED, "STEP": Fore.CYAN, "BOT": Fore.MAGENTA}
    color = colors.get(level, Fore.WHITE)
    print(f"{color}[{ts}] [{level}] {msg}{Style.RESET_ALL}")


async def emit_status_event(typ, **data):
    global STATUS_QUEUE
    if STATUS_QUEUE is None:
        return
    try:
        await STATUS_QUEUE.put({"type": typ, "data": data})
    except Exception:
        pass


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
        f"EXPOSED LIE: Fake Russia bio vs real Assam (India) identity. "
        f"ALIASES: @nikalgarib @NahhQT @diboed. "
        f"GROUPS: t.me/TEAMSTICKYONTOP + t.me/nikalgarib. "
        f"BANNERS: @Sexiestbanner @rarestbanner. PINNED: 15147444. "
        f"Evidence: 8+ screenshots + full video (IMG_3916.MP4) + UPI proof. "
        f"PLEASE PERMANENT BAN ALL ACCOUNTS + BLOCK PHONE {phone} + LEGAL ACTION (FRAUD + THREATS)."
    )
    specific = {
        "spam": f"SPAM/SCAM RING. {name} uses group TEAMSTICKYONTOP + alias @nikalgarib to scam via fake 'work/agent fees'. Phone {phone}. {base}",
        "fake": f"FAKE IDENTITY + FAKE LOCATION. {name} lies about Russia location (real Assam), multi-aliases: @tradaxin @nikalgarib @NahhQT @diboed. Phone {phone}. {base}",
        "violence": f"THREAT TO LIFE, FAMILY & RAPE. {name} threatens: 'Chod dalunga' (rape/assault), 'family power dikhunga', 'Jo ukhad sakta ukhad lena'. Victim terrified. Phone {phone}. {base}",
        "personal_details": f"VICTIM DOXXING + UPI LEAK. {name} demanded victim's location, used fake Russia location vs real phone {phone}. Suraj Chanda UPI leaked by scammer. @nikalgarib alias. {base}",
        "illegal_drugs": f"EXTORTION / ORGANIZED FINANCIAL FRAUD. Rs 3000 taken, 2-3k extra demand. Multi-account group scam. Phone {phone}. @nikalgarib + TEAMSTICKYONTOP. {base}",
        "geo_irrelevant": f"LOCATION FRAUD EXPOSED: {name} bio claims Russia but OWN MSG 'Assam sw hu' + UPI Bank (Assam Gramin Vikash) + phone {phone} = ASSAM, INDIA. Group t.me/nikalgarib. {base}",
        "child_abuse": base,
        "pornography": base,
        "copyright": base,
    }
    return specific.get(reason_key, base)


async def login_account(phone):
    session_path = os.path.join(SESSIONS_DIR, phone.replace("+", ""))
    client = TelegramClient(session_path, config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            log(f"Account {phone} logged in as @{me.username} ({me.first_name})", "SUCCESS")
            return client
    except Exception as e:
        log(f"Connection failed for {phone}: {e}", "ERROR")
        await emit_status_event("error", msg=f"Connect {phone}: {e}")

    try:
        if not await client.is_user_authorized():
            log(f"Sending login code to {phone}...", "STEP")
            try:
                await client.send_code_request(phone)
            except PhoneNumberUnoccupiedError:
                log(f"Phone {phone} not registered on Telegram. Skipping.", "ERROR")
                await client.disconnect()
                return None

            code = input(f"{Fore.MAGENTA}[?] Enter OTP for {phone}: {Style.RESET_ALL}").strip()
            try:
                await client.sign_in(phone, code)
            except PhoneCodeInvalidError:
                log("Invalid code. Try again.", "ERROR")
                code = input(f"{Fore.MAGENTA}[?] Re-enter OTP: {Style.RESET_ALL}").strip()
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                pwd = input(f"{Fore.MAGENTA}[?] 2FA Password: {Style.RESET_ALL}")
                await client.sign_in(password=pwd)

            me = await client.get_me()
            log(f"Successfully logged in {phone} as @{me.username}", "SUCCESS")
            return client

    except FloodWaitError as e:
        log(f"Flood wait for {phone}: {e.seconds} seconds. Try later.", "ERROR")
        await emit_status_event("error", msg=f"FloodWait login {phone}: {e.seconds}s")
    except Exception as e:
        log(f"Login failed for {phone}: {e}", "ERROR")
        await emit_status_event("error", msg=f"Login {phone}: {e}")

    await client.disconnect()
    return None


async def resolve_entity(client, identifier, label="target"):
    try:
        return await client.get_entity(identifier)
    except Exception as e:
        log(f"Could not resolve {label} '{identifier}': {e}", "WARN")
        return None


async def report_one_target(client, phone_display, entity, reasons, label):
    total = 0
    entity_desc = f"@{entity.username}" if getattr(entity, "username", None) else f"ID {entity.id}"
    for reason_key in reasons:
        reason_cls = REASON_MAP.get(reason_key)
        if not reason_cls:
            continue
        try:
            msg = get_detailed_report_message(reason_key)
            log(f"[{phone_display}] Reporting {label} {entity_desc} -> {reason_key}", "STEP")
            result = await client(ReportPeerRequest(peer=entity, reason=reason_cls(message=msg)))
            if result:
                log(f"[{phone_display}]   ✓ {label} report OK ({reason_key})", "SUCCESS")
                total += 1
            else:
                log(f"[{phone_display}]   ⚠ {label} report empty ({reason_key})", "WARN")
            await asyncio.sleep(4)
        except FloodWaitError as e:
            log(f"[{phone_display}] FloodWait {e.seconds}s on {label}", "WARN")
            await emit_status_event("error", msg=f"FloodWait {e.seconds}s on {label}")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            log(f"[{phone_display}]   ✗ {label} report failed ({reason_key}): {e}", "ERROR")
            await emit_status_event("error", msg=f"Report {label} {reason_key}: {e}")
    return total


async def report_target(client, phone_display, main_entity, reasons):
    total = 0
    total += await report_one_target(client, phone_display, main_entity, reasons, "MAIN")

    extras = []
    extra_list = getattr(config, "EXTRA_TARGETS", [
        "@nikalgarib", "@NahhQT", "@diboed",
        "https://t.me/TEAMSTICKYONTOP", "https://t.me/nikalgarib",
        "@Sexiestbanner", "@rarestbanner"
    ])
    for extra_id in extra_list:
        try:
            ent = await client.get_entity(extra_id)
            extras.append((ent, extra_id))
        except Exception:
            pass

    for ent, label in extras:
        await asyncio.sleep(3)
        total += await report_one_target(client, phone_display, ent, reasons, f"EXTRA:{label}")

    return total


async def get_target_entity(client):
    if config.TARGET_USER_ID:
        try:
            return await client.get_entity(config.TARGET_USER_ID)
        except Exception as e:
            log(f"Failed to resolve TARGET_USER_ID: {e}", "ERROR")
    if config.TARGET_USERNAME:
        try:
            return await client.get_entity(config.TARGET_USERNAME)
        except Exception as e:
            log(f"Failed to resolve TARGET_USERNAME: {e}", "ERROR")
    return None


async def send_proofs_to_officials(client, phone_display, proofs_folder):
    if not hasattr(config, "REPORT_USERNAMES") or not config.REPORT_USERNAMES:
        return
    proof_files = []
    try:
        for fn in sorted(os.listdir(proofs_folder)):
            fp = os.path.join(proofs_folder, fn)
            ext = os.path.splitext(fn)[1].lower()
            if os.path.isfile(fp) and ext in config.PROOF_EXTENSIONS:
                proof_files.append(fp)
    except Exception:
        return
    if not proof_files:
        return

    summary = config.REPORT_MESSAGE_SUMMARY.format(
        target=config.TARGET_USERNAME or str(config.TARGET_USER_ID),
        display_name=config.TARGET_DISPLAY_NAME
    )

    for ru in config.REPORT_USERNAMES:
        try:
            ent = await resolve_entity(client, ru, "ReportBot")
            if not ent:
                continue
            try:
                await client.send_message(ent, summary)
                await asyncio.sleep(2)
                for i, fp in enumerate(proof_files[:5]):
                    await client.send_file(ent, fp, caption=f"Proof #{i+1} against {config.TARGET_USERNAME}")
                    await asyncio.sleep(4)
                log(f"[{phone_display}] Proofs sent to {ru}", "SUCCESS")
            except Exception as e:
                log(f"[{phone_display}] Could not send proofs to {ru}: {e}", "WARN")
        except Exception:
            pass


async def single_round(clients, reasons, send_proofs, round_num):
    log(f"=== Starting new report round ===", "STEP")
    target_entity = None
    for c in clients:
        if c:
            target_entity = await get_target_entity(c)
            if target_entity:
                break

    if not target_entity:
        log("Could not resolve target entity. Aborting round.", "ERROR")
        await emit_status_event("error", msg="Could not resolve target in round")
        return 0

    total_reports = 0
    for idx, client in enumerate(clients):
        if not client:
            continue
        me = await client.get_me()
        phone_display = f"+{me.phone}" if me.phone else f"@{me.username}"
        reports = await report_target(client, phone_display, target_entity, reasons)
        total_reports += reports

        if send_proofs and idx == 0:
            await send_proofs_to_officials(client, phone_display, config.PROOFS_FOLDER)

        if idx < len(clients) - 1:
            log(f"Waiting {config.DELAY_BETWEEN_ACCOUNTS}s before next account...", "INFO")
            await asyncio.sleep(config.DELAY_BETWEEN_ACCOUNTS)

    log(f"=== Round #{round_num} complete: {total_reports} reports sent (main + accomplices) ===", "SUCCESS")
    await emit_status_event("reports", reports=total_reports, round=round_num)
    return total_reports


async def login_all_accounts():
    clients = []
    log(f"Attempting login for {len(config.PHONE_NUMBERS)} account(s)...", "STEP")
    for phone in config.PHONE_NUMBERS:
        try:
            client = await login_account(phone)
            if client:
                clients.append(client)
        except Exception as e:
            log(f"Critical error for {phone}: {e}", "ERROR")
            await emit_status_event("error", msg=f"Login critical {phone}: {e}")
        time.sleep(2)

    log(f"Successfully logged into {len(clients)}/{len(config.PHONE_NUMBERS)} accounts", "INFO")
    await emit_status_event("accounts", active=len(clients), total=len(config.PHONE_NUMBERS))
    return clients


async def main_core():
    banner()

    if not config.PHONE_NUMBERS or len(config.PHONE_NUMBERS) == 0:
        log("No phone numbers in config.py. Add at least one account.", "ERROR")
        return

    if not config.TARGET_USERNAME and not config.TARGET_USER_ID:
        log("Set TARGET_USERNAME or TARGET_USER_ID in config.py first.", "ERROR")
        return

    reasons = [r for r in config.SELECTED_REASONS if r in REASON_MAP]
    if not reasons:
        log("No valid reasons selected in config.py", "ERROR")
        return

    send_proofs = getattr(config, "SEND_PROOFS_EVERY_ROUND", False)

    log(f"Target: {config.TARGET_USERNAME or config.TARGET_USER_ID} ({config.TARGET_DISPLAY_NAME})", "INFO")
    log(f"Scammer real phone: {getattr(config, 'SCAMMER_REAL_PHONE', 'N/A')}", "INFO")
    log(f"Selected report reasons: {', '.join(reasons)}", "INFO")
    extras = getattr(config, "EXTRA_TARGETS", ["@nikalgarib","@NahhQT","@diboed","TEAMSTICKYONTOP","@Sexiestbanner","@rarestbanner"])
    log(f"Also reporting extras: {', '.join(extras)}", "INFO")
    log(f"Delay between accounts: {config.DELAY_BETWEEN_ACCOUNTS}s", "INFO")
    log(f"Delay between rounds: {config.DELAY_BETWEEN_ROUNDS}s", "INFO")
    log(f"Auto-send proofs every round: {'YES' if send_proofs else 'NO (use send_proofs.py separately)'}", "INFO")
    if getattr(config, "BOT_TOKEN", None):
        log(f"Status Bot: ENABLED (via status_bot.py). Launch separately for live Telegram notifications.", "BOT")

    clients = await login_all_accounts()
    if not clients:
        log("No accounts logged in. Exiting.", "ERROR")
        return

    grand_total = 0
    round_num = 0
    try:
        while True:
            round_num += 1
            log(f"============= ROUND #{round_num} =============", "STEP")
            count = await single_round(clients, reasons, send_proofs, round_num)
            grand_total += count
            log(f"Progress: {grand_total} total reports (main + accomplices) so far", "INFO")
            log(f"Waiting {config.DELAY_BETWEEN_ROUNDS}s until next round... (Press Ctrl+C to stop)", "INFO")
            try:
                await asyncio.sleep(config.DELAY_BETWEEN_ROUNDS)
            except KeyboardInterrupt:
                break
    except KeyboardInterrupt:
        log("\nUser interrupted. Stopping...", "WARN")
    finally:
        log(f"Disconnecting {len(clients)} account(s)...", "INFO")
        for c in clients:
            try:
                await c.disconnect()
            except Exception:
                pass
        log(f"=== FINISHED ===", "SUCCESS")
        log(f"Total reports sent across all rounds: {grand_total}", "SUCCESS")


async def main_with_bot():
    global STATUS_QUEUE
    try:
        from status_bot import run_in_background
        STATUS_QUEUE, bot_coro = run_in_background()
        bot_task = asyncio.create_task(bot_coro)
        log("Status Bot background task started (aiogram).", "BOT")
    except Exception as e:
        log(f"Status Bot failed to init (running without): {e}", "WARN")
        bot_task = None
        STATUS_QUEUE = None

    try:
        await main_core()
    finally:
        if bot_task is not None and not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except (asyncio.CancelledError, Exception):
                pass


if __name__ == "__main__":
    use_bot = "--with-bot" in sys.argv
    if use_bot and getattr(config, "BOT_TOKEN", None):
        log("Starting report tool WITH Status Bot (aiogram)...", "STEP")
        try:
            asyncio.run(main_with_bot())
        except KeyboardInterrupt:
            log("\nExiting...", "WARN")
            sys.exit(0)
    else:
        if not use_bot and getattr(config, "BOT_TOKEN", None):
            log("Tip: run with 'python report_bot.py --with-bot' to enable status bot live notifications", "BOT")
        try:
            asyncio.run(main_core())
        except KeyboardInterrupt:
            log("\nExiting...", "WARN")
            sys.exit(0)

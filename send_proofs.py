import os
import sys
import time
import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, \
    UserBlockedError, AuthBytesInvalidError
from telethon.tl.types import InputMediaUploadedPhoto, InputMediaUploadedDocument

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[0m'
    class Style:
        RESET_ALL = '\033[0m'
        BRIGHT = '\033[1m'

import config

if not getattr(config, "API_ID", 0) or not getattr(config, "API_HASH", ""):
    print("ERROR: API_ID/API_HASH missing. Set environment variables API_ID and API_HASH.")
    sys.exit(1)

SESSIONS_DIR = "sessions"
STATUS_QUEUE = None

async def emit_status(typ, **data):
    global STATUS_QUEUE
    if STATUS_QUEUE is None:
        return
    try:
        await STATUS_QUEUE.put({"type": typ, "data": data})
    except Exception:
        pass


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": Fore.WHITE,
        "SUCCESS": Fore.GREEN,
        "WARN": Fore.YELLOW,
        "ERROR": Fore.RED,
        "STEP": Fore.CYAN,
    }
    color = colors.get(level, Fore.WHITE)
    print(f"{color}[{ts}] [{level}] {msg}{Style.RESET_ALL}")


def banner():
    print(f"""{Fore.MAGENTA}{Style.BRIGHT}
╔═══════════════════════════════════════════════════════════════╗
║     Telegram Proof Submitter v1.1 (@Notoscam / @Support)      ║
║         Scam + Threat + Family Danger - Emergency Mode        ║
╚═══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}""")


def collect_proof_files():
    files = []
    if not os.path.exists(config.PROOFS_FOLDER):
        os.makedirs(config.PROOFS_FOLDER)
        log(f"Created folder '{config.PROOFS_FOLDER}'. Put your proof pics/videos there.", "WARN")
        return files

    for fn in sorted(os.listdir(config.PROOFS_FOLDER)):
        fp = os.path.join(config.PROOFS_FOLDER, fn)
        if os.path.isfile(fp):
            ext = os.path.splitext(fn)[1].lower()
            if ext in config.PROOF_EXTENSIONS:
                size_mb = os.path.getsize(fp) / (1024 * 1024)
                if size_mb > 2000:
                    log(f"Skipping {fn} (too large: {size_mb:.1f}MB)", "WARN")
                    continue
                files.append(fp)

    log(f"Found {len(files)} proof file(s) in '{config.PROOFS_FOLDER}'", "INFO")
    for f in files:
        log(f"  ✓ {os.path.basename(f)} ({os.path.getsize(f) / (1024 * 1024):.2f} MB)", "INFO")
    return files


async def login_existing(phone):
    session_path = os.path.join(SESSIONS_DIR, phone.replace("+", ""))
    if not os.path.exists(session_path + ".session"):
        log(f"No session found for {phone}. Run report_bot.py first to login.", "WARN")
        return None

    client = TelegramClient(session_path, config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            log(f"Account {phone} ready as @{me.username} ({me.first_name})", "SUCCESS")
            return client
    except AuthBytesInvalidError:
        log(f"Session invalid for {phone}. Re-run report_bot.py.", "ERROR")
    except Exception as e:
        log(f"Connection failed for {phone}: {e}", "ERROR")

    try:
        await client.disconnect()
    except Exception:
        pass
    return None


def is_image(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic"]


def is_video(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]


def is_audio(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".ogg", ".mp3", ".wav", ".amr", ".aac"]


async def upload_and_send_proofs(client, phone, proofs):
    me = await client.get_me()
    summary_msg = config.REPORT_MESSAGE_SUMMARY.format(
        target=config.TARGET_USERNAME or str(config.TARGET_USER_ID),
        display_name=config.TARGET_DISPLAY_NAME
    )

    for report_user in config.REPORT_USERNAMES:
        log(f"[{phone}] -> Submitting proofs to {report_user}...", "STEP")
        try:
            target_entity = await client.get_entity(report_user)

            try:
                await client.send_message(target_entity, summary_msg)
                log(f"[{phone}] Summary message sent to {report_user}", "SUCCESS")
                await asyncio.sleep(2)
            except Exception as e:
                log(f"[{phone}] Couldn't send text to {report_user}: {e}", "WARN")

            sent_count = 0
            image_proofs = [p for p in proofs if is_image(p)]
            other_proofs = [p for p in proofs if not is_image(p)]

            MAX_PER_ALBUM = 10
            if len(image_proofs) >= 2:
                for chunk_idx in range(0, len(image_proofs), MAX_PER_ALBUM):
                    chunk = image_proofs[chunk_idx : chunk_idx + MAX_PER_ALBUM]
                    try:
                        captions = [
                            f"Proof #{chunk_idx + i + 1} - Photo evidence against {config.TARGET_USERNAME} ({config.TARGET_DISPLAY_NAME}) - SCAM + THREATS + UPI PROOF"
                            for i in range(len(chunk))
                        ]
                        if len(chunk) == 1:
                            await client.send_file(target_entity, chunk[0], caption=captions[0][:1000])
                        else:
                            await client.send_file(target_entity, chunk, caption=captions[-1][:1000])
                        sent_count += len(chunk)
                        log(f"[{phone}]   ✓ Album {chunk_idx // MAX_PER_ALBUM + 1}: {len(chunk)} images sent to {report_user}", "SUCCESS")
                        await asyncio.sleep(5)
                    except FloodWaitError as e:
                        log(f"[{phone}] FloodWait: {e.seconds}s. Waiting...", "WARN")
                        await asyncio.sleep(e.seconds + 10)
                    except (ChatWriteForbiddenError, UserBlockedError) as e:
                        log(f"[{phone}] Cannot message {report_user}: {e}. Skipping this target.", "ERROR")
                        break
                    except Exception as e:
                        log(f"[{phone}]   ⚠ Album failed, falling back to individual send: {e}", "WARN")
                        for i, p in enumerate(chunk):
                            fname = os.path.basename(p)
                            try:
                                await client.send_file(target_entity, p, caption=f"Proof #{chunk_idx + i + 1}: {fname} - Scam/Threat evidence"[:1000])
                                sent_count += 1
                                await asyncio.sleep(3)
                            except Exception as e2:
                                log(f"[{phone}]   ✗ {fname}: {e2}", "ERROR")

            for idx, proof in enumerate(other_proofs):
                fname = os.path.basename(proof)
                overall_idx = len(image_proofs) + idx + 1
                caption = f"Proof #{overall_idx} - Evidence against {config.TARGET_USERNAME} ({config.TARGET_DISPLAY_NAME}) - SCAMMER (@tradaxin / Mr╳ 【STICKYYY】) - File: {fname}"
                try:
                    if is_video(proof):
                        await client.send_file(target_entity, proof, caption=caption[:1000], supports_streaming=True, thumbnail=None)
                    elif is_audio(proof):
                        await client.send_file(target_entity, proof, caption=caption[:1000], voice_note=False)
                    else:
                        await client.send_file(target_entity, proof, caption=caption[:1000], force_document=True)
                    sent_count += 1
                    log(f"[{phone}]   ✓ Sent proof {overall_idx}/{len(proofs)}: {fname}", "SUCCESS")
                    await asyncio.sleep(3)
                except FloodWaitError as e:
                    log(f"[{phone}] FloodWait: {e.seconds}s. Waiting...", "WARN")
                    await asyncio.sleep(e.seconds + 5)
                    try:
                        if is_video(proof):
                            await client.send_file(target_entity, proof, caption=caption[:1000], supports_streaming=True)
                        else:
                            await client.send_file(target_entity, proof, caption=caption[:1000], force_document=True)
                        log(f"[{phone}]   ✓ Retry sent: {fname}", "SUCCESS")
                        sent_count += 1
                    except Exception as e2:
                        log(f"[{phone}]   ✗ Retry failed for {fname}: {e2}", "ERROR")
                except (ChatWriteForbiddenError, UserBlockedError) as e:
                    log(f"[{phone}] Cannot message {report_user}: {e}. Skipping this target.", "ERROR")
                    break
                except Exception as e:
                    log(f"[{phone}]   ✗ Failed to send {fname}: {e}", "ERROR")

            log(f"[{phone}] -> {report_user}: {sent_count}/{len(proofs)} proofs submitted", "INFO")
            await asyncio.sleep(5)

        except FloodWaitError as e:
            log(f"[{phone}] FloodWait on resolve {report_user}: {e.seconds}s", "WARN")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            log(f"[{phone}] Failed to submit to {report_user}: {e}", "ERROR")


async def main():
    banner()

    proofs = collect_proof_files()
    if not proofs:
        log(f"ERROR: No proof files found. Put images/videos in the '{config.PROOFS_FOLDER}' folder.", "ERROR")
        log(f"Expected folder: {os.path.abspath(config.PROOFS_FOLDER)}", "ERROR")
        return

    if not os.path.exists(SESSIONS_DIR):
        log("No sessions folder. Run report_bot.py first to login accounts.", "ERROR")
        return

    clients = []
    log(f"Loading existing sessions for {len(config.PHONE_NUMBERS)} account(s)...", "STEP")
    for phone in config.PHONE_NUMBERS:
        client = await login_existing(phone)
        if client:
            clients.append((phone, client))
        time.sleep(2)

    if not clients:
        log("No logged-in accounts found. Run report_bot.py first!", "ERROR")
        return

    log(f"Loaded {len(clients)} account(s). Starting proof submission...", "STEP")
    try:
        for idx, (phone, client) in enumerate(clients):
            await upload_and_send_proofs(client, phone, proofs)
            if idx < len(clients) - 1:
                log(f"Waiting {config.DELAY_BETWEEN_ACCOUNTS}s before next account...", "INFO")
                await asyncio.sleep(config.DELAY_BETWEEN_ACCOUNTS)
    finally:
        log("Disconnecting all clients...", "INFO")
        for _, client in clients:
            try:
                await client.disconnect()
            except Exception:
                pass
    log("=== PROOF SUBMISSION COMPLETED ===", "SUCCESS")
    log(f"Total proofs sent per account: {len(proofs)} x {len(clients)} accounts = {len(proofs) * len(clients)} total files delivered", "SUCCESS")
    log("Tip: Also email abuse@telegram.org with the same proofs for extra priority.", "INFO")


async def main_with_bot():
    global STATUS_QUEUE
    try:
        from status_bot import run_in_background
        STATUS_QUEUE, bot_coro = run_in_background()
        bot_task = asyncio.create_task(bot_coro)
    except Exception as e:
        log(f"Status Bot failed to init (running without): {e}", "WARN")
        bot_task = None
        STATUS_QUEUE = None
    try:
        await main()
        await emit_status("proofs", count=len(collect_proof_files()), accounts=len(getattr(config, "PHONE_NUMBERS", [])))
    finally:
        if bot_task is not None and not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except (asyncio.CancelledError, Exception):
                pass


if __name__ == "__main__":
    use_bot = "--with-bot" in sys.argv
    try:
        if use_bot and getattr(config, "BOT_TOKEN", None):
            asyncio.run(main_with_bot())
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        log("\nUser interrupted.", "WARN")
        sys.exit(0)

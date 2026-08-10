import os

API_ID = int(os.getenv("API_ID", "0") or "0")
API_HASH = os.getenv("API_HASH", "") or ""

BOT_TOKEN = os.getenv("BOT_TOKEN", "") or ""
BOT_OWNER_CHAT_ID = os.getenv("BOT_OWNER_CHAT_ID")
if BOT_OWNER_CHAT_ID is not None:
    try:
        BOT_OWNER_CHAT_ID = int(BOT_OWNER_CHAT_ID)
    except Exception:
        BOT_OWNER_CHAT_ID = None

TARGET_USERNAME = "@tradaxin"
TARGET_USER_ID = None
TARGET_DISPLAY_NAME = "Mr╳ 【STICKYYY】 / Chill Flame #105818"

REPORT_REASONS = [
    "spam",
    "violence",
    "pornography",
    "child_abuse",
    "copyright",
    "fake",
    "geo_irrelevant",
    "illegal_drugs",
    "personal_details",
]

SELECTED_REASONS = ["spam", "fake", "violence", "personal_details"]

DELAY_BETWEEN_ACCOUNTS = 15
DELAY_BETWEEN_ROUNDS = 600
REPORTS_PER_ACCOUNT_PER_ROUND = 1

AUTO_START_REPORTS_AFTER_LOGIN = True

PHONE_NUMBERS = [
    "+919876543210",
    "+919876543211",
]

PROOFS_FOLDER = "proofs"

REPORT_MESSAGE_SUMMARY = """
URGENT: SCAMMER + THREAT + EXTORTION. PLEASE BAN PERMANENTLY.
HIGH PRIORITY - FAMILY THREATS + REAL PHONE NUMBER + UPI PROOF.

====================================================
SCAMMER / THREAT PROFILE (FULL IDENTITY)
====================================================
- PRIMARY USERNAME : @tradaxin   (display name: Mr╳ 【STICKYYY】)
- ALT USERNAME     : @nikalgarib  (same scammer - alternate account)
- OTHER USERNAMES  : @NahhQT , @diboed   (same person / partners)
- DISPLAY NAME     : Mr╳ 【STICKYYY】 / Chill Flame #105818
- REAL PHONE NO.   : +91 93959 21365   (OWN TELEGRAM REGISTERED PHONE)
- PINNED CHANNEL   : 15147444 (53 subscribers, fake "channel" for scam)
- BIO FAKE         : Shows Russia location + Russia flag. FAKE!
- REAL LOCATION    : ASSAM, INDIA (he admits it - see below)
- SCAM GROUP       : https://t.me/TEAMSTICKYONTOP (STICKYYY AGENTS COMMUNITY)
- ALT GROUP/URL    : https://t.me/nikalgarib (his other alias channel)
- SUPPORT HANDLES  : @tradaxin @NahhQT (group me listed)
- OTHER BANNER IDs : @Sexiestbanner @rarestbanner @XXXX- @XnXX- @MeMe @instagram

====================================================
FINANCIAL SCAM (Extortion) - FULL PROOF CHAIN
====================================================
- UPI PAYMENT TAKEN  : Rs 3,000  (Three Thousand Rupees)
- UPI BENEFICIARY    : Suraj Chanda
- UPI BANK           : Assam Gramin Vikash Bank
- PAYMENT PROOF      : Screenshot attached (Rs.3000.00 payment success + QR)
- FURTHER DEMANDS    : "Mujhe aur 2k 3k fund krwa de" (Rs 2000-3000 extra demand)
- MULTIPLE PAYMENTS  : "Payment 1500 1500 kr diya unko" (scam pattern exposed)
- SCAM CONFESSED (his own msgs):
                        * "Idhar scam ho rha"
                        * "Sala 2k. Scam ktk gaya"

====================================================
THREATS, ABUSE AND HARASSMENT (Family + Rape Threats)
====================================================
EXACT QUOTES from the scammer (screenshots + video attached):
- "Madarchod vc aa"
- "Aukat h to"
- "Mc.1"
- "Re bsdk"
- "Bahg"
- "Tu kya jhat bolega"
- "Soo rha kal aaunga"
- "Dehadi nahi krta hy na"
- "Salo"
- "Jo ukhad sakta ukhad lena"    (open threat - "Do whatever you can")
- "Tere family power dikhna mai dikhunga apna"
  (FAMILY THREAT: "I will show my family power vs yours")
- "Tg par  3 4 lakh dikhne se kuch n hota"
- "Gand. Mat gisa"
- "Chod dalunga"                   (THREAT OF RAPE / PHYSICAL ASSAULT)
- "Ja ab"
- "Time pass n kt"

====================================================
LOCATION & IDENTITY TRACE (Caught in his own lie)
====================================================
1. TELEGRAM BIO SAYS: "Kraysnoyarsk Krai, Russia" + Russia flag
   (100% FAKE location to avoid police action)
2. HIS OWN MESSAGE: "Assam sw hu" = "I AM FROM ASSAM"
3. UPI BANK: Assam Gramin Vikash Bank (Regional rural bank of ASSAM only!)
4. Apple Maps LOCATION he shared = ASSAM area
5. HIS REAL PHONE NUMBER: +91 93959 21365  (Indian mobile, registered on Telegram)
   - Trace this number via TRAI + telecom operator to find his name/address
   - Also cross-check with UPI holder Suraj Chanda (likely same person or family)

====================================================
EVIDENCE FILES ATTACHED (please review)
====================================================
1. 8+ screenshots of Telegram chat (full conversation):
   - scam confession messages
   - gaali / dhamki (abuse + threats)
   - money demand screenshots
   - family threats ("tere family power dikhna...", "Chod dalunga")
   - Russia vs Assam location contradiction
   - group join links of TEAMSTICKYONTOP + nikalgarib
   - profile page showing @tradaxin @NahhQT @diboed @nikalgarib
2. Video proof: IMG_3916.MP4 (VC voice recording + dhamki on video call)
3. UPI Payment success screenshot: Rs.3,000 to Suraj Chanda (Assam)
4. UPI QR code screenshot of scammer
5. His phone number (+91 93959 21365) shared on chat screenshot

====================================================
REQUEST TO TELEGRAM TRUST & SAFETY
====================================================
1. IMMEDIATE PERMANENT BAN / SUSPEND:
   - @tradaxin        (primary account)
   - @nikalgarib      (his alternate / alias account)
   - @NahhQT          (same scammer alias)
   - @diboed          (third alias)
2. BAN SCAM GROUPS / CHANNELS:
   - https://t.me/TEAMSTICKYONTOP  (STICKYYY AGENTS COMMUNITY)
   - https://t.me/nikalgarib       (his other group/channel)
3. DELETE HIS FAKE CHANNEL: ID 15147444 ("ABOUT sticky" fake channel)
4. BAN banner network IDs: @Sexiestbanner @rarestbanner
5. BLOCK HIS REGISTERED PHONE NUMBER: +91 93959 21365
   (prevent new account creation on same number)
6. LEGAL / INVESTIGATION (share with authorities):
   - Share phone number + IP log + UPI details with Indian Cyber Crime
   - Contact: cyber.gov.in (NCRP India)
   - Bank: Assam Gramin Vikash Bank, A/c holder Suraj Chanda
   - Phone: +91 93959 21365 (scammer's registered Telegram number)
7. Preserve all chat logs + evidence files for any criminal prosecution.

This person is a DANGEROUS SCAMMER. He is:
- Extorting money via fake "work / agent" scams
- THREATENING VICTIM'S ENTIRE FAMILY with violence ("family power dikhunga")
- Using RAPE THREATS ("Chod dalunga") to terrorize victims
- Faking his location (Russia vs real Assam) to hide from police
- Using multiple Telegram accounts + groups + phone numbers to run scam ring

VICTIM HAS FULL EVIDENCE CHAIN. PLEASE ACT URGENTLY BEFORE HE HARMS MORE
PEOPLE. Family threats + financial fraud together make this a CRIMINAL CASE.
"""

REPORT_USERNAMES = [
    "@Notoscam",
    "@Support",
    "@Telegram",
]

PROOF_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".heic",
    ".ogg", ".mp3", ".wav", ".amr", ".aac",
    ".pdf", ".txt", ".doc", ".docx", ".rtf",
]

SEND_PROOFS_EVERY_ROUND = False

EXTRA_TARGETS = [
    "@nikalgarib",
    "@NahhQT",
    "@diboed",
    "https://t.me/TEAMSTICKYONTOP",
    "https://t.me/nikalgarib",
    "@Sexiestbanner",
    "@rarestbanner",
]

SCAMMER_REAL_PHONE = "+919395921365"

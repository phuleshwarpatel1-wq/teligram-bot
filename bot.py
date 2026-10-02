import os
import re
import base64
import urllib.parse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# CHANNEL SETTINGS
# =========================

CHANNEL_USERNAME = "@tokyooobaby"
CHANNEL_LINK = "https://t.me/tokyooobaby"


# =========================
# URL DECODE
# =========================

def safe_decode(value):
    try:
        return urllib.parse.unquote(value)
    except Exception:
        return None


# =========================
# BASE64 DECODE
# =========================

def decode_base64(value):
    try:
        text = str(value).strip()

        # Remove whitespace
        text = re.sub(r"\s+", "", text)

        # URL-safe Base64
        text = text.replace("-", "+")
        text = text.replace("_", "/")

        if not text:
            return None

        # Add Base64 padding
        text += "=" * (-len(text) % 4)

        raw = base64.b64decode(
            text,
            validate=False
        )

        return raw.decode(
            "utf-8",
            errors="ignore"
        )

    except Exception:
        return None


# =========================
# FIREBASE URL EXTRACTION
# =========================

def extract_firebase_urls(text):

    if not text:
        return []

    urls = []

    regex = re.compile(
        r"https?://[a-zA-Z0-9][a-zA-Z0-9._-]*"
        r"(?:firebaseio\.com|firebasedatabase\.app)",
        re.IGNORECASE
    )

    for match in regex.finditer(text):

        url = match.group(0)

        # Remove trailing dots
        url = re.sub(r"\.+$", "", url)

        try:
            parsed = urllib.parse.urlparse(url)

            hostname = parsed.hostname

            if not hostname:
                continue

            hostname = hostname.lower()

            if (
                hostname.endswith(".firebaseio.com")
                or hostname.endswith(".firebasedatabase.app")
            ):
                urls.append(
                    "https://" + hostname
                )

        except Exception:
            continue

    return list(dict.fromkeys(urls))


# =========================
# QUERY PARAMETERS
# =========================

def get_query_values(text):

    values = []

    try:
        parsed = urllib.parse.urlparse(text)

        query_values = urllib.parse.parse_qs(
            parsed.query,
            keep_blank_values=True
        )

        for value_list in query_values.values():

            for value in value_list:

                values.append(value)

                decoded = safe_decode(value)

                if decoded:
                    values.append(decoded)

    except Exception:
        pass

    # Common parameters used for encoded URLs
    regex = re.compile(
        r"(?:^|[?&])"
        r"(?:s|url|link|data)"
        r"=([^&#\s]+)",
        re.IGNORECASE
    )

    for match in regex.finditer(text):

        value = match.group(1)

        values.append(value)

        decoded = safe_decode(value)

        if decoded:
            values.append(decoded)

    return values


# =========================
# GENERATE CANDIDATES
# =========================

def generate_candidates(original):

    found = set()
    queue = []

    def add(value):

        if not isinstance(value, str):
            return

        value = value.strip()

        if not value:
            return

        if len(value) > 2000000:
            return

        if value in found:
            return

        found.add(value)
        queue.append(value)

    # Original text
    add(original)

    # Query values
    for value in get_query_values(original):
        add(value)

    index = 0

    # Maximum 8 decoding levels
    for _depth in range(8):

        if index >= len(queue):
            break

        end = len(queue)

        while index < end:

            current = queue[index]
            index += 1

            # URL decode
            decoded = safe_decode(current)

            if decoded and decoded != current:
                add(decoded)

            # Base64 decode
            decoded_base64 = decode_base64(current)

            if (
                decoded_base64
                and decoded_base64 != current
            ):
                add(decoded_base64)

            # Search query parameters again
            for value in get_query_values(current):
                add(value)

    return list(found)


# =========================
# FINAL FIREBASE EXTRACTION
# =========================

def extract_all(text):

    firebase_urls = []

    candidates = generate_candidates(text)

    for candidate in candidates:

        firebase_urls.extend(
            extract_firebase_urls(candidate)
        )

    return list(
        dict.fromkeys(firebase_urls)
    )


# =========================
# CHANNEL MEMBERSHIP CHECK
# =========================

async def is_channel_member(bot, user_id):

    try:

        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception as error:

        print(
            "Channel membership check error:",
            error
        )

        return False


# =========================
# JOIN CHANNEL MESSAGE
# =========================

async def send_join_message(update):

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 JOIN CHANNEL",
                url=CHANNEL_LINK
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(
        keyboard
    )

    await update.message.reply_text(
        "🔒 Bot use karne ke liye pehle "
        "hamara channel join karo.\n\n"
        "1️⃣ Channel join karo\n"
        "2️⃣ Phir /start bhejo\n"
        "3️⃣ Uske baad bot use karo.",
        reply_markup=reply_markup
    )


# =========================
# START COMMAND
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    joined = await is_channel_member(
        context.bot,
        user.id
    )

    if not joined:

        await send_join_message(update)

        return

    await update.message.reply_text(
        "🔥 TOKYO FIREBASE BOT\n\n"
        "✅ Channel membership verified.\n\n"
        "🔗 URL / Encoded URL / Base64 / "
        "Code bhejo."
    )


# =========================
# MESSAGE HANDLER
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    # Check channel membership
    # on every message
    joined = await is_channel_member(
        context.bot,
        user.id
    )

    if not joined:

        await send_join_message(update)

        return

    text = update.message.text or ""

    if not text.strip():

        await update.message.reply_text(
            "⚠️ Pehle URL ya code bhejo."
        )

        return

    urls = extract_all(text)

    if not urls:

        await update.message.reply_text(
            "❌ Firebase URL nahi mila."
        )

        return

    if len(urls) == 1:

        message = (
            "🔥 Firebase found & extracted ✓\n\n"
            + urls[0]
        )

    else:

        message = (
            f"🔥 {len(urls)} Firebase URLs found ✓\n\n"
        )

        for index, url in enumerate(
            urls,
            start=1
        ):

            message += (
                f"{index}. {url}\n"
            )

    await update.message.reply_text(
        message
    )


# =========================
# MAIN
# =========================

def main():

    token = os.getenv("BOT_TOKEN")

    if not token:

        raise RuntimeError(
            "BOT_TOKEN set nahi hai."
        )

    app = (
        Application
        .builder()
        .token(token)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print(
        "🔥 TOKYO FIREBASE BOT STARTED"
    )

    app.run_polling()


if __name__ == "__main__":
    main()

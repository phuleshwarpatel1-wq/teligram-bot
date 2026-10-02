import os
import re
import base64
import urllib.parse

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Firebase URL pattern
FIREBASE_PATTERN = re.compile(
    r'https?://[^\s<>"\']+\.(?:firebaseio\.com|firebasedatabase\.app)(?:[^\s<>"\']*)',
    re.IGNORECASE
)


def decode_text(text):
    results = [text]
    current = text

    for _ in range(8):
        changed = False

        # URL decode
        try:
            decoded = urllib.parse.unquote(current)
            if decoded != current:
                results.append(decoded)
                current = decoded
                changed = True
        except Exception:
            pass

        # Base64 decode
        try:
            padded = current + "=" * (-len(current) % 4)
            decoded = base64.b64decode(
                padded,
                validate=False
            ).decode("utf-8", errors="ignore")

            if decoded and decoded != current:
                results.append(decoded)
                current = decoded
                changed = True
        except Exception:
            pass

        if not changed:
            break

    return results


def extract_firebase_urls(text):
    found = []

    for decoded_text in decode_text(text):

        # Direct Firebase URLs
        matches = FIREBASE_PATTERN.findall(decoded_text)
        found.extend(matches)

        # Check common query parameters
        try:
            parsed = urllib.parse.urlparse(decoded_text)
            params = urllib.parse.parse_qs(parsed.query)

            for key in ["s", "url", "link", "data"]:
                for value in params.get(key, []):
                    found.extend(
                        FIREBASE_PATTERN.findall(
                            urllib.parse.unquote(value)
                        )
                    )
        except Exception:
            pass

    # Remove duplicates
    unique = []
    for url in found:
        url = url.rstrip(".,;)]}")
        if url not in unique:
            unique.append(url)

    return unique


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 TOKYO FIREBASE BOT\n\n"
        "Firebase URL bhejo, main automatically extract kar dunga."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""

    urls = extract_firebase_urls(text)

    if not urls:
        await update.message.reply_text(
            "❌ Firebase URL nahi mila."
        )
        return

    message = "🔥 Firebase URL Found:\n\n"

    for i, url in enumerate(urls, 1):
        message += f"{i}. {url}\n\n"

    await update.message.reply_text(message)


def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "BOT_TOKEN set nahi hai. Termux me BOT_TOKEN set karo."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("🔥 TOKYO FIREBASE BOT STARTED")
    app.run_polling()


if __name__ == "__main__":
    main()

import asyncio
import base64
import html
import logging
import os
import re
import ssl
from urllib.parse import unquote, parse_qs

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from dotenv import load_dotenv

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


def format_proxy_configs(content: str):
    """Format proxy configurations with proper HTML formatting"""
    formatted_configs = []
    proxy_count = 0

    # Regex to parse proxy URLs: protocol://[user@]host[:port][?params][#name]
    proxy_pattern = re.compile(
        r"^(?P<protocol>[a-zA-Z][a-zA-Z0-9+\-.]*)://"
        r"(?:(?P<user>[^@]+)@)?"
        r"(?P<host>[^:/?#]+)"
        r"(?::(?P<port>\d+))?"
        r"(?P<params>[^#]*)?"
        r"(?:#(?P<name>.*))?$"
    )

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        match = proxy_pattern.match(line)
        if not match:
            formatted_configs.append(html.escape(line))
            continue

        proxy_count += 1
        groups = match.groupdict()

        # Extract and decode name
        name = ""
        if groups["name"]:
            try:
                name = unquote(groups["name"])
            except:
                name = groups["name"]

        # Parse query parameters to extract SNI
        sni = ""
        if groups["params"] and groups["params"].startswith("?"):
            try:
                params = parse_qs(groups["params"][1:])  # Remove leading '?'
                sni = params.get('sni', [''])[0]
            except:
                pass

        # Build hostname:port
        host = groups["host"]
        port = groups["port"] or ""
        hostname_port = f"{host}:{port}" if port else host

        # Format output
        escaped_name = html.escape(name or f"Proxy {proxy_count}")
        escaped_user_id = html.escape(groups["user"] or "N/A")
        escaped_hostname = html.escape(hostname_port)
        escaped_line = html.escape(line)

        # Build the formatted output with SNI if available
        output_lines = [
            f"<b>{proxy_count}. {escaped_name}</b>",
            f" <b>ID:</b> {escaped_user_id}",
            f" <b>IP:</b> {escaped_hostname}"
        ]

        if sni:
            escaped_sni = html.escape(sni)
            output_lines.append(f" <b>SNI:</b> {escaped_sni}")

        output_lines.append(f"<code>{escaped_line}</code>")

        formatted_configs.append("\n".join(output_lines))

    return "\n\n".join(formatted_configs) if formatted_configs else content, proxy_count


async def fetch_base64_content(url: str):
    """Fetch and decode base64 content from URL"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    return f"Error: HTTP {response.status} - {response.reason}"

                content = await response.text()
                try:
                    return base64.b64decode(content).decode("utf-8")
                except (Exception,):
                    return f"Raw content (not base64): {content[:1000]}..."
    except aiohttp.ClientTimeout:
        return "Error: Request timed out"
    except Exception as e:
        return f"Error: {str(e)}"


@dp.message()
async def handle_message(message: Message):
    """Handle incoming messages as URLs"""
    url = message.text.strip() if message.text else ""

    if not url.startswith(("http://", "https://")):
        await message.answer("Bad protocol. Please send a valid HTTP or HTTPS URL.")
        return

    sent_message = await message.answer(f"🔄 Fetching content from: <code>{html.escape(url)}</code>")
    content = await fetch_base64_content(url)

    if content.startswith("Error:"):
        await sent_message.edit_text(f"❌ {html.escape(content)}")
        return

    formatted_content, proxy_count = format_proxy_configs(content)
    header = f"✅ Found {proxy_count} configurations:\n\n" if proxy_count else "✅ Decoded content:\n\n"
    full_message = header + formatted_content

    # Handle message length limits
    if len(full_message) <= 4000:
        await sent_message.edit_text(full_message)
        return

    # Split into chunks for long messages
    chunk_size = 4000 - len(header) - 10
    await sent_message.edit_text(f"{header}(Part 1)\n\n{formatted_content[:chunk_size]}")

    remaining = formatted_content[chunk_size:]
    for i, chunk in enumerate((remaining[j : j + 4000] for j in range(0, len(remaining), 4000)), 2):
        await message.answer(f"📝 Part {i}:\n\n{chunk}")


async def main():
    logger.info("Starting bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

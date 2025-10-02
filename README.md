# vless-to-text-bot

Telegram bot that fetches base64 encoded content from URLs and decodes proxy configurations.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and add your Telegram bot token:

```bash
cp .env.example .env
```

3. Run the bot:

```bash
python main.py
```

## Usage

Send any HTTP/HTTPS URL to the bot. It will fetch the content, decode base64, and format any proxy configurations found.

## Requirements

- Python 3.12+
- Telegram bot token from @BotFather

## License

[LICENSE](LICENSE)
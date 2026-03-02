from telethon import TelegramClient
from telethon.sessions import StringSession


def main() -> None:
    api_id = int(input("TELEGRAM_API_ID: ").strip())
    api_hash = input("TELEGRAM_API_HASH: ").strip()

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        print("\nTELETHON_STRING_SESSION:\n")
        print(client.session.save())


if __name__ == "__main__":
    main()

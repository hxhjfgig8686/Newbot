import requests
import re
import json
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from telegram import Bot
from telegram.ext import Application, CommandHandler
import asyncio

# Load environment variables
load_dotenv()
IVASMS_EMAIL = os.getenv("IVASMS_EMAIL")
IVASMS_PASSWORD = os.getenv("IVASMS_PASSWORD")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

async def send_to_telegram(sms):
    bot = Bot(token=BOT_TOKEN)
    message = (
        f"📩 New SMS\n"
        f"Time: {sms['timestamp']}\n"
        f"Number: +{sms['number']}\n"
        f"Message: {sms['message']}\n"
        f"Range: {sms['range']}\n"
        f"Revenue: {sms['revenue']}"
    )
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print("Sent to Telegram")
    except Exception as e:
        print(f"Telegram Error: {e}")

def payload_1(session):
    url = "https://www.ivasms.com/login"
    response = session.get(url, headers=BASE_HEADERS)
    token = re.search(r'name="_token" value="([^"]+)"', response.text).group(1)
    return token

def payload_2(session, token):
    url = "https://www.ivasms.com/login"
    data = {
        "_token": token,
        "email": IVASMS_EMAIL,
        "password": IVASMS_PASSWORD,
        "remember": "on"
    }
    session.post(url, headers=BASE_HEADERS, data=data)

def payload_3(session):
    url = "https://www.ivasms.com/portal/sms/received"
    response = session.get(url, headers=BASE_HEADERS)
    csrf = re.search(r'csrf-token" content="([^"]+)"', response.text).group(1)
    return csrf

def payload_4(session, csrf, from_date, to_date):
    url = "https://www.ivasms.com/portal/sms/received/getsms"
    data = {
        "_token": csrf,
        "from": from_date,
        "to": to_date
    }
    response = session.post(url, data=data)
    return response.text

def parse_statistics(html):
    soup = BeautifulSoup(html, 'html.parser')
    ranges = []
    cards = soup.find_all('div', class_='card card-body mb-1 pointer')
    
    for card in cards:
        cols = card.find_all('div')
        if len(cols) >= 5:
            ranges.append({
                "range": cols[0].text.strip(),
                "count": int(cols[1].text.strip() or 0)
            })
    return ranges

async def main():
    today = datetime.now()
    from_date = today.strftime("%m/%d/%Y")
    to_date = (today + timedelta(days=1)).strftime("%m/%d/%Y")

    last_counts = {}

    while True:
        try:
            with requests.Session() as session:
                token = payload_1(session)
                payload_2(session, token)
                csrf = payload_3(session)

                html = payload_4(session, csrf, from_date, to_date)
                ranges = parse_statistics(html)

                for r in ranges:
                    name = r["range"]
                    count = r["count"]

                    if name not in last_counts:
                        last_counts[name] = count

                    elif count > last_counts[name]:
                        sms = {
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "number": "Unknown",
                            "message": "New SMS detected",
                            "range": name,
                            "revenue": "0"
                        }
                        await send_to_telegram(sms)
                        last_counts[name] = count

                await asyncio.sleep(10)

        except Exception as e:
            print("Error:", e)
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())

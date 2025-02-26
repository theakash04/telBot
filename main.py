import json
from dotenv import load_dotenv
import time
import requests
import os
from apscheduler.schedulers.blocking import BlockingScheduler
import sys

load_dotenv()

MANGA_API= os.getenv("MANGA_API")
CHAT_ID= os.getenv("CHAT_ID")
BOT_TOKEN= os.getenv("BOT_TOKEN")
IMAGE_API= os.getenv("IMAGE_API")

JSON_FILE="titles.json"

if not all([MANGA_API, CHAT_ID, BOT_TOKEN]):
    print("Error: Missing required environment variables!")
    sys.exit(1)  # Exit the script with error code 1

def escape_markdown(text):
    """Escapes special characters for Telegram MarkdownV2."""
    text = str(text)
    if text:
        escape_chars = r"_*[]()~`>#+-=|{}.!"
        for char in escape_chars:
            text = text.replace(char, f"\\{char}")
    return text



def load_sent_titles():
    """Loads previously sent manhwa titles from a JSON file."""
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []


def save_title(title):
    """Saves a sent title to the JSON file to prevent duplicates."""
    sent_titles = load_sent_titles()
    sent_titles.append(title)
    with open(JSON_FILE, "w") as file:
        json.dump(sent_titles, file, indent=4)

def is_image_url_accessible(url):
    """
    Checks if the provided URL is accessible and points to an image.
    """
    try:
        response = requests.head(url, timeout=5)
        content_type = response.headers.get('Content-Type', '').lower()
        if response.status_code == 200 and content_type.startswith('image/'):
            return True
    except requests.RequestException as e:
        print(f"Error checking image URL: {e}")
    return False

def get_manga_list():
    """Fetches the latest manhwas from the API."""
    url = f"{MANGA_API}?limit=200&demographic=1&country=kr&status=1&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://comick.io",
    }
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception as err:
        print(f"Error while listing manhwas: {err}")
        return None


def send_message(title, link, rating,desc, chap, year, image=None):
    """
    Sends a formatted manhwa post to the Telegram channel.
    If the image URL is accessible, includes the image; otherwise, sends text only.
    """
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
    chat_id = f"@{CHAT_ID}"


    # Prepare the caption with escaped Markdown
    caption = (
        f"📖 *{escape_markdown(title)}*\n\n"
        f"⭐ Rating: {escape_markdown(str(rating))}\n"
        f"Chapter: {escape_markdown(str(chap))}\n"
        f"Year: {escape_markdown(str(year))}\n\n"
        f"{escape_markdown(desc)}"
    )

    
    # Inline keyboard markup
    reply_markup = json.dumps({
        "inline_keyboard": [
            [{"text": "🔗 READ NOW", "url": link}]
        ]
    }, ensure_ascii=False)

    # Check if the image URL is accessible
    if image and is_image_url_accessible(image):
        url = f"{base_url}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": image,
            "caption": caption,
            "parse_mode": "MarkdownV2",
            "reply_markup": reply_markup
        }    
    else:
        url = f"{base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": caption,
            "parse_mode": "MarkdownV2",
            "reply_markup": reply_markup
        }
    try:
        response = requests.post(url, data=payload)
        response_data = response.json()
        if not response_data.get("ok"):
            print(f"Telegram API Error: {response_data}")
            return None
        print(response_data["result"]["message_id"])
        return response_data["result"]["message_id"]
    except Exception as err:
        print(f"Error while sending message: {err}")
        return None




def schedule_task():
    """Fetches and sends new manhwa updates at the scheduled time."""

    manga_list = get_manga_list()
    if manga_list:
        for manga in manga_list:
            slug = manga.get("slug")
            comick_link = f"https://comick.io/comic/{slug}"
            title = manga.get("title")
            rating = manga.get("rating")
            desc = manga.get("desc")
            chap = manga.get("last_chapter")
            year = manga.get("year")
            image_url = None
            if "md_covers" in manga and manga["md_covers"]:
                image_url = f"{IMAGE_API}/{manga['md_covers'][0]['b2key']}" 


            sent_titles = load_sent_titles()
            if title in sent_titles:
                print(f"{title} already sent. skipping...")
                continue
            else:
                sent = send_message(title=title, link=comick_link, rating=rating, desc=desc,chap=chap, year=year, image=image_url)
                if sent:
                    save_title(title)
            time.sleep(15)

task = BlockingScheduler()
task.add_job(schedule_task, "cron", hour=18, minute=30)

schedule_task()


# Start the scheduler to keep the script running
print("Running schedule Task")
task.start()






import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
import os

load_dotenv()

# === CONFIG ===
clickup_api = os.getenv('CLICKUP_API_KEY')
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
TIMEZONE = 'Asia/Dhaka'

# === LISTS TO PROCESS ===
LISTS = [
    {
        "id": '901800830748',
        "title": "*Developer Task Board:*"
    },
    {
        "id": '901800835985',
        "title": "*Designer Task Board:*"
    }
]

# === FETCH TODAY'S TASKS FROM CLICKUP LIST ===
def get_tasks(list_id):
    headers = {"Authorization": clickup_api}
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    resp = requests.get(url, headers=headers)
    data = resp.json()
    tasks = data.get("tasks", [])

    # Filter tasks due today
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).date()

    today_tasks = []
    for task in tasks:
        due_ts = task.get("due_date")
        if due_ts:
            due_dt = datetime.fromtimestamp(int(due_ts) / 1000, tz).date()
            if due_dt == today:
                today_tasks.append(task)

    return today_tasks

# === SEND TO TELEGRAM ===
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": telegram_chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, data=payload)
    print("Telegram response:", resp.text)

# === FORMAT AND SEND FOR EACH LIST ===
def daily_task_summary(list_id, board_title):
    tasks = get_tasks(list_id)
    if not tasks:
        send_to_telegram(f"{board_title}\nNo tasks due today!")
        return

    tz = pytz.timezone(TIMEZONE)
    task_map = {}
    today_str = datetime.now(tz).strftime("%B %d, %Y")

    for task in tasks:
        task_name = task.get("name", "No title")
        task_url = task.get("url", "")
        due_ts = task.get("due_date")
        status = task.get("status", {}).get("status", "Unknown")

        # Format due time
        if due_ts:
            due_dt = datetime.fromtimestamp(int(due_ts) / 1000, tz)
            due_str = due_dt.strftime("%B %d, %Y")
        else:
            due_str = "No due time"

        # Assignees
        assignees = task.get("assignees", [])
        if not assignees:
            assignees = [{"name": "Unassigned"}]

        for a in assignees:
            name = a.get("name") or a.get("username") or a.get("email") or "Unassigned"
            if name not in task_map:
                task_map[name] = []
            task_map[name].append(f"- [{task_name}]({task_url}) ({due_str}) - *{status}*")

    # Compose final message
    msg = f"{board_title} ({today_str})\n"
    for name, items in task_map.items():
        msg += f"\n*{name}* is assigned at:\n" + "\n".join(items) + "\n"

    send_to_telegram(msg + "\n")

# === MAIN ===
if __name__ == "__main__":
    print("Sending today's task summaries...")
    for board in LISTS:
        daily_task_summary(board["id"], board["title"])
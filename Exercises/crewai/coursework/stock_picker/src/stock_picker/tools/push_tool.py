import os

import requests
from crewai.tools import tool  # type: ignore[import-not-found]


@tool("Send Push Notification")
def send_push_notification(message: str) -> str:
    """
    Tool to send push notifications

    Args:
        message (str): Message to be sent as push notification to the user

    Returns:
        str: A string indicating the status of push notifications
    """
    pushover_user = os.getenv("PUSHOVER_USER")
    pushover_token = os.getenv("PUSHOVER_TOKEN")
    pushover_url = "https://api.pushover.net/1/messages.json"
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    try:
        result = requests.post(pushover_url, data=payload).status_code
        return f"Push notification sent with API response {result}"
    except Exception as e:
        return f"Failed to send push notification: {str(e)}"

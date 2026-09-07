import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

from agents import Agent, function_tool

load_dotenv()
OPENAI_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5.4-nano")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_SERVER = os.getenv("EMAIL_SERVER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

if not EMAIL_ADDRESS or not EMAIL_SERVER or not EMAIL_APP_PASSWORD:
    print("Email configuration not received")

USE_EMAIL = EMAIL_ADDRESS and EMAIL_SERVER and EMAIL_APP_PASSWORD

print("Email setup completed") if USE_EMAIL else print("Email setup failed")


# Test the email
def send_email(subject, text_body, html_body):
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(EMAIL_SERVER, 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        print("Email sent")


@function_tool
def send_email_tool(subject: str, text_body: str, html_body: str) -> str:
    """
    Send out an email with the given subject and body to all sales prospects

    Args:
        subject: The subject of the email
        text_body: The body of the email as plain text
        html_body: The HTML body of the email
    """
    send_email(subject, text_body, html_body)


INSTRUCTIONS = """
You are provided with a detailed report. Use your tool to send an email, converting the report into
a clean, well presented HTML email with an appropriate subject line.
"""


email_agent = Agent(
    name="Email Agent", instructions=INSTRUCTIONS, model=OPENAI_MODEL, tools=[send_email_tool]
)

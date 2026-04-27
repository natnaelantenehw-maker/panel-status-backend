import os
import aiosmtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


async def send_email(to_email: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = SMTP_USER
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        start_tls=True,
        username=SMTP_USER,
        password=SMTP_PASS,
    )


async def send_admin_request_email(user_email: str):
    subject = "New App Access Request"
    body = f"A new user requested access:\n\nEmail: {user_email}"
    await send_email(ADMIN_EMAIL, subject, body)


async def send_user_code_email(user_email: str, code: str, duration_label: str):
    subject = "Your App Access Code"
    body = (
        f"Your access code is: {code}\n\n"
        f"Access duration: {duration_label}\n"
        f"Enter this code in the app."
    )
    await send_email(user_email, subject, body)
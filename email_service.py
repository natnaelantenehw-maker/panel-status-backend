import os
import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


def send_email(to_email: str, subject: str, body: str):
    url = "https://api.resend.com/emails"

    payload = {
        "from": "onboarding@resend.dev",
        "to": [to_email],
        "subject": subject,
        "text": body
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Email failed: {response.text}")


def send_admin_request_email(user_email: str):
    subject = "New App Access Request"
    body = f"A new user requested access:\n\nEmail: {user_email}"
    send_email(ADMIN_EMAIL, subject, body)


def send_user_code_email(user_email: str, code: str, duration_label: str):
    subject = "Your App Access Code"
    body = f"Your code: {code}\n\nAccess duration: {duration_label}"
    send_email(user_email, subject, body)
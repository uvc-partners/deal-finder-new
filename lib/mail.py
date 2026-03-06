import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

from lib.utils import *

load_dotenv()


def get_today_str():
    return datetime.today().strftime('%Y-%m-%d')


# Email configuration (from .env)
sender_email = os.environ["EMAIL_SENDER"]
password = os.environ["EMAIL_APP_PASSWORD"]


#  CC addresses must be a comma-separated string: "email1@gmail.com, email2@gmail.com, etc@gmail.com"
def send_email(receiver_emails, subject, html_content, cc_emails=None):
    # Ensure that receiver_emails is a list of strings (emails)
    if isinstance(receiver_emails, str):
        receiver_emails = [receiver_emails]  # If it's a single email, convert it to a list

    # Create the email message
    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = ", ".join(receiver_emails)  # Join the list of emails into a comma-separated string
    msg['Subject'] = subject

    if cc_emails is not None:
        msg['Cc'] = ", ".join(cc_emails)  # Join the CC emails if provided

    # Attach the HTML content to the email
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)

    # Combine the receiver emails and cc emails to send to all recipients
    all_recipients = receiver_emails + (cc_emails if cc_emails is not None else [])

    # Connect to the Gmail SMTP server and send the email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, all_recipients, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise


def get_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        file = file.read()
    return file

def replace_content_variables(html_file, content_variables):
    for key, value in content_variables.items():
        html_file = html_file.replace("{{" + key + "}}", value)

    return html_file

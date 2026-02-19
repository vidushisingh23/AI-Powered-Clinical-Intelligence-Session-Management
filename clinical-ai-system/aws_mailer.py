import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SES_HOST = os.getenv("AWS_SES_HOST")
SES_PORT = int(os.getenv("AWS_SES_PORT"))
SES_USER = os.getenv("AWS_SES_USERNAME")
SES_PASS = os.getenv("AWS_SES_PASSWORD")
SENDER = os.getenv("SES_VERIFIED_SENDER")


def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = SENDER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SES_HOST, SES_PORT) as server:
        server.starttls()
        server.login(SES_USER, SES_PASS)
        server.sendmail(SENDER, to_email, msg.as_string())
  
    

import smtplib, ssl
from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app, render_template
from jinja2 import TemplateNotFound

from hackspace_storage.models import User

def send_email(user: User, template: str, subject: str, **kwargs):
    sender_email = current_app.config["SENDER_EMAIL"]

    plain_content = render_template(f"{template}.txt.j2", user=user, **kwargs)
    try:
        html_content = render_template(f"{template}.html.j2", user=user, **kwargs)
    except TemplateNotFound:
        html_content = None

    receiver_email = formataddr((user.name, user.email))

    if current_app.config.get("SMTP_HOST"):
        send_fn = send_smtp_email
    else:
        send_fn = send_logger_email

    send_fn(sender_email, receiver_email, plain_content, html_content, subject)


def send_smtp_email(sender: str, receiver: str, text: str, html: str|None, subject:str):
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    port = current_app.config.get("SMTP_PORT", 465)
    host = current_app.config["SMTP_HOST"]
    username = current_app.config["SMTP_USERNAME"]
    password = current_app.config["SMTP_PASSWORD"]

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(username, password)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = receiver

        message.attach(MIMEText(text, "plain"))

        if html:
            message.attach(MIMEText(html, "html"))

        server.sendmail(sender, receiver, message.as_string())


def send_logger_email(sender: str, receiver: str, text: str, html: str|None):
    current_app.logger.info(f"Sending email from {sender} to {receiver}: {subject} \n\n {text}")
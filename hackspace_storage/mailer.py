import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app, render_template
from jinja2 import TemplateNotFound

from hackspace_storage.models import User

def send_email(receiver_email: str, template: str, **kwargs):
    # context = ssl.create_default_context()
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    port = current_app.config.get("SMTP_PORT", 465)
    host = current_app.config["SMTP_HOST"]
    username = current_app.config["SMTP_USERNAME"]
    password = current_app.config["SMTP_PASSWORD"]

    sender_email = current_app.config["SENDER_EMAIL"]

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(username, password)

        message = MIMEMultipart("alternative")
        message["Subject"] = "Hello from python"
        message["From"] = sender_email
        message["To"] = receiver_email

        user = None
        plain_content = render_template(f"{template}.txt", user=user, **kwargs)
        plain_text = MIMEText(plain_content, "plain")
        message.attach(plain_text)

        try:
            html_content = render_template(f"{template}.html", user=user, **kwargs)
            html_text = MIMEText(html_content, "html")
            message.attach(html_text)
        except TemplateNotFound:
            pass

        server.sendmail(sender_email, receiver_email, message.as_string())
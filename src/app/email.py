from flask import Flask, current_app
from flask_mail import Message
from threading import Thread

from app import mail

from typing import List, Optional as Opt, Tuple, AnyStr
from app.types import HTML


def send_async_email(app: Flask, msg: Message) -> None:
    with app.app_context():
        mail.send(msg)


def send_email(subject: str,
               sender: str,
               recipients: List[str],
               text_body: str,
               html_body: HTML,
               attachments: Opt[List[Tuple[str, str, AnyStr]]] = None,
               sync: bool = False) -> None:
    """ # cc bcc field also possible"""
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    if attachments is not None:
        for attachment in attachments:  # for tuple in list
            msg.attach(*attachment)  # unpack tuple as *args (filename. mimetype, data)

    if sync:
        mail.send(msg)
    else:
        Thread(target=send_async_email,
               args=(current_app._get_current_object(), msg)).start()

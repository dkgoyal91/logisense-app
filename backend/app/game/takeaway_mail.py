"""Compose and send the 'repo + build prompt' takeaway email over SMTP (Gmail app password by default)."""
from __future__ import annotations

import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

from app.game.models import GameError

MAX_EMAIL_LENGTH = 254
EMAIL_PATTERN = re.compile(r'^[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$')
SMTP_TIMEOUT_SECONDS = 20
SUBJECT = 'Your LogiSense copilot kit from Flo 2026'
PROMPT_PATH = 'blob/main/docs/demo/build-your-own-prompt.md'
SPEAKERS = 'Rachit Singhal, Dinesh Kumar, Sunil Gupta, Gaurav Tyagi and Punhik Gandhi (Nagarro)'


@dataclass(frozen=True)
class MailSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    from_address: str | None
    from_name: str
    repo_url: str

    @property
    def is_configured(self) -> bool:
        return bool(self.username and self.password and self.from_address)

    @property
    def clone_command(self) -> str:
        return f'git clone {self.repo_url.rstrip("/")}.git'

    @property
    def prompt_url(self) -> str:
        return f'{self.repo_url.rstrip("/")}/{PROMPT_PATH}'


# Addresses -------------------------------------------------------------------------------

def normalize_email(raw: str) -> str:
    email = str(raw or '').strip()
    if len(email) > MAX_EMAIL_LENGTH or not EMAIL_PATTERN.match(email):
        raise GameError('Please enter a valid email address.')
    local, domain = email.rsplit('@', 1)
    return f'{local}@{domain.lower()}'


def mask_email(email: str) -> str:
    local, domain = email.rsplit('@', 1)
    return f'{local[:1]}•••@{domain}'


# Message ---------------------------------------------------------------------------------

def build_takeaway_message(to_address: str, player_name: str, settings: MailSettings) -> EmailMessage:
    message = EmailMessage()
    message['Subject'] = SUBJECT
    message['From'] = formataddr((settings.from_name, settings.from_address or ''))
    message['To'] = to_address
    message.set_content(plain_body(player_name, settings))
    message.add_alternative(_html_body(player_name, settings), subtype='html')
    return message


def plain_body(player_name: str, settings: MailSettings) -> str:
    return (
        f'Hi {player_name},\n\n'
        'Thanks for playing Beat the Copilot at Flo 2026! Here is everything you need to build your own '
        'logistics AI copilot.\n\n'
        f'Repo: {settings.repo_url}\n'
        f'Clone it: {settings.clone_command}\n'
        f'Build-your-own prompt (paste into any AI coding agent): {settings.prompt_url}\n\n'
        'It runs with no API key. Python 3.12 and Node 18+ are the only prerequisites.\n\n'
        f'See you around,\n{SPEAKERS}\n'
    )


def _html_body(player_name: str, settings: MailSettings) -> str:
    repo, prompt, clone = escape(settings.repo_url), escape(settings.prompt_url), escape(settings.clone_command)
    return (
        '<div style="font-family:Arial,sans-serif;font-size:15px;color:#0f172a;line-height:1.5">'
        f'<p>Hi {escape(player_name)},</p>'
        '<p>Thanks for playing <b>Beat the Copilot</b> at Flo 2026! Here is everything you need to build your own '
        'logistics AI copilot.</p>'
        f'<p><b>Repo:</b> <a href="{repo}">{repo}</a></p>'
        f'<p><b>Clone it:</b><br><code style="background:#f1f5f9;padding:4px 8px;border-radius:6px">{clone}</code></p>'
        f'<p><b>Build-your-own prompt</b> (paste into any AI coding agent): <a href="{prompt}">{prompt}</a></p>'
        '<p>It runs with no API key. Python 3.12 and Node 18+ are the only prerequisites.</p>'
        f'<p>See you around,<br>{escape(SPEAKERS)}</p></div>'
    )


# Sending ---------------------------------------------------------------------------------

class SmtpSender:
    def __init__(self, settings: MailSettings) -> None:
        self._settings = settings

    def send(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self._settings.host, self._settings.port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(self._settings.username or '', self._settings.password or '')
            smtp.send_message(message)

import pytest

from app.game.models import GameError
from app.game.takeaway_mail import (
    MailSettings,
    SmtpSender,
    build_takeaway_message,
    mask_email,
    normalize_email,
)

SETTINGS = MailSettings(
    host='smtp.gmail.com', port=587, username='flo.demo@gmail.com', password='app-password',
    from_address='flo.demo@gmail.com', from_name='LogiSense @ Flo 2026',
    repo_url='https://github.com/dkgoyal91/logisense-app',
)


def test_normalize_email_trims_and_lowercases_the_domain() -> None:
    assert normalize_email('  Ananya.Rao@Nagarro.COM ') == 'Ananya.Rao@nagarro.com'


@pytest.mark.parametrize('raw', ['', 'not-an-email', 'a@b', 'two@@at.com', 'space in@x.com', 'x' * 250 + '@a.com', 'a@b.com\nBcc: x@y.com'])
def test_normalize_email_rejects_invalid_or_injected_addresses(raw: str) -> None:
    with pytest.raises(GameError, match='valid email'):
        normalize_email(raw)


def test_mask_email_hides_the_local_part() -> None:
    assert mask_email('ananya@nagarro.com') == 'a•••@nagarro.com'


def test_takeaway_message_carries_the_repo_clone_command_and_prompt_link() -> None:
    message = build_takeaway_message('ananya@nagarro.com', 'Ananya', SETTINGS)
    text = message.get_body(('plain',)).get_content()
    html = message.get_body(('html',)).get_content()
    assert message['To'] == 'ananya@nagarro.com'
    assert message['From'] == '"LogiSense @ Flo 2026" <flo.demo@gmail.com>'
    assert 'LogiSense' in message['Subject']
    for body in (text, html):
        assert 'git clone https://github.com/dkgoyal91/logisense-app.git' in body
        assert 'https://github.com/dkgoyal91/logisense-app/blob/main/docs/demo/build-your-own-prompt.md' in body
        assert 'Ananya' in body


def test_takeaway_message_escapes_the_player_name_in_html() -> None:
    message = build_takeaway_message('x@y.com', '<b>Eve</b>', SETTINGS)
    html = message.get_body(('html',)).get_content()
    assert '<b>Eve</b>' not in html
    assert '&lt;b&gt;Eve&lt;/b&gt;' in html


def test_mail_settings_need_username_password_and_sender() -> None:
    assert SETTINGS.is_configured is True
    assert MailSettings(host='smtp.gmail.com', port=587, username=None, password=None, from_address=None,
                        from_name='x', repo_url='r').is_configured is False


class FakeSmtp:
    instances: list['FakeSmtp'] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.calls = [('connect', host, port)]
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        self.calls.append(('quit',))

    def starttls(self, context=None) -> None:
        self.calls.append(('starttls',))

    def login(self, username: str, password: str) -> None:
        self.calls.append(('login', username, password))

    def send_message(self, message) -> None:
        self.calls.append(('send', message['To']))


def test_smtp_sender_uses_starttls_and_logs_in_before_sending(monkeypatch) -> None:
    from app.game import takeaway_mail

    FakeSmtp.instances.clear()
    monkeypatch.setattr(takeaway_mail.smtplib, 'SMTP', FakeSmtp)
    SmtpSender(SETTINGS).send(build_takeaway_message('ananya@nagarro.com', 'Ananya', SETTINGS))
    assert FakeSmtp.instances[0].calls == [
        ('connect', 'smtp.gmail.com', 587), ('starttls',), ('login', 'flo.demo@gmail.com', 'app-password'),
        ('send', 'ananya@nagarro.com'), ('quit',),
    ]


def test_takeaway_message_lists_the_prerequisites_for_mac_and_windows() -> None:
    message = build_takeaway_message('ananya@nagarro.com', 'Ananya', SETTINGS)
    for body in (message.get_body(('plain',)).get_content(), message.get_body(('html',)).get_content()):
        assert 'Python 3.10 or newer' in body
        assert 'Add python.exe to PATH' in body
        assert 'Node.js 20.19 or newer' in body
        assert 'Node 22 LTS' in body
        assert 'No API key needed' in body
        assert 'py --version' in body and 'python3 --version' in body and 'node --version' in body
        assert 'Node 18+' not in body

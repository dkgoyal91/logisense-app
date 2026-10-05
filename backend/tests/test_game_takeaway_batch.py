from pathlib import Path

from app.game.takeaway import TakeawayLog
from app.game.takeaway_batch import batch_text, mark_sent, pending_recipients, read_log
from app.game.takeaway_mail import MailSettings

SETTINGS = MailSettings(host='smtp.gmail.com', port=587, username=None, password=None, from_address=None,
                        from_name='LogiSense @ Flo 2026', repo_url='https://github.com/dkgoyal91/logisense-app')


def _log(tmp_path: Path, *rows: tuple[str, str, str]) -> Path:
    path = tmp_path / 'takeaway.csv'
    log = TakeawayLog(path)
    for name, email, status in rows:
        log.record(name, email, status)
    return path


def test_pending_recipients_are_unique_case_insensitive_and_skip_already_sent(tmp_path: Path) -> None:
    path = _log(tmp_path,
                ('Ananya', 'ananya@nagarro.com', 'pending'),
                ('Ananya2', 'Ananya@Nagarro.com', 'pending'),
                ('Rohan', 'rohan@example.com', 'failed'),
                ('Meera', 'meera@example.com', 'pending'),
                ('Meera', 'meera@example.com', 'sent'))
    assert pending_recipients(read_log(path)) == ['ananya@nagarro.com', 'rohan@example.com']


def test_missing_log_means_nobody_to_email(tmp_path: Path) -> None:
    assert pending_recipients(read_log(tmp_path / 'missing.csv')) == []


def test_batch_text_has_subject_bcc_and_a_generic_greeting() -> None:
    text = batch_text(['a@x.com', 'b@y.com'], SETTINGS)
    assert 'Subject: Your LogiSense copilot kit from Flo 2026' in text
    assert 'BCC (2): a@x.com, b@y.com' in text
    assert 'Hi there,' in text
    assert 'git clone https://github.com/dkgoyal91/logisense-app.git' in text


def test_mark_sent_records_each_recipient_so_a_rerun_skips_them(tmp_path: Path) -> None:
    path = _log(tmp_path, ('Ananya', 'ananya@nagarro.com', 'pending'), ('Rohan', 'rohan@example.com', 'pending'))
    mark_sent(TakeawayLog(path), ['ananya@nagarro.com', 'rohan@example.com'])
    assert pending_recipients(read_log(path)) == []

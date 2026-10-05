"""After the session: one BCC email to everyone who asked (run from the backend folder):

    ../.venv/bin/python -m app.game.takeaway_batch              # writes data/takeaway_batch.txt
    ../.venv/bin/python -m app.game.takeaway_batch --mark-sent  # after you sent it, so a rerun skips them
"""
from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from app.config import resolve_backend_path, settings
from app.game.takeaway import Sender, TakeawayLog
from app.game.takeaway_mail import GENERIC_GREETING_NAME, SUBJECT, MailSettings, build_bcc_message, plain_body

BATCH_FILE = 'data/takeaway_batch.txt'
MAX_DETAIL_LENGTH = 200


def read_log(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def pending_recipients(rows: list[dict[str, str]]) -> list[str]:
    already_sent = {row['email'].lower() for row in rows if row['status'] == 'sent'}
    recipients: dict[str, str] = {}
    for row in rows:
        key = row['email'].lower()
        if key not in already_sent:
            recipients.setdefault(key, _normalised(row['email']))
    return list(recipients.values())


def _normalised(email: str) -> str:
    local, domain = email.rsplit('@', 1)
    return f'{local.lower()}@{domain.lower()}'


def batch_text(recipients: list[str], mail: MailSettings) -> str:
    return (
        f'Subject: {SUBJECT}\n'
        f'BCC ({len(recipients)}): {", ".join(recipients)}\n\n'
        f'{plain_body(GENERIC_GREETING_NAME, mail)}'
    )


def mark_sent(log: TakeawayLog, recipients: list[str]) -> None:
    for email in recipients:
        log.record('batch', email, 'sent', 'sent in the post-session BCC email')


class TakeawayBroadcaster:
    """The host's 'Send email to everyone' button: one BCC email to every pending address, then mark them sent."""

    def __init__(self, settings: MailSettings, log: TakeawayLog, sender: Sender | None) -> None:
        self._settings = settings
        self._log = log
        self._sender = sender

    @property
    def can_send(self) -> bool:
        return self._sender is not None and bool(self._settings.from_address)

    def pending(self) -> list[str]:
        return pending_recipients(read_log(self._log.path))

    async def send(self, recipients: list[str]) -> tuple[str, str]:
        try:
            await asyncio.to_thread(self._sender.send, build_bcc_message(recipients, self._settings))
        except Exception as exc:  # reported on the host remote and projector; addresses stay pending for a retry
            return 'failed', f'{type(exc).__name__}: {exc}'[:MAX_DETAIL_LENGTH]
        mark_sent(self._log, recipients)
        return 'sent', ''


def _mail_settings() -> MailSettings:
    return MailSettings(host=settings.smtp_host, port=settings.smtp_port, username=None, password=None,
                        from_address=None, from_name=settings.mail_from_name, repo_url=settings.takeaway_repo_url)


def main() -> None:
    parser = argparse.ArgumentParser(description='Prepare (or record) the one post-session takeaway email.')
    parser.add_argument('--mark-sent', action='store_true', help='Record everyone pending as sent')
    args = parser.parse_args()
    log = TakeawayLog(resolve_backend_path(settings.takeaway_log_path))
    recipients = pending_recipients(read_log(log.path))
    if args.mark_sent:
        mark_sent(log, recipients)
        print(f'Marked {len(recipients)} recipient(s) as sent.')
        return
    target = resolve_backend_path(BATCH_FILE)
    target.write_text(batch_text(recipients, _mail_settings()), encoding='utf-8')
    print(f'{len(recipients)} unique recipient(s). Batch written to {target}')


if __name__ == '__main__':
    main()

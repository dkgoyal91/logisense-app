"""Tests for run.py's cross-platform process helpers (Windows behaviour is simulated)."""
import signal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run  # noqa: E402


def test_npm_command_uses_the_resolved_path_so_windows_finds_npm_cmd(monkeypatch) -> None:
    monkeypatch.setattr(run.shutil, 'which', lambda name: r'C:\Program Files\nodejs\npm.CMD' if name == 'npm' else None)
    assert run._npm_command('run', 'dev') == [r'C:\Program Files\nodejs\npm.CMD', 'run', 'dev']


def test_npm_command_explains_a_missing_node_install(monkeypatch) -> None:
    monkeypatch.setattr(run.shutil, 'which', lambda _name: None)
    with pytest.raises(RuntimeError, match='npm was not found'):
        run._npm_command('install')


def test_terminate_tree_uses_taskkill_on_windows(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(run.os, 'name', 'nt')
    monkeypatch.setattr(run.subprocess, 'run', lambda args, **_kwargs: calls.append(args))
    assert run._terminate_tree(4242) is True
    assert calls == [['taskkill', '/PID', '4242', '/T', '/F']]


def test_terminate_tree_signals_the_process_elsewhere(monkeypatch) -> None:
    sent = []
    monkeypatch.setattr(run.os, 'name', 'posix')
    monkeypatch.setattr(run.os, 'kill', lambda pid, sig: sent.append((pid, sig)))
    assert run._terminate_tree(4242) is True
    assert sent == [(4242, signal.SIGTERM)]


def test_terminate_tree_reports_an_already_stopped_process(monkeypatch) -> None:
    def gone(_pid, _sig):
        raise ProcessLookupError

    monkeypatch.setattr(run.os, 'name', 'posix')
    monkeypatch.setattr(run.os, 'kill', gone)
    assert run._terminate_tree(4242) is False


def test_stale_pid_file_from_another_machine_does_not_block_startup(tmp_path, monkeypatch) -> None:
    pid_file = tmp_path / '.logisense-local.pid'
    pid_file.write_text('{"backend": 999991, "frontend": 999992}')
    monkeypatch.setattr(run, '_pid_file', lambda: pid_file)
    monkeypatch.setattr(run, '_has_local_process_running', lambda: False)
    monkeypatch.setattr(run, '_process_alive', lambda _pid: False)
    run._ensure_local_services_not_running()
    assert not pid_file.exists()


def test_live_pid_file_still_blocks_a_second_start(tmp_path, monkeypatch) -> None:
    pid_file = tmp_path / '.logisense-local.pid'
    pid_file.write_text('{"backend": 111, "frontend": 222}')
    monkeypatch.setattr(run, '_pid_file', lambda: pid_file)
    monkeypatch.setattr(run, '_has_local_process_running', lambda: False)
    monkeypatch.setattr(run, '_process_alive', lambda pid: pid == 111)
    with pytest.raises(RuntimeError, match='already appear to be running'):
        run._ensure_local_services_not_running()


def test_process_alive_asks_tasklist_on_windows(monkeypatch) -> None:
    class Result:
        stdout = 'python.exe                    4242 Console    1     50,000 K'

    monkeypatch.setattr(run.os, 'name', 'nt')
    monkeypatch.setattr(run.subprocess, 'run', lambda *_args, **_kwargs: Result())
    assert run._process_alive(4242) is True
    assert run._process_alive(4343) is False

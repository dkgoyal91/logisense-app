#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / 'backend'
FRONTEND_DIR = ROOT / 'frontend'


def _pid_file() -> Path:
    instance_id = os.environ.get('LOGISENSE_INSTANCE', '').strip()
    if instance_id:
        return ROOT / f'.logisense-local-{instance_id}.pid'
    return ROOT / '.logisense-local.pid'


def _log(message: str) -> None:
    print(f'[logisense] {message}')


def _find_python_312() -> str:
    candidates: list[str] = []

    env_python = os.environ.get('PYTHON_BIN')
    if env_python:
        candidates.append(env_python)

    candidates.extend(
        [
            'python3.12',
            'python3',
            'py',
            sys.executable,
        ]
    )

    common_paths = [
        '/opt/homebrew/bin/python3.12',
        '/usr/local/bin/python3.12',
        '/usr/bin/python3.12',
        'C:/Python312/python.exe',
        'C:/Users/%USERNAME%/AppData/Local/Programs/Python/Python312/python.exe',
    ]
    for path in common_paths:
        expanded = os.path.expandvars(path)
        expanded = os.path.expanduser(expanded)
        if expanded:
            candidates.append(expanded)

    for candidate in candidates:
        if not candidate:
            continue

        try:
            if candidate.lower() == 'py':
                result = subprocess.run(
                    ['py', '-3.12', '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            else:
                result = subprocess.run(
                    [candidate, '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
                    capture_output=True,
                    text=True,
                    check=True,
                )
        except Exception:
            continue

        version = result.stdout.strip()
        if version.startswith('3.12'):
            return candidate

    raise RuntimeError('Python 3.12 is required. Install Python 3.12 or point PYTHON_BIN to it.')


def _venv_python() -> Path:
    venv_dir = ROOT / '.venv'
    if os.name == 'nt':
        return venv_dir / 'Scripts' / 'python.exe'
    return venv_dir / 'bin' / 'python'


def _venv_python_version(venv_python: Path) -> str | None:
    if not venv_python.exists():
        return None
    try:
        result = subprocess.run(
            [str(venv_python), '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    return result.stdout.strip()


def _ensure_venv(python_executable: str) -> Path:
    venv_python = _venv_python()
    venv_version = _venv_python_version(venv_python)
    if venv_python.exists() and venv_version == '3.12':
        return venv_python
    if venv_python.exists() and venv_version and venv_version != '3.12':
        _log(f'Recreating .venv because it is using Python {venv_version}, not Python 3.12.')
        shutil.rmtree(ROOT / '.venv', ignore_errors=True)
    if not venv_python.exists():
        _log('Creating Python 3.12 virtual environment in .venv')
        subprocess.run([python_executable, '-m', 'venv', str(ROOT / '.venv')], check=True)
    return venv_python


def _ensure_local_dependencies() -> None:
    venv_python = _ensure_venv(_find_python_312())
    _log('Installing backend dependencies')
    subprocess.run([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
    subprocess.run([str(venv_python), '-m', 'pip', 'install', '-r', str(BACKEND_DIR / 'requirements.txt')], check=True)

    if not (FRONTEND_DIR / 'node_modules').exists():
        _log('Installing frontend dependencies')
        subprocess.run(['npm', 'install'], cwd=str(FRONTEND_DIR), check=True)


def _backend_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault('PYTHONUNBUFFERED', '1')
    env.setdefault('DATABASE_PATH', 'data/logisense.db')
    return env


def _start_local() -> None:
    _ensure_local_dependencies()
    venv_python = _ensure_venv(_find_python_312())
    backend_port = os.environ.get('BACKEND_PORT', '8000')
    frontend_port = os.environ.get('FRONTEND_PORT', '5173')

    backend_process = subprocess.Popen(
        [str(venv_python), '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', backend_port],
        cwd=str(BACKEND_DIR),
        env=_backend_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    frontend_process = subprocess.Popen(
        ['npm', 'run', 'dev', '--', '--host', '0.0.0.0', '--port', frontend_port],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    _pid_file().write_text(json.dumps({'backend': backend_process.pid, 'frontend': frontend_process.pid}))

    _log('Local services started.')
    _log(f'Backend: http://localhost:{backend_port}')
    _log(f'Frontend: http://localhost:{frontend_port}')
    _log('Use: python3 run.py stop to stop both services')


def _stop_local() -> None:
    pid_file = _pid_file()
    if not pid_file.exists():
        _log('No local process file found; nothing to stop.')
        return

    try:
        pids = json.loads(pid_file.read_text())
    except Exception:
        _log('Could not read local PID file; removing stale state.')
        pid_file.unlink(missing_ok=True)
        return

    for key in ('backend', 'frontend'):
        pid = pids.get(key)
        if not pid:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    pid_file.unlink(missing_ok=True)
    _log('Stopped local services.')


def _compose_command(*args: str) -> list[str]:
    docker_cli = shutil.which('docker')
    docker_compose = shutil.which('docker-compose')

    if docker_cli:
        try:
            subprocess.run([docker_cli, 'compose', 'version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return [docker_cli, 'compose', *args]
        except Exception:
            pass

    if docker_compose:
        return [docker_compose, *args]

    raise RuntimeError('Docker is required for the Docker mode. Install Docker Desktop or Docker Engine.')


def _start_docker() -> None:
    subprocess.run(_compose_command('up', '--build', '-d'), cwd=str(ROOT), check=True)
    _log('Docker services started.')
    _log('Backend: http://localhost:8000')
    _log('Frontend: http://localhost:5173')


def _stop_docker() -> None:
    subprocess.run(_compose_command('down', '--remove-orphans', '--volumes'), cwd=str(ROOT), check=True)
    _log('Docker services stopped.')


def _status_docker() -> None:
    subprocess.run(_compose_command('ps'), cwd=str(ROOT), check=True)


def _ensure_docker_compose_file() -> None:
    compose_candidates = ['docker-compose.yml', 'compose.yml', 'docker-compose.yaml', 'compose.yaml']
    for name in compose_candidates:
        if (ROOT / name).exists():
            return
    raise FileNotFoundError('No Docker Compose file was found in the repo root.')


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='LogiSense launcher for Python 3.12 local or Docker-based startup.')
    parser.add_argument('mode', choices=['local', 'docker', 'start', 'stop', 'restart', 'status'], nargs='?')
    parser.add_argument('--python', dest='python_bin', default=None, help='Explicit Python 3.12 binary to use for the local mode.')
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.python_bin:
        os.environ['PYTHON_BIN'] = args.python_bin

    try:
        if args.mode in (None, 'start', 'local'):
            if args.mode == 'start':
                _log('Using local startup mode. Use docker for containerized mode.')
            _start_local()
            return 0
        if args.mode == 'docker':
            _ensure_docker_compose_file()
            _start_docker()
            return 0
        if args.mode == 'stop':
            if _pid_file().exists():
                _stop_local()
            else:
                _ensure_docker_compose_file()
                _stop_docker()
            return 0
        if args.mode == 'restart':
            if _pid_file().exists():
                _stop_local()
                _start_local()
                return 0
            _ensure_docker_compose_file()
            _stop_docker()
            _start_docker()
            return 0
        if args.mode == 'status':
            if _pid_file().exists():
                _log('Local services are running via PID file.')
                return 0
            _ensure_docker_compose_file()
            _status_docker()
            return 0
    except Exception as exc:  # pragma: no cover - CLI-level fail-safe
        _log(f'Error: {exc}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

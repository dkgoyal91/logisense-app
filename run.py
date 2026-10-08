#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / 'backend'
FRONTEND_DIR = ROOT / 'frontend'


def _is_supported_python_version(version: str) -> bool:
    return version in {'3.12', '3.13'}


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
            'python3.13',
            'python3.12',
            'python3',
            'py',
            sys.executable,
        ]
    )

    common_paths = [
        '/opt/homebrew/bin/python3.13',
        '/opt/homebrew/bin/python3.12',
        '/usr/local/bin/python3.13',
        '/usr/local/bin/python3.12',
        '/usr/bin/python3.13',
        '/usr/bin/python3.12',
        'C:/Python312/python.exe',
        'C:/Python313/python.exe',
        'C:/Users/%USERNAME%/AppData/Local/Programs/Python/Python312/python.exe',
        'C:/Users/%USERNAME%/AppData/Local/Programs/Python/Python313/python.exe',
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
                    ['py', '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
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
        if _is_supported_python_version(version[:4]):
            return candidate

    raise RuntimeError('Python 3.12 or 3.13 is required. Install a supported Python version or point PYTHON_BIN to it.')


def _venv_python() -> Path:
    venv_dir = ROOT / '.venv'
    if os.name == 'nt':
        return venv_dir / 'Scripts' / 'python.exe'
    return venv_dir / 'bin' / 'python'


def _local_log_file(service_name: str) -> Path:
    instance_id = os.environ.get('LOGISENSE_INSTANCE', '').strip()
    suffix = f'-{instance_id}' if instance_id else ''
    return ROOT / f'.logisense-{service_name}{suffix}.log'


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


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
    if venv_python.exists() and venv_version and _is_supported_python_version(venv_version[:4]):
        return venv_python
    if venv_python.exists() and venv_version and not _is_supported_python_version(venv_version[:4]):
        _log(f'Recreating .venv because it is using Python {venv_version}, not a supported Python 3.12/3.13 runtime.')
        shutil.rmtree(ROOT / '.venv', ignore_errors=True)
    if not venv_python.exists():
        _log('Creating Python 3.12/3.13 virtual environment in .venv')
        subprocess.run([python_executable, '-m', 'venv', str(ROOT / '.venv')], check=True)
    return venv_python


def _frontend_dependencies_need_install() -> bool:
    node_modules_dir = FRONTEND_DIR / 'node_modules'
    package_json = FRONTEND_DIR / 'package.json'
    package_lock = FRONTEND_DIR / 'package-lock.json'
    lock_stamp = node_modules_dir / '.package-lock.json'

    if not node_modules_dir.exists():
        return True

    if not package_lock.exists():
        return False

    if not lock_stamp.exists():
        return True

    manifest_mtime = max(package_json.stat().st_mtime, package_lock.stat().st_mtime)
    return lock_stamp.stat().st_mtime < manifest_mtime


def _npm_command() -> str:
    resolved = shutil.which('npm.cmd') or shutil.which('npm')
    if resolved:
        return resolved
    raise RuntimeError('npm was not found. Install Node.js or ensure npm is available on PATH.')


def _ensure_local_dependencies() -> None:
    venv_python = _ensure_venv(_find_python_312())
    _log('Installing backend dependencies')
    subprocess.run([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
    subprocess.run([str(venv_python), '-m', 'pip', 'install', '-r', str(BACKEND_DIR / 'requirements.txt')], check=True)

    if _frontend_dependencies_need_install():
        _log('Installing frontend dependencies')
        subprocess.run([_npm_command(), 'install'], cwd=str(FRONTEND_DIR), check=True)


def _ensure_local_services_not_running() -> None:
    pid_file = _pid_file()
    if pid_file.exists():
        try:
            pids = json.loads(pid_file.read_text())
        except Exception:
            pid_file.unlink(missing_ok=True)
        else:
            if any(_is_process_alive(int(pids.get(name, 0) or 0)) for name in ('backend', 'frontend')):
                raise RuntimeError('Local services already appear to be running. Stop them first with: python3 run.py stop')
            pid_file.unlink(missing_ok=True)

    if _has_local_process_running():
        raise RuntimeError('Local services already appear to be running. Stop them first with: python3 run.py stop')


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.25)
        return connection.connect_ex((host, port)) == 0


def _wait_for_startup(
    processes: dict[str, subprocess.Popen[str]],
    ports: dict[str, int],
    timeout_seconds: float = 10.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        failed_service = next((name for name, process in processes.items() if process.poll() is not None), None)
        if failed_service:
            break
        if all(_is_port_open('127.0.0.1', port) for port in ports.values()):
            return
        time.sleep(0.2)

    failed_service = next((name for name, process in processes.items() if process.poll() is not None), None)

    for name, process in processes.items():
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()

    _pid_file().unlink(missing_ok=True)

    if failed_service:
        failed_process = processes[failed_service]
        log_file = _local_log_file(failed_service)
        raise RuntimeError(
            f'{failed_service.title()} failed to start (exit code {failed_process.returncode}). '
            f'Check {log_file.name} for details.'
        )

    pending_services = ', '.join(name for name, port in ports.items() if not _is_port_open('127.0.0.1', port))
    raise RuntimeError(
        f'Local services did not become reachable in time: {pending_services}. '
        'Check the local service logs for details.'
    )


def _backend_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault('PYTHONUNBUFFERED', '1')
    env.setdefault('DATABASE_PATH', 'data/logisense.db')
    return env


def _start_local() -> None:
    _ensure_local_dependencies()
    _ensure_local_services_not_running()
    venv_python = _ensure_venv(_find_python_312())
    backend_port = os.environ.get('BACKEND_PORT', '8000')
    frontend_port = os.environ.get('FRONTEND_PORT', '5173')

    backend_log = _local_log_file('backend')
    frontend_log = _local_log_file('frontend')

    with backend_log.open('w', encoding='utf-8') as backend_log_handle, frontend_log.open('w', encoding='utf-8') as frontend_log_handle:
        backend_process = subprocess.Popen(
            [str(venv_python), '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', backend_port],
            cwd=str(BACKEND_DIR),
            env=_backend_env(),
            stdin=subprocess.DEVNULL,
            stdout=backend_log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

        frontend_process = subprocess.Popen(
            [_npm_command(), 'run', 'dev', '--', '--host', '0.0.0.0', '--port', frontend_port],
            cwd=str(FRONTEND_DIR),
            stdin=subprocess.DEVNULL,
            stdout=frontend_log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

        _pid_file().write_text(json.dumps({'backend': backend_process.pid, 'frontend': frontend_process.pid}))

        _wait_for_startup(
            {'backend': backend_process, 'frontend': frontend_process},
            {'backend': int(backend_port), 'frontend': int(frontend_port)},
        )

    _log('Local services started.')
    _log(f'Backend: http://localhost:{backend_port}')
    _log(f'Frontend: http://localhost:{frontend_port}')
    _log(f'Logs: {backend_log.name}, {frontend_log.name}')
    _log('Use: python3 run.py stop to stop both services')


def _kill_local_by_pattern(patterns: list[str]) -> bool:
    killed_any = False
    for pattern in patterns:
        try:
            result = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True, check=False)
        except FileNotFoundError:
            continue
        for pid_text in result.stdout.split():
            try:
                os.kill(int(pid_text), signal.SIGTERM)
                killed_any = True
            except (ProcessLookupError, ValueError):
                continue
    return killed_any


def _has_local_process_running() -> bool:
    patterns = [
        'uvicorn app.main:app --host 0.0.0.0 --port 8000',
        'vite --host 0.0.0.0',
        'npm run dev -- --host 0.0.0.0',
        'npm run dev --host 0.0.0.0',
    ]
    for pattern in patterns:
        try:
            result = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True, check=False)
        except FileNotFoundError:
            continue
        if result.stdout.strip():
            return True
    return False


def _stop_local() -> None:
    pid_file = _pid_file()
    stopped = False

    if pid_file.exists():
        try:
            pids = json.loads(pid_file.read_text())
        except Exception:
            _log('Could not read local PID file; removing stale state.')
            pid_file.unlink(missing_ok=True)
        else:
            for key in ('backend', 'frontend'):
                pid = pids.get(key)
                if not pid:
                    continue
                try:
                    os.kill(pid, signal.SIGTERM)
                    stopped = True
                except ProcessLookupError:
                    pass
            pid_file.unlink(missing_ok=True)

    patterns = [
        'uvicorn app.main:app --host 0.0.0.0 --port 8000',
        'vite --host 0.0.0.0',
        'npm run dev -- --host 0.0.0.0',
        'npm run dev --host 0.0.0.0',
    ]
    if _kill_local_by_pattern(patterns):
        stopped = True

    if stopped:
        _log('Stopped local services.')
    else:
        _log('No local services were running.')


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


def _compose_file_exists() -> bool:
    compose_candidates = ['docker-compose.yml', 'compose.yml', 'docker-compose.yaml', 'compose.yaml']
    for name in compose_candidates:
        if (ROOT / name).exists():
            return True
    return False


def _ensure_docker_compose_file() -> None:
    if not _compose_file_exists():
        raise FileNotFoundError('No Docker Compose file was found in the repo root.')


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='LogiSense launcher for Python 3.12/3.13 local or Docker-based startup.')
    parser.add_argument('mode', choices=['local', 'docker', 'start', 'stop', 'restart', 'status'], nargs='?')
    parser.add_argument('--python', dest='python_bin', default=None, help='Explicit Python 3.12/3.13 binary to use for the local mode.')
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
            if _has_local_process_running() or _pid_file().exists():
                _stop_local()
                return 0
            if _compose_file_exists():
                _stop_docker()
                return 0
            _log('No local or Docker services were running.')
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

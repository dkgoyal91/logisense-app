"""Serve the built frontend from FastAPI so one URL (and one tunnel) covers the whole show."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

SPA_PATHS = ('/', '/show', '/play', '/host')


def mount_frontend(app: FastAPI, dist_dir: Path) -> bool:
    index_file = dist_dir / 'index.html'
    if not index_file.is_file():
        return False
    _mount_assets(app, dist_dir)
    _add_spa_routes(app, index_file)
    _add_top_level_files(app, dist_dir)
    return True


def _mount_assets(app: FastAPI, dist_dir: Path) -> None:
    assets_dir = dist_dir / 'assets'
    if assets_dir.is_dir():
        app.mount('/assets', StaticFiles(directory=assets_dir), name='frontend-assets')


def _add_spa_routes(app: FastAPI, index_file: Path) -> None:
    for path in SPA_PATHS:
        app.add_api_route(path, _file_responder(index_file), methods=['GET'], include_in_schema=False)


def _add_top_level_files(app: FastAPI, dist_dir: Path) -> None:
    for file in dist_dir.iterdir():
        if file.is_file() and file.name != 'index.html':
            app.add_api_route(f'/{file.name}', _file_responder(file), methods=['GET'], include_in_schema=False)


def _file_responder(file: Path) -> Callable[[], FileResponse]:
    def respond() -> FileResponse:
        return FileResponse(file)
    return respond

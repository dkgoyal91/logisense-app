from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.static_site import mount_frontend


def _dist(tmp_path: Path) -> Path:
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'index.html').write_text('<html>game</html>', encoding='utf-8')
    (tmp_path / 'assets' / 'app.js').write_text('console.log(1)', encoding='utf-8')
    (tmp_path / 'logo.svg').write_text('<svg/>', encoding='utf-8')
    return tmp_path


def test_serves_the_spa_for_every_screen(tmp_path: Path) -> None:
    app = FastAPI()
    assert mount_frontend(app, _dist(tmp_path)) is True
    client = TestClient(app)
    for path in ('/', '/show', '/play', '/host'):
        assert client.get(path).text == '<html>game</html>'
    assert client.get('/assets/app.js').text == 'console.log(1)'
    assert client.get('/logo.svg').status_code == 200


def test_skips_mounting_without_a_build(tmp_path: Path) -> None:
    app = FastAPI()
    assert mount_frontend(app, tmp_path) is False
    assert TestClient(app).get('/play').status_code == 404

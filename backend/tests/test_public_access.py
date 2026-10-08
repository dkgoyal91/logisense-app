import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.public_access import install_public_allowlist

PUBLIC_URL = 'https://show.trycloudflare.com'
PUBLIC_HOST = {'host': 'show.trycloudflare.com'}
LOCAL_HOST = {'host': 'localhost:8000'}


def _app(public_url: str) -> FastAPI:
    app = FastAPI()
    for path in ('/', '/play', '/host', '/api/dashboard'):
        app.add_api_route(path, lambda: {'ok': True}, methods=['GET'])

    async def echo(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_json({'ok': True})
        await websocket.close()

    app.add_api_websocket_route('/ws/game/play', echo)
    app.add_api_websocket_route('/ws/chat', echo)
    install_public_allowlist(app, public_url)
    return app


def test_public_host_reaches_only_game_routes() -> None:
    client = TestClient(_app(PUBLIC_URL), base_url=PUBLIC_URL)
    assert client.get('/play').status_code == 200
    assert client.get('/host').status_code == 200
    assert client.get('/').status_code == 404
    assert client.get('/api/dashboard').status_code == 404
    with client.websocket_connect('/ws/game/play', headers=PUBLIC_HOST) as socket:
        assert socket.receive_json() == {'ok': True}
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws/chat', headers=PUBLIC_HOST) as socket:
            socket.receive_json()


def test_localhost_keeps_the_whole_app() -> None:
    client = TestClient(_app(PUBLIC_URL), base_url='http://localhost:8000')
    assert client.get('/').status_code == 200
    assert client.get('/api/dashboard').status_code == 200
    with client.websocket_connect('/ws/chat', headers=LOCAL_HOST) as socket:
        assert socket.receive_json() == {'ok': True}


def test_no_public_url_means_no_restriction() -> None:
    client = TestClient(_app(''), base_url=PUBLIC_URL)
    assert client.get('/api/dashboard').status_code == 200

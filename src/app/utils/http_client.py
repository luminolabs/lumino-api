import aiohttp
from fastapi import FastAPI


async def get_http_client(app: FastAPI) -> aiohttp.ClientSession:
    if not hasattr(app.state, 'http_client'):
        app.state.http_client = aiohttp.ClientSession()
    return app.state.http_client


async def close_http_client(app: FastAPI):
    if hasattr(app.state, 'http_client'):
        await app.state.http_client.close()


def setup_http_client(app: FastAPI):
    app.add_event_handler("startup", lambda: get_http_client(app))
    app.add_event_handler("shutdown", lambda: close_http_client(app))

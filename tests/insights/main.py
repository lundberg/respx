from fastapi import FastAPI, responses, Body
import typing as t
import httpx


app = FastAPI()


async def hook(response: httpx.Response) -> None:
    response.raise_for_status()


@app.post('/endpoint')
async def endpoint(
    data: t.Dict[str, str] = Body(...)
) -> responses.JSONResponse:
    async with httpx.AsyncClient(event_hooks={'response': [hook]}) as client:
        try:
            await client.post('https://test.com/post', json=data)
        except httpx.HTTPStatusError as e:
            return responses.JSONResponse(status_code=400, content={'status': 'error', 'detail': e.response.text})

    return responses.JSONResponse(content={'status': 'ok'})

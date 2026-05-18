import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import router as api_router
from websocket.router import router as websocket_router


def _get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


app = FastAPI(title="CoachModule API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(websocket_router)


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "coachmodule-backend"}

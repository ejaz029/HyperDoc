import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent.runner import run_incremental_agent
from app.api.changes import router as changes_router
from app.api.findings import router as findings_router
from app.api.routes import router as document_router
from app.watcher import watch_folder


app = FastAPI(
    title="Agentic Document System"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(document_router)
app.include_router(findings_router)
app.include_router(changes_router)


class WatchRequest(BaseModel):
    folder: str = "data/watch"

    existing_document_ids: list[int] = Field(
        default_factory=list
    )

    rules: list[str] = Field(
        default_factory=list
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents/watch/start")
def start_document_watcher(
    request: WatchRequest,
):
    thread = threading.Thread(
        target=watch_folder,
        kwargs={
            "folder": request.folder,
            "existing_document_ids": (
                request.existing_document_ids
            ),
            "rules": request.rules,
        },
        daemon=True,
    )

    thread.start()

    return {
        "status": "watching",
        "folder": request.folder,
        "existing_document_ids": (
            request.existing_document_ids
        ),
        "rules": request.rules,
    }
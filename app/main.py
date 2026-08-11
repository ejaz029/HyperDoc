from fastapi import FastAPI

from app.api.routes import router as document_router
from app.api.findings import router as findings_router


app = FastAPI(title="Agentic Document System")

app.include_router(document_router)
app.include_router(findings_router)


@app.get("/health")
def health():
    return {"status": "ok"}
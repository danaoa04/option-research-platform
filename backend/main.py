from backend.api import router
from backend.api.contracts import APPLICATION_VERSION
from fastapi import FastAPI

app = FastAPI(title="QuantLab backend", version=APPLICATION_VERSION)
app.include_router(router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "QuantLab backend",
        "version": APPLICATION_VERSION,
    }

from fastapi import FastAPI

app = FastAPI(title="QuantLab backend", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "QuantLab backend",
        "version": "0.1.0",
    }

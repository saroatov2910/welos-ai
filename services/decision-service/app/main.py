from fastapi import FastAPI

app = FastAPI(title="WelosAI Decision Service")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/readiness")
def readiness():
    return {"ready": True}

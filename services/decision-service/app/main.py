from fastapi import FastAPI

app = FastAPI(title="WelosAI Decision Service")


@app.get("/health")
def health():
    return {"status": "ok"}

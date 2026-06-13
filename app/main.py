from fastapi import FastAPI
import asyncio
from .worker import worker_loop, set_worker_control_flag

app = FastAPI(title="microdom_task")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "microdom_task"}

@app.get("/check_assign_change")
async def check_assign_change():
    set_worker_control_flag

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(worker_loop())
    
from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def pipeline_status():
    return {"status": "idle", "last_run_at": None, "run_id": None}


@router.post("/run")
def pipeline_run():
    return {"run_id": "stub"}


@router.get("/stream/{run_id}")
async def pipeline_stream(run_id: str):
    from fastapi.responses import StreamingResponse

    async def _empty():
        yield "data: [done]\n\n"

    return StreamingResponse(_empty(), media_type="text/event-stream")

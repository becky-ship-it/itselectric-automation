from fastapi import APIRouter

router = APIRouter()


@router.get("/export/snapshot")
def export_snapshot():
    return {"contacts": [], "outbound_emails": [], "chargers": [], "templates": [], "geocache": []}

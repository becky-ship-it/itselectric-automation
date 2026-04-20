from fastapi import APIRouter

router = APIRouter()


@router.get("/config")
def get_config():
    return {"data": {}}


@router.get("/decision-tree")
def get_decision_tree():
    return None

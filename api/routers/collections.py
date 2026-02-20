"""Collections API router."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/collections", tags=["collections"])

@router.get("")
async def list_collections():
    return []

@router.post("")
async def create_collection(name: str, embedding_dimension: int = 2048):
    return {"status": "created", "name": name}

@router.delete("/{name}")
async def delete_collection(name: str):
    return {"status": "deleted", "name": name}

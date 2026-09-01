from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.schemas.ask import AskRequest, AskResponse
from app.api.v1.services.ask import AskService

router = APIRouter(prefix="/ask", tags=["Ask"])


@router.post("/", response_model=AskResponse)
async def ask_question(request: AskRequest, db: AsyncSession = Depends(get_db)):
    service = AskService(db)
    return await service.process(request)

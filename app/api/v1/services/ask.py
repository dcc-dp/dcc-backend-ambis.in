import time
from app.api.v1.schemas.ask import AskRequest, AskResponse


class AskService:
    def __init__(self, db):
        self.db = db

    async def process(self, request: AskRequest) -> AskResponse:
        start = time.time()

        # TODO: Integrasi AI di sini (OpenAI, dll)
        answer = self._generate_response(request)

        elapsed_ms = int((time.time() - start) * 1000)

        return AskResponse(
            answer=answer,
            references=[],
            processing_time_ms=elapsed_ms,
            mode_used=request.mode,
        )

    def _generate_response(self, request: AskRequest) -> str:
        # Placeholder - integrasi AI akan diganti nanti
        return f"[AI Response] {request.question} (mode: {request.mode})"

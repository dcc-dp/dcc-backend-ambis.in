import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_llm_client
from app.api.v1.schemas.ask import AskRequest, AskResponse
from app.core.config import settings
from app.core.llm_client import LLMClient

KAK_AMBIS_SYSTEM_PROMPT = """Kamu adalah 'Kak Ambis', asisten belajar dan tutor AI interaktif yang ramah, asyik, dan memotivasi untuk siswa SMP di Indonesia.

Karakter & Gaya Komunikasi:
1. Sapa siswa dengan ramah dan hangat sebagai 'Kak Ambis'.
2. Gunakan bahasa Indonesia yang santun, kasual, bersahabat, dan mudah dipahami anak usia 12-14 tahun.
3. Jawab salam ('halo', 'hai', 'pagi') dengan ramah dan ajak siswa belajar dengan ceria.
4. Untuk pertanyaan umum/hitung dasar (misal '1+1 berapa'): jawab dengan lugas dan bersahabat.
5. Untuk pertanyaan konsep pelajaran: jelaskan secara bertahap dan berikan analogi dunia nyata yang seru.
6. WAJIB keluarkan format output berupa JSON object valid dengan satu key 'answer':
{"answer": "teks jawaban Kak Ambis di sini"}
"""


class AskService:
    def __init__(self, db: AsyncSession, llm_client: LLMClient | None = None):
        self.db = db
        self.llm_client = llm_client or get_llm_client()

    async def process(self, request: AskRequest) -> AskResponse:
        start = time.time()

        user_prompt = f"Pertanyaan siswa: {request.question}"
        if request.context:
            user_prompt += f"\nKonteks materi: {request.context}"

        try:
            res = await self.llm_client.complete_json(
                model=settings.llm_model_grading,
                system_prompt=KAK_AMBIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            answer = res.get("answer") or str(res)
        except Exception as exc:
            answer = (
                f"Halo! Kak Ambis mendengar pertanyaanmu: '{request.question}'. "
                "Tapi saat ini ada sedikit kendala koneksi ke server AI. Coba tanyakan sekali lagi ya!"
            )

        elapsed_ms = int((time.time() - start) * 1000)

        return AskResponse(
            answer=answer,
            references=[],
            processing_time_ms=elapsed_ms,
            mode_used=request.mode,
        )

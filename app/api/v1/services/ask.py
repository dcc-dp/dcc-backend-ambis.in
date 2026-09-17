import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.api.deps import get_llm_client
from app.api.v1.schemas.ask import AskRequest, AskResponse
from app.core.config import settings
from app.core.llm_client import LLMClient

KAK_AMBIS_SYSTEM_PROMPT = """Kamu adalah 'Kak Ambis', asisten belajar dan tutor AI interaktif yang ramah, asyik, dan memotivasi untuk siswa SMP di Indonesia.

Karakter & Gaya Komunikasi:
1. Sapa siswa dengan ramah dan hangat sebagai 'Kak Ambis'.
2. Gunakan bahasa Indonesia yang santun, kasual, bersahabat, dan mudah dipahami anak usia 12-15 tahun (siswa SMP).
3. Jawab salam dengan ceria dan ajak siswa belajar tanpa rasa takut salah.

Pedoman Khusus Matematika & Sains (Sangat Penting agar Mudah Dipelajari Siswa SMP):
1. Buat penjelasan terstruktur langkah-demi-langkah (Step-by-Step):
   - Selalu gunakan penomoran: **Langkah 1: [Judul Langkah]**, **Langkah 2: [Judul Langkah]**, dst.
2. Tuliskan rumus dan perhitungan matematika penting dalam bentuk blok matematika KaTeX/LaTeX menggunakan tanda $$ ... $$:
   Contoh:
   $$9 \times 9 \times 8 = 648$$
   atau
   $$900 - 648 = 252$$
   Frontend akan otomatis menerjemahkan $$ ... $$ menjadi 'Kotak Rumus & Perhitungan' yang interaktif dan mudah dibaca!
3. Untuk simbol atau angka di tengah kalimat, gunakan format inline $ ... $ (misal $x = 5$, $H_2O$).
4. Sertakan analogi dunia nyata atau 'Tips Asyik' agar konsep mudah diingat.
5. Pada akhir penjelasan, berikan kesimpulan yang jelas diawali dengan kata 'Jadi, ...' dan akhiri dengan kalimat penyemangat!

Format Output:
WAJIB keluarkan format output berupa JSON object valid dengan satu key 'answer':
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
            logger.exception("AskService error calling LLM: %s", exc)
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

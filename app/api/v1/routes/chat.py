"""SSE chat endpoint — streaming & non-streaming multi-model chat."""
import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.v1.services.multi_ai import (
    DEFAULT_MODEL_ID,
    MultiAIClient,
    get_multi_ai_client,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


DEFAULT_SYSTEM_PROMPT = (
    "Kamu adalah 'Kak Ambis', tutor AI yang ramah, asyik, dan suportif untuk siswa SMP di Indonesia.\n"
    "Pedoman Format Menjawab (Target: Siswa SMP — Rapi, Ringkas, & Bersih):\n"
    "1. ATURAN EMOJI: DILARANG KERAS menggunakan emoji dalam bentuk apa pun di seluruh jawaban.\n"
    "2. Nada Bicara: Santai, hangat, menyemangati, dan to-the-point layaknya kakak kelas yang baik.\n"
    "3. Penulisan Matematika: Gunakan KaTeX yang bersih. Gunakan $$ ... $$ untuk rumus utama (misal: $$ L = \\frac{1}{2} \\times a \\times t $$) atau $ ... $ untuk variabel/simbol ($x$, $cm^2$). JANGAN menumpuk rumus dengan kata-kata berulang di dalam tanda kurung.\n"
    "4. Penulisan Kode (Python/dsb): WAJIB gunakan blok kode markdown lengkap (```python ... ```) dengan sintaks yang benar dan rapi.\n"
    "5. Struktur Rapi: Gunakan judul bagian singkat dengan ### (misal: ### Cara Perbaikan, ### Kode yang Benar, ### Tips Tambahan).\n"
    "6. Anti-Malas Baca: Buat paragraf pendek (2-3 baris). Tebalkan kata kunci penting (**bold**).\n"
    "7. Penutup: Berikan kalimat singkat penyemangat di akhir."
)


class StudentContext(BaseModel):
    goal: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: str | None = None
    previous_sessions: list[str] | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    prompt: str = Field(..., min_length=1, max_length=10000)
    messages: list[ChatMessage] | None = None
    student_context: StudentContext | None = None
    model_id: str = Field(default=DEFAULT_MODEL_ID)
    system_prompt: str | None = None
    stream: bool = True


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest):
    """Chat dengan streaming SSE (default) atau non-streaming JSON (mendukung memori 1 sesi penuh & memori jangka panjang)."""
    system_prompt = request.system_prompt or DEFAULT_SYSTEM_PROMPT

    # Inject long-term student memory and cross-session context if provided
    if request.student_context:
        ctx = request.student_context
        memories = ["\n[MEMORI JANGKA PANJANG & PROFIL BELAJAR SISWA]"]
        if ctx.goal:
            memories.append(f"- Target Belajar: {ctx.goal}")
        if ctx.topic or ctx.subtopic:
            memories.append(f"- Minat Materi: {ctx.topic} {f'({ctx.subtopic})' if ctx.subtopic else ''}")
        if ctx.difficulty:
            memories.append(f"- Tingkat Pemahaman: {ctx.difficulty}")
        if ctx.previous_sessions:
            memories.append("- Riwayat Sesi Percakapan Sebelumnya:")
            for s in ctx.previous_sessions:
                memories.append(f"  * {s}")
        memories.append(
            "- PANDUAN MEMORI PERSONAL: Kamu mengingat profil dan topik-topik yang pernah dipelajari siswa ini sebelumnya. "
            "Jika siswa membuat percakapan baru atau menyinggung materi terdahulu, tunjukkan pemahamanmu secara hangat "
            "(misal: 'Senang ketemu lagi! Terakhir kamu sudah belajar aljabar, sekarang mau lanjut lagi ya?'). "
            "Pahami sejauh mana perkembangan belajarnya!"
        )
        system_prompt += "\n" + "\n".join(memories)

    # Build conversation messages payload for full current session
    history_messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]

    if request.messages:
        for m in request.messages:
            r = "assistant" if m.role == "assistant" else "user"
            history_messages.append({"role": r, "content": m.content})
        # If the last message in history is not current prompt, append it
        if not history_messages or history_messages[-1]["content"] != request.prompt:
            history_messages.append({"role": "user", "content": request.prompt})
    else:
        history_messages.append({"role": "user", "content": request.prompt})

    if not request.stream:
        client = get_multi_ai_client()
        start = time.time()
        answer = await client.complete(
            request.model_id,
            system_prompt,
            request.prompt,
            messages=history_messages,
        )
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "answer": answer,
            "model_used": request.model_id,
            "processing_time_ms": elapsed_ms,
        }

    client = get_multi_ai_client()

    async def event_generator():
        start = time.time()
        total_chars = 0

        yield (
            f"event: thinking\n"
            f"data: {json.dumps({'status': 'memulai...', 'model': request.model_id}, ensure_ascii=False)}\n\n"
        )

        try:
            async for chunk in client.stream_text(
                request.model_id,
                system_prompt,
                request.prompt,
                messages=history_messages,
            ):
                total_chars += len(chunk)
                yield (
                    f"event: token\n"
                    f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
                )
        except Exception as exc:
            yield (
                f"event: error\n"
                f"data: {json.dumps({'message': str(exc)}, ensure_ascii=True)}\n\n"
            )
            return

        elapsed_ms = int((time.time() - start) * 1000)
        yield (
            f"event: done\n"
            f"data: {json.dumps({'model_used': request.model_id, 'processing_time_ms': elapsed_ms, 'total_chars': total_chars}, ensure_ascii=False)}\n\n"
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

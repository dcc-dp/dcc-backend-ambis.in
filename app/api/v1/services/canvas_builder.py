"""Canvas Builder — detects deep explanations and parses them into structured canvas payload."""
import re
from dataclasses import dataclass, field


# ── Trigger heuristics ─────────────────────────────────────────────────────────
CANVAS_KEYWORD_PATTERNS = [
    r"\bjellaskan\b", r"\bjelaskan\b", r"\bpahami\b", r"\bpembuktian\b",
    r"\bbuktikan\b", r"\balgorithm\b", r"\balgoritma\b", r"\bderivasi\b",
    r"\bturunkan\b", r"\blangkah[\s-]?demi[\s-]?langkah\b", r"\bstep by step\b",
    r"\bcara kerja\b", r"\bbagaimana cara\b", r"\bgimana cara\b",
    r"\bkonsep\b", r"\bprinsip\b", r"\bteori\b", r"\brumus\b",
    r"\bcontoh soal\b", r"\bcontoh kode\b", r"\bpseudocode\b",
    r"\bflowchart\b", r"\bdiagram\b",
]

CANVAS_RESPONSE_SIGNALS = [
    r"###\s+Langkah",       # step-by-step headings
    r"^Langkah\s+\d+",      # explicit step lines
    r"```[a-zA-Z]+",        # code blocks
    r"\$\$[^\n]{5,}\$\$",   # display math
    r"####",                # sub-sub-headings (deep structure)
]

MIN_RESPONSE_LEN_FOR_CANVAS = 600  # characters — short answers skip canvas


def should_open_canvas(prompt: str, response: str) -> bool:
    """Return True when the response warrants a canvas panel."""
    prompt_lower = prompt.lower()
    if any(re.search(p, prompt_lower) for p in CANVAS_KEYWORD_PATTERNS):
        return True
    if len(response) >= MIN_RESPONSE_LEN_FOR_CANVAS:
        for sig in CANVAS_RESPONSE_SIGNALS:
            if re.search(sig, response, re.MULTILINE):
                return True
    return False


# ── Payload builder ────────────────────────────────────────────────────────────

@dataclass
class CanvasStep:
    number: int
    title: str
    body: str  # may contain markdown / KaTeX
    formula: str = ""


@dataclass
class CanvasPayload:
    title: str = ""
    subject: str = "Matematika"   # Matematika | Informatika | Umum
    analogy: str = ""
    concept: str = ""
    steps: list[CanvasStep] = field(default_factory=list)
    summary: str = ""
    quiz: list[dict] = field(default_factory=list)  # [{"q": "...", "a": "..."}]
    raw_content: str = ""


def _extract_heading_title(text: str) -> str:
    """Pull the first markdown heading as canvas title."""
    m = re.search(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "Penjelasan Mendalam"


def _detect_subject(text: str, prompt: str) -> str:
    combined = (text + " " + prompt).lower()
    if any(w in combined for w in ["python", "javascript", "program", "kode", "code",
                                    "algoritma", "variabel", "fungsi", "loop", "if"]):
        return "Informatika"
    if any(w in combined for w in ["rumus", "persamaan", "integral", "turunan", "matriks",
                                    "aljabar", "geometri", "statistik", "probabilitas"]):
        return "Matematika"
    return "Umum"


def _extract_analogy(text: str) -> str:
    """Find an analogy / intro paragraph (first non-heading paragraph)."""
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("```"):
            if len(stripped) > 30:
                return stripped[:500]
    return ""


def _extract_steps(text: str) -> list[CanvasStep]:
    """Parse **Langkah N** or ### Langkah N blocks into CanvasStep objects."""
    steps: list[CanvasStep] = []

    # Pattern: **Langkah 1: Title** followed by body until next langkah or end
    pattern = re.compile(
        r"(?:\*{0,2}Langkah\s+(\d+)[:\.]?\*{0,2})\s*([^\n]*)\n([\s\S]*?)(?=(?:\*{0,2}Langkah\s+\d+)|$)",
        re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        num = int(m.group(1))
        title = m.group(2).replace("**", "").strip() or f"Langkah {num}"
        body = m.group(3).strip()

        # Extract any display-math formula from body
        formula_match = re.search(r"\$\$([\s\S]*?)\$\$", body)
        formula = formula_match.group(0).strip() if formula_match else ""

        steps.append(CanvasStep(number=num, title=title, body=body, formula=formula))

    # Fallback: markdown ### Langkah N headers
    if not steps:
        pattern2 = re.compile(
            r"^#{1,4}\s+(?:Langkah|Step)\s+(\d+)[:\.]?\s*([^\n]*)\n([\s\S]*?)(?=^#{1,4}\s+|$)",
            re.MULTILINE | re.IGNORECASE,
        )
        for m in pattern2.finditer(text):
            num = int(m.group(1))
            title = m.group(2).strip() or f"Langkah {num}"
            body = m.group(3).strip()
            formula_match = re.search(r"\$\$([\s\S]*?)\$\$", body)
            formula = formula_match.group(0).strip() if formula_match else ""
            steps.append(CanvasStep(number=num, title=title, body=body, formula=formula))

    return steps


def _extract_summary(text: str) -> str:
    """Extract conclusion / Jadi, ... paragraph."""
    m = re.search(r"(?:Jadi,|Kesimpulan:|Maka,|Sehingga,)([^\n]+(?:\n(?!#)[^\n]+)*)", text)
    if m:
        return m.group(0).strip()[:600]
    # Fallback: last non-empty paragraph
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paras[-1][:400] if paras else ""


def build_canvas_payload(prompt: str, response: str) -> CanvasPayload:
    """Parse the full AI response into a structured CanvasPayload."""
    payload = CanvasPayload(
        title=_extract_heading_title(response),
        subject=_detect_subject(response, prompt),
        analogy=_extract_analogy(response),
        steps=_extract_steps(response),
        summary=_extract_summary(response),
        raw_content=response,
    )

    # concept: first ### section that is not Langkah
    concept_match = re.search(
        r"^#{1,3}\s+(?!Langkah)([^\n]+)\n([\s\S]*?)(?=^#{1,3}\s+|$)",
        response, re.MULTILINE
    )
    if concept_match:
        payload.concept = (concept_match.group(1) + "\n" + concept_match.group(2)).strip()[:600]

    return payload

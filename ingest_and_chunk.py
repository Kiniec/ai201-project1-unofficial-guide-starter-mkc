"""
ingest_and_chunk.py  —  Milestone 3
Loads all source documents, cleans text, and produces semantic chunks
saved to data/chunks.json for the embedding step.

Run:
    python ingest_and_chunk.py
"""

import io
import json
import re
import time
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup
from transformers import AutoTokenizer

# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE  = 300   # max tokens per chunk (ceiling; semantic splits take priority)
OVERLAP     = 50    # overlap tokens carried from previous chunk into next
MODEL_NAME      = "sentence-transformers/all-MiniLM-L6-v2"
OUTPUT_PATH     = Path("data/chunks.json")
DOCUMENTS_DIR   = Path("documents")   # drop Reddit .txt files here
CRAWL_DELAY     = 1.5   # seconds between HTTP requests — be polite to servers
MIN_DOC_TOKENS  = 100   # skip documents with fewer tokens after cleaning

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Sources from planning.md ──────────────────────────────────────────────────
WEB_SOURCES = [
    {
        "url": "https://www.untdallas.edu/finaid/apply/emergency-funding.php",
        "source": "UNT Dallas Emergency Funding",
    },
    {
        "url": "https://dhantx.com/applicants/emergency-housing-resources/",
        "source": "Dallas Housing Authority",
    },
    {
        "url": "https://salvationarmyntx.org/north-texas/carr-p-collins-social-service-center/provide-housing",
        "source": "Salvation Army NTX",
    },
    {
        "url": "https://dallaslife.org/place-to-stay/",
        "source": "Dallas Life",
    },
    {
        "url": "https://www.under1roofdallas.org/faq?questionId=0f50598c-e23b-4c41-9625-f4cb302a2547",
        "source": "Under 1 Roof Dallas",
    },
    {
        "url": "https://housingforwardntx.org",
        "source": "Housing Forward NTX",
    },
    {
        "url": "https://www.ivcompassion.org/",
        "source": "Inspired Vision Compassion Center",
    },
    {
        "url": "https://htdallas.org/ht-food-pantry/",
        "source": "Holy Trinity Food Pantry",
    },
    {
        "url": "https://www.unt.edu/onestop/student-emergency-support-program.html",
        "source": "UNT Denton Emergency Support",
    },
    {
        "url": "https://studentaffairs.unt.edu/desresources/programs/food-pantry/hours.html",
        "source": "UNT Denton Food Pantry",
    },
    {
        "url": "https://basicneeds.utdallas.edu/resource-hub/",
        "source": "UT Dallas Basic Needs",
    },
    {
        "url": "https://www.dallascollege.edu/resources/student-care-network/housing/",
        "source": "Dallas College Student Care",
    },
]



PDF_SOURCES = [
    {
        "url": "https://austinstreet.org/wp-content/uploads/2024/12/ASC-Resource-Guide-2024.pdf",
        "source": "Austin Street Center Resource Guide",
    },
]


# ── Noise patterns for HTML cleaning ─────────────────────────────────────────

# Elements whose class or id signals they are chrome, not content
_NOISE_CLASS_RE = re.compile(
    r"cookie|consent|gdpr|banner|modal|popup|overlay|"
    r"social|share[-_]|share$|sharebar|"
    r"breadcrumb|sidebar|widget|advert|ad[-_]|advertisement|"
    r"newsletter|subscribe|related[-_]|recommended|trending|"
    r"comment[-_]count|tag[-_]cloud|pagination|pager|"
    r"search[-_]form|site[-_]header|site[-_]footer|"
    r"skip[-_]link|screen[-_]reader|back[-_]to[-_]top|"
    r"sticky|floating|offcanvas|dropdown|mega[-_]menu|"
    r"utility[-_]nav|top[-_]bar|alert[-_]bar",
    re.IGNORECASE,
)
_NOISE_ID_RE = re.compile(
    r"cookie|consent|banner|modal|popup|overlay|social|share|"
    r"breadcrumb|sidebar|advertisement|newsletter|subscribe|"
    r"search[-_]form|masthead|colophon|wpadminbar",
    re.IGNORECASE,
)

# When a line matches this, drop it and everything after it — footer has started
_FOOTER_START_RE = re.compile(
    r"(^footer\s+\w|"                                # "footer dallas college ..."
    r"©\s*20\d\d\s+\w|"                              # "© 2026 Dallas Life ..."
    r"privacy policy.*ecfa|"                         # dallaslife footer block
    r"tax\s+id\s*#\s*:\s*\d|"                        # "tax id # : 75-2336522"
    r"report an accessibility issue|"
    r"legal notices.*financial transparency|"
    r"updated\s+\w+\s+\d+,\s*20\d\d\s+footer)",     # "updated september 5, 2025 footer"
    re.IGNORECASE,
)

# Lines that are UI chrome regardless of source
_BOILERPLATE_LINE_RE = re.compile(
    r"^("
    r"skip (to |navigation|content|main)|"
    r"(main |primary )?menu|close menu|open menu|toggle (menu|nav)|"
    r"search(\.\.\.|…)?|"
    r"read more|learn more|click here|more info(rmation)?|find out more|"
    r"share( this( page)?)?|tweet( this)?|"
    r"facebook|instagram|linkedin|twitter|pinterest|youtube|tiktok|"
    r"email (this|page)|print( page| this)?|"
    r"(un)?subscribe( now)?|sign[ -]?up( (now|for free))?|"
    r"log[ -]?in|log[ -]?out|sign[ -]?in|register( now)?|create (an )?account|"
    r"accept (all )?cookies?|reject (all )?cookies?|decline( cookies?)?|"
    r"manage (cookie )?settings|cookie (settings|preferences|policy)|"
    r"privacy policy|terms of (use|service)|terms and conditions|"
    r"all rights reserved\.?|copyright ©?|\© \d{4}|"
    r"follow us( on)?|like us( on)?|"
    r"donate( now)?|make a donation|give now|"
    r"contact us|about us|our (team|staff|mission)|"
    r"get directions|view (map|on map)|"
    r"back to top|scroll (back )?to top|return to top|"
    r"add to calendar|view calendar|"
    r"home\s*[›»>/|]|you are here|"
    r"(show|load|view|see) (more|all( results)?)|"
    r"comments?\s*\(\d+\)|no comments?|leave a (comment|reply)|"
    r"posted (in|by|on)\s|filed under\s|tags?:\s|categor(y|ies):\s|"
    r"\d+\s*(views?|shares?|likes?|comments?|replies)|"
    r"was this (article |page )?(helpful|useful)\?|"
    r"(yes|no),?\s*(it was|this was) (helpful|useful)|"
    r"rate this( page| article)?|"
    r"(previous|next) (post|article|page)|"
    r"table of contents|jump to (section|content)|"
    # Plain-text footer lines that survive .txt ingestion
    r"need an it company\?|techsmarter can help|visit our website at http|"
    r"backed by a team of experienced professionals|deliver lasting changes|"
    r"apply now!|take a tour|get more info|"
    r"(myunt|ecampus|econnect|workday|canvas)\b.*|"
    r"report an accessibility issue|notice of non.discrimination|"
    r"financial transparency|privacy (& security )?policy|report fraud|site map|"
    r"disclaimer notice of non.discrimination|electronic accessibility|"
    r"required links|©\s*20\d\d\s+\w.*all rights reserved"
    r")$",
    re.IGNORECASE,
)

# ── Loaders ───────────────────────────────────────────────────────────────────

def fetch_web(url: str, source: str) -> dict | None:
    """Fetch a web page, strip all chrome, and return substantive body text."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Remove structural noise tags outright
        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside",
             "form", "iframe", "noscript", "svg", "figure", "figcaption",
             "picture", "button", "dialog", "template"]
        ):
            tag.decompose()

        # 2. Remove elements whose class or id signals chrome (cookie banners,
        #    share bars, sidebars, ads, modals, etc.)
        noise = [
            el for el in soup.find_all(True)
            if _NOISE_CLASS_RE.search(" ".join(el.get("class", [])))
            or _NOISE_ID_RE.search(el.get("id", ""))
        ]
        for el in noise:
            el.decompose()

        # 3. Prefer a focused content container over the full page
        main = None
        for selector in [
            "main", "article", "[role='main']",
            "#main-content", "#content", "#main", "#page-content",
            ".main-content", ".entry-content", ".page-content",
            ".post-content", ".content-area", ".article-body",
        ]:
            main = soup.select_one(selector)
            if main:
                break

        text = (main or soup).get_text(separator="\n")
        return {"text": text, "source": source, "url": url}
    except Exception as e:
        print(f"  [WARN] {source}: {e}")
        return None


def fetch_reddit(url: str, source: str) -> dict | None:
    """Fetch a Reddit thread via JSON API and return post + top-level comments."""
    try:
        reddit_headers = {**HEADERS, "Accept": "application/json"}
        resp = requests.get(url, headers=reddit_headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        parts = []
        post = data[0]["data"]["children"][0]["data"]
        if post.get("title"):
            parts.append(post["title"])
        if post.get("selftext"):
            parts.append(post["selftext"])

        for comment in data[1]["data"]["children"]:
            body = comment["data"].get("body", "")
            if body and body not in ("[deleted]", "[removed]"):
                parts.append(body)

        return {"text": "\n\n".join(parts), "source": source, "url": url}
    except Exception as e:
        print(f"  [WARN] {source}: {e}")
        return None


def fetch_pdf(url: str, source: str) -> dict | None:
    """Download a PDF from a URL and extract its text page by page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        pages = []
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
        return {"text": "\n\n".join(pages), "source": source, "url": url}
    except Exception as e:
        print(f"  [WARN] {source}: {e}")
        return None


def load_local_files() -> list[dict]:
    """
    Read every .txt and .md file from the documents/ folder.
    Use this for Reddit threads (or any source blocked by automated fetching):
    paste the raw thread text into a file named after the source, e.g.
        documents/reddit_college_homelessness.txt
    The filename (without extension, underscores → spaces) becomes the source label.
    """
    docs = []
    if not DOCUMENTS_DIR.exists():
        return docs
    for path in sorted(DOCUMENTS_DIR.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        source = path.stem.replace("_", " ").title()
        print(f"  {source}  ({path.name})")
        docs.append({"text": text, "source": source, "url": str(path)})
    return docs


def load_documents() -> list[dict]:
    docs = []

    print("Loading web sources...")
    for item in WEB_SOURCES:
        print(f"  {item['source']}")
        doc = fetch_web(item["url"], item["source"])
        if doc:
            docs.append(doc)
        time.sleep(CRAWL_DELAY)

    print("\nLoading PDF sources...")
    for item in PDF_SOURCES:
        print(f"  {item['source']}")
        doc = fetch_pdf(item["url"], item["source"])
        if doc:
            docs.append(doc)
        time.sleep(CRAWL_DELAY)

    print("\nLoading local files (documents/ folder)...")
    docs.extend(load_local_files())

    return docs


# ── Cleaning ──────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Strip boilerplate and normalize whitespace.
    Removes: nav items, cookie notices, share buttons, footers, ads, repeated
    headers, "Read more" links, comment counts, and any single-line UI chrome.
    Keeps: service descriptions, hours, addresses, eligibility info, and any
    substantive prose needed to answer a user question.
    """
    # Unicode artifacts
    text = (
        text.replace("\xa0", " ")
            .replace("​", "")
            .replace("‌", "")
            .replace("‍", "")
            .replace("﻿", "")
    )
    # Strip Markdown formatting from Reddit text (safe to apply universally)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)   # [label](url) → label
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", text)     # bold / italic
    text = re.sub(r"_{1,2}([^_\n]+)_{1,2}", r"\1", text)        # underline / italic
    text = re.sub(r"~~([^~\n]+)~~", r"\1", text)                 # strikethrough
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)        # blockquotes
    text = re.sub(r"`([^`\n]+)`", r"\1", text)                   # inline code

    # Normalize line endings and horizontal whitespace
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Truncate at the first footer sentinel before any line processing.
    # Handles footers appended mid-paragraph (no line break before them).
    m = _FOOTER_START_RE.search(text)
    if m:
        text = text[:m.start()].rstrip()

    seen: set[str] = set()
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()

        # Drop empty / trivial lines
        if len(stripped) <= 2:
            continue
        # Drop boilerplate UI phrases
        if _BOILERPLATE_LINE_RE.match(stripped):
            continue
        # Drop bare URLs (leaked href text)
        if re.match(r"^https?://\S+$", stripped):
            continue
        # Drop lines that are only digits (page numbers, vote counts)
        if re.match(r"^\d+$", stripped):
            continue
        # Drop duplicate lines — navigation menus repeat across the page
        lower = stripped.lower()
        if lower in seen:
            continue
        seen.add(lower)
        kept.append(line)

    text = "\n".join(kept).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


# ── Chunking ──────────────────────────────────────────────────────────────────

def _split_to_segments(text: str) -> list[str]:
    """
    Split at paragraph boundaries first; fall back to sentences for long paragraphs.
    This is the 'semantic' part — we respect meaning boundaries before hitting the
    token ceiling.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    segments = []
    for para in paragraphs:
        if len(para) > 1500:  # rough char heuristic to avoid tokenizing huge blocks
            sentences = re.split(r"(?<=[.!?])\s+", para)
            segments.extend(s.strip() for s in sentences if s.strip())
        else:
            segments.append(para)
    return segments


def chunk_text(text: str, tokenizer) -> list[str]:
    """
    Group segments into chunks up to CHUNK_SIZE tokens.
    Each new chunk starts with the last OVERLAP tokens of the previous chunk
    so context is not lost at boundaries.
    """
    segments = _split_to_segments(text)
    chunks: list[str] = []
    current_ids: list[int] = []

    for seg in segments:
        seg_ids = tokenizer.encode(seg, add_special_tokens=False)

        if len(current_ids) + len(seg_ids) <= CHUNK_SIZE:
            current_ids.extend(seg_ids)
        else:
            if current_ids:
                chunks.append(tokenizer.decode(current_ids, skip_special_tokens=True))
            overlap = current_ids[-OVERLAP:] if len(current_ids) >= OVERLAP else current_ids[:]
            current_ids = overlap + seg_ids

            # Hard-split oversized segments that exceed the ceiling even alone
            while len(current_ids) > CHUNK_SIZE:
                chunks.append(
                    tokenizer.decode(current_ids[:CHUNK_SIZE], skip_special_tokens=True)
                )
                current_ids = current_ids[CHUNK_SIZE - OVERLAP:]

    if current_ids:
        chunks.append(tokenizer.decode(current_ids, skip_special_tokens=True))

    # Strip WordPiece continuation markers that leak through on chunk boundaries
    cleaned = [re.sub(r"\s*##\S*", "", c).strip() for c in chunks]
    return [c for c in cleaned if c]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading tokenizer: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    docs = load_documents()
    print(f"\nLoaded {len(docs)} documents.")

    all_chunks = []
    skipped = []
    for doc in docs:
        cleaned = clean_text(doc["text"])
        if not cleaned:
            skipped.append((doc["source"], "empty after cleaning"))
            continue
        token_count = len(tokenizer.encode(cleaned, add_special_tokens=False))
        if token_count < MIN_DOC_TOKENS:
            skipped.append((doc["source"], f"only {token_count} tokens after cleaning — likely JS-rendered or blocked"))
            continue
        chunk_texts = chunk_text(cleaned, tokenizer)
        slug = re.sub(r"[^a-z0-9]+", "_", doc["source"].lower()).strip("_")
        for i, text in enumerate(chunk_texts):
            all_chunks.append(
                {
                    "chunk_id": f"{slug}_{i:04d}",
                    "source": doc["source"],
                    "url": doc["url"],
                    "text": text,
                    "token_count": len(tokenizer.encode(text, add_special_tokens=False)),
                }
            )

    if skipped:
        print("\n[SKIPPED — too little content after cleaning]")
        for name, reason in skipped:
            print(f"  {name}: {reason}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    token_counts = [c["token_count"] for c in all_chunks]
    print(f"\nSaved {len(all_chunks)} chunks → {OUTPUT_PATH}")
    if token_counts:
        print(f"  Avg tokens/chunk : {sum(token_counts) / len(token_counts):.0f}")
        print(f"  Max tokens/chunk : {max(token_counts)}")
        print(f"  Min tokens/chunk : {min(token_counts)}")


if __name__ == "__main__":
    main()

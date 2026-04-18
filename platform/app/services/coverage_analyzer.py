"""Coverage-of-source-terms analyzer.

For a task linked to source documents (SRC-NNN), check which key terms from
those sources are NOT present in the task's acceptance criteria. Used by
task_report to flag likely under-coverage before closing.

MVP heuristic (intentional — no NLP dependency):
- Tokenize: lowercase, split on non-alphanumeric, keep tokens of length >= 5
- Stopwords: hand-curated PL+EN list (see _STOPWORDS)
- Match: prefix-5 comparison catches Polish declensions (rezerwacja/rezerwacji
  share prefix "rezer"). False positives possible but acceptable for MVP.
- Score: rank gap terms by frequency in source (most-mentioned gaps first)
"""
import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+")
_MIN_TOKEN_LEN = 5
_PREFIX_LEN = 5  # chars used for declension-tolerant match

_STOPWORDS: frozenset[str] = frozenset({
    # Polish common words
    "który", "która", "które", "których", "którego", "którym",
    "jest", "są", "być", "była", "było", "były", "będzie", "będą",
    "bardzo", "tylko", "jeszcze", "także", "również", "oraz",
    "można", "musi", "powinien", "powinna", "powinno",
    "przez", "dla", "przy", "bez", "poza", "wokół",
    "jednak", "dlatego", "ponieważ", "podczas", "natomiast",
    "wszystkie", "wszystko", "wszystkich", "każdy", "każda", "każde",
    "kiedy", "gdzie", "dlaczego",
    "zostać", "zostanie", "został", "została",
    "liczba", "ilość", "wartość",  # too generic for domain signal
    # English common words
    "about", "above", "after", "again", "against", "because", "before",
    "being", "below", "between", "both", "doing", "during", "each", "few",
    "from", "further", "having", "into", "more", "most", "other", "over",
    "same", "should", "such", "than", "that", "their", "them", "then",
    "there", "these", "they", "this", "those", "under", "until", "very",
    "what", "when", "where", "which", "while", "with", "would", "your",
    "will", "must", "just", "also", "make", "makes", "made", "been",
    # Generic noise
    "example", "content", "data", "value", "item", "list",
})


@dataclass
class TermStat:
    term: str
    src_count: int
    ac_count: int
    src_ids: list[str]

    @property
    def covered(self) -> bool:
        return self.ac_count > 0


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)
            if len(m.group(0)) >= _MIN_TOKEN_LEN]


def _prefix(token: str) -> str:
    return token[:_PREFIX_LEN]


def analyze_coverage(
    source_texts: dict[str, str],
    ac_texts: list[str],
    max_gap_terms: int = 15,
    max_covered_terms: int = 0,
) -> dict:
    """Compute which significant source terms are absent from AC texts.

    source_texts: {source_external_id: content_string}
    ac_texts: list of AC.text strings
    max_gap_terms: cap gap list (sorted by src_count DESC)
    max_covered_terms: cap covered list (0 = no list, saves response size)

    Returns:
      {
        "total_unique_terms": int,
        "covered_count": int,
        "gap_count": int,
        "coverage_pct": float,       # 0..100, 100 = all source terms also in AC
        "gap_terms": [               # biggest gaps first
          {"term": str, "src_count": int, "src_ids": [str]}
        ],
        "covered_terms": [...],      # only if max_covered_terms > 0
        "sources_analyzed": [str],
      }
    """
    # source-side: prefix -> {canonical_term: str, count: int, src_ids: set[str]}
    src_index: dict[str, dict] = {}
    sources_analyzed: list[str] = []
    for src_id, content in source_texts.items():
        sources_analyzed.append(src_id)
        seen_in_this_src: set[str] = set()
        for tok in _tokenize(content):
            if tok in _STOPWORDS:
                continue
            pfx = _prefix(tok)
            entry = src_index.setdefault(pfx, {"term": tok, "count": 0, "src_ids": set()})
            entry["count"] += 1
            entry["src_ids"].add(src_id)
            # Keep shortest canonical form (approx. stem/base)
            if len(tok) < len(entry["term"]):
                entry["term"] = tok
            seen_in_this_src.add(pfx)

    # AC-side: set of prefixes present
    ac_prefixes: set[str] = set()
    for txt in ac_texts:
        for tok in _tokenize(txt):
            if tok in _STOPWORDS:
                continue
            ac_prefixes.add(_prefix(tok))

    # Classify
    gap: list[TermStat] = []
    covered: list[TermStat] = []
    for pfx, meta in src_index.items():
        if pfx in ac_prefixes:
            covered.append(TermStat(
                term=meta["term"], src_count=meta["count"], ac_count=1,
                src_ids=sorted(meta["src_ids"]),
            ))
        else:
            gap.append(TermStat(
                term=meta["term"], src_count=meta["count"], ac_count=0,
                src_ids=sorted(meta["src_ids"]),
            ))

    gap.sort(key=lambda t: (-t.src_count, t.term))
    covered.sort(key=lambda t: (-t.src_count, t.term))

    total = len(src_index)
    covered_n = len(covered)
    pct = round(100.0 * covered_n / total, 1) if total else 100.0

    result = {
        "total_unique_terms": total,
        "covered_count": covered_n,
        "gap_count": len(gap),
        "coverage_pct": pct,
        "gap_terms": [
            {"term": t.term, "src_count": t.src_count, "src_ids": t.src_ids}
            for t in gap[:max_gap_terms]
        ],
        "sources_analyzed": sources_analyzed,
    }
    if max_covered_terms > 0:
        result["covered_terms"] = [
            {"term": t.term, "src_count": t.src_count, "src_ids": t.src_ids}
            for t in covered[:max_covered_terms]
        ]
    return result

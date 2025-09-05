import re
import unicodedata

# Common abbreviations that shouldn't terminate a sentence when followed by a period.
_ABBREV = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "etc",
    "e.g", "i.e", "no", "dept", "fig", "al", "est",
    "a.m", "p.m", "u.s", "u.k", "d.c",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}

# Characters we allow to immediately trail an ender and still count as part of the sentence
_CLOSERS = '\'"”’）)]}»›'

# Ender characters (include full-width forms and Unicode ellipsis)
_ENDERS = set(['.', '!', '?', '…', '。', '！', '？'])

def _is_decimal(s: str, i: int) -> bool:
    """True if s[i] == '.' and is between digits: 3.14"""
    return s[i] == '.' and i > 0 and i+1 < len(s) and s[i-1].isdigit() and s[i+1].isdigit()

def _token_before_dot(s: str, i: int) -> str:
    """Return the token (letters/numbers/_/-) immediately before s[i]=='.'."""
    k = i - 1
    while k >= 0 and (s[k].isalnum() or s[k] in "-_"):
        k -= 1
    return s[k+1:i].lower()

def first_sentence(text: str) -> str:
    """
    Return the first sentence from `text`.

    Recognized sentence enders:
      '.', '!', '?', '…' (or '...'), plus combos like '?!', '!!', '!?'
    Avoids false stops for decimals (3.14), initials/acronyms (U.S.), and abbreviations (e.g., Dr., p.m.).
    Includes trailing closers like quotes/brackets immediately after the end mark.
    """
    if not text:
        return ""

    # Normalize whitespace and Unicode form
    s = unicodedata.normalize("NFC", re.sub(r'\s+', ' ', text.strip()))
    if not s:
        return ""

    n = len(s)
    i = 0
    while i < n:
        ch = s[i]

        # Handle explicit '!' or '?' → may be followed by more !/? or dots/ellipsis
        if ch in ('!', '?', '！', '？'):
            j = i + 1
            # absorb sequences like !!, ?!, !?, ?!!, and trailing dots/ellipsis
            while j < n and s[j] in ('!', '?', '.', '…', '！', '？'):
                j += 1
            # include any immediate closing quotes/brackets
            while j < n and s[j] in _CLOSERS:
                j += 1
            return s[:j].strip()

        # Ellipsis as a distinct char
        if ch == '…':
            j = i + 1
            # include extra ellipsis dots if repeated
            while j < n and s[j] == '…':
                j += 1
            while j < n and s[j] in _CLOSERS:
                j += 1
            return s[:j].strip()

        # ASCII periods: handle '...' and regular '.'
        if ch == '.':
            # Case 1: decimal like 3.14 → not an end
            if _is_decimal(s, i):
                i += 1
                continue

            # Case 2: 3-dot ellipsis "..."
            if i+2 < n and s[i+1] == '.' and s[i+2] == '.':
                j = i + 3
                # absorb any additional periods (some writers use 4 dots)
                while j < n and s[j] == '.':
                    j += 1
                while j < n and s[j] in _CLOSERS:
                    j += 1
                return s[:j].strip()

            # Case 3: initials/acronyms like "U.S." or "A.B."
            prev = s[i-1] if i > 0 else ''
            nxt  = s[i+1] if i+1 < n else ''
            if prev.isalpha() and prev.isupper() and (i+1 < n and nxt.isupper()):
                i += 1
                continue

            # Case 4: common abbreviations before the period
            if _token_before_dot(s, i) in _ABBREV:
                i += 1
                continue

            # Otherwise treat as a sentence end; also absorb trailing additional '.' (e.g., stylistic stops)
            j = i + 1
            while j < n and s[j] == '.':
                j += 1
            while j < n and s[j] in _CLOSERS:
                j += 1
            return s[:j].strip()

        i += 1

    # No terminal punctuation found → return entire string
    return s

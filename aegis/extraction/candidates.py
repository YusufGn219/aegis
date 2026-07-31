"""Kullanicinin ham mesajindan deterministik (regex tabanli) 'aday' cikarma.

Bu modul saftir: hicbir I/O, hicbir LLM cagrisi yapmaz. Amaci, LLM'in tool
cagrilarinda kullanacagi metin degerlerini KENDISI URETMESIN diye, gercekte
kullanicinin yazdigi kelimelerden bir aday havuzu cikarmaktir. LLM daha sonra
sadece bu havuzdan secim yapar (bkz. aegis.llm.prompt_builder).

Bilinen sinirlamalar (bilerek bu asamada cozulmuyor):
- Sadece "X klasoru" / "X folder" / "X directory" kalibi destekleniyor
  (kelime SIRASI sabit - hedef once gelir); "klasor X" gibi ters sira
  yakalanmiyor.
- Fuzzy/Levenshtein eslesme yok - sadece tam string (normalize edilmis)
  ve substring eslesme var (bkz. normalize() ve PathResolver).
- Dosya sistemi varlik kontrolu burada YAPILMAZ - bu modul saf metin
  islemedir, gercek path cozumlemesi aegis.resolution.path_resolver'in isi.
- Tirnak ici ifadelerin hangisinin "subject" hangisinin "body" oldugu bu
  modulun karari degil; sadece sirali bir liste doner, anlam atamasi
  Skill katmaninin sozlesmesidir (ilk tirnak = subject, ikinci = body).
- Baglamsal referanslar ("bu dosya", "az once indirdigim") yakalanmiyor.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

QUOTED_RE = re.compile(r"""['"]([^'"]+)['"]""")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
FILENAME_RE = re.compile(r"\b[\w\-]+\.\w{1,5}\b")
FOLDER_RE = re.compile(r"(\w+)\s+klas[oö]r\w*", re.IGNORECASE)
FOLDER_EN_RE = re.compile(r"(\w+)\s+(?:folder|directory)", re.IGNORECASE)
# Sadece "GG.AA.YYYY" sayisal kalibi (orn. "15.08.2026") - ayristirma/
# dogrulama YAPILMAZ, ham metin oldugu gibi tutulur (calendar Skill'i icin).
DATE_RE = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b")
# Sadece "SS:DD" sayisal kalibi (orn. "14:30") - ayristirma/dogrulama
# YAPILMAZ, ham metin oldugu gibi tutulur.
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
# Diger alanlardan farkli olarak ham metin DEGIL, sabit 3 kategoriden
# birine normalize edilir (tekrar sikligi dogasi geregi kategorik) - ama
# yine de kullanicinin GERCEKTEN yazdigi bir ifadeye dayanir, uydurma yok.
RECURRENCE_PATTERNS: dict[str, re.Pattern] = {
    "gunluk": re.compile(r"her\s+g[uü]n|g[uü]nl[uü]k", re.IGNORECASE),
    "haftalik": re.compile(r"her\s+hafta|haftal[iı]k", re.IGNORECASE),
    "aylik": re.compile(r"her\s+ay|ayl[iı]k", re.IGNORECASE),
}


def normalize(text: str) -> str:
    """Aksanlari (ör. 's' <-> 'ş') sadelestirip kucuk harfe cevirir - saf
    fonksiyon, I/O yok. PathResolver'in normalize edilmis eslesme
    kademesiyle paylasilir."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_marks.casefold()


@dataclass
class Candidates:
    quoted_spans: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    filenames: list[str] = field(default_factory=list)
    folder_names: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    times: list[str] = field(default_factory=list)
    recurrences: list[str] = field(default_factory=list)
    raw_text: str = ""


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_candidates(text: str) -> Candidates:
    """Metinden aday havuzunu cikarir. Saf fonksiyon - I/O ve LLM bagimliligi yok."""
    quoted_spans = _dedupe_preserve_order(QUOTED_RE.findall(text))
    emails = _dedupe_preserve_order(EMAIL_RE.findall(text))

    # filenames regex'i email'lerle cakisabilir (orn. "example.com" kismini
    # bagimsiz bir dosya adi gibi yakalayabilir) - email olarak zaten
    # yakalanmis olan alt-dizeleri filenames'ten dislariz.
    raw_filenames = FILENAME_RE.findall(text)
    filenames = _dedupe_preserve_order(
        [f for f in raw_filenames if not any(f in email for email in emails)]
    )

    folder_names = _dedupe_preserve_order(FOLDER_RE.findall(text) + FOLDER_EN_RE.findall(text))
    dates = _dedupe_preserve_order(DATE_RE.findall(text))
    times = _dedupe_preserve_order(TIME_RE.findall(text))
    recurrences = _dedupe_preserve_order(
        [tag for tag, pattern in RECURRENCE_PATTERNS.items() if pattern.search(text)]
    )

    return Candidates(
        quoted_spans=quoted_spans,
        emails=emails,
        filenames=filenames,
        folder_names=folder_names,
        dates=dates,
        times=times,
        recurrences=recurrences,
        raw_text=text,
    )

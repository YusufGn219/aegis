"""Kullanicinin ham mesajindan deterministik (regex tabanli) 'aday' cikarma.

Bu modul saftir: hicbir I/O, hicbir LLM cagrisi yapmaz. Amaci, LLM'in tool
cagrilarinda kullanacagi metin degerlerini KENDISI URETMESIN diye, gercekte
kullanicinin yazdigi kelimelerden bir aday havuzu cikarmaktir. LLM daha sonra
sadece bu havuzdan secim yapar (bkz. aegis.llm.prompt_builder).

Bilinen sinirlamalar (bilerek bu asamada cozulmuyor):
- Sadece Turkce "klasor" kalibi destekleniyor (ornegin "folder"/"directory"
  gibi Ingilizce esdegerleri yakalanmiyor).
- Fuzzy/normalize eslesme yok: "arsiv" ile "Arşiv" farkli string'ler olarak
  kalir (case-insensitive eslesme PathResolver'da ayrica ele alinir, ama
  aksan/karakter normalizasyonu yok).
- Dosya sistemi varlik kontrolu burada YAPILMAZ - bu modul saf metin
  islemedir, gercek path cozumlemesi aegis.resolution.path_resolver'in isi.
- Tirnak ici ifadelerin hangisinin "subject" hangisinin "body" oldugu bu
  modulun karari degil; sadece sirali bir liste doner, anlam atamasi
  Skill katmaninin sozlesmesidir (ilk tirnak = subject, ikinci = body).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

QUOTED_RE = re.compile(r"""['"]([^'"]+)['"]""")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
FILENAME_RE = re.compile(r"\b[\w\-]+\.\w{1,5}\b")
FOLDER_RE = re.compile(r"(\w+)\s+klas[oö]r\w*", re.IGNORECASE)


@dataclass
class Candidates:
    quoted_spans: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    filenames: list[str] = field(default_factory=list)
    folder_names: list[str] = field(default_factory=list)
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

    folder_names = _dedupe_preserve_order(FOLDER_RE.findall(text))

    return Candidates(
        quoted_spans=quoted_spans,
        emails=emails,
        filenames=filenames,
        folder_names=folder_names,
        raw_text=text,
    )

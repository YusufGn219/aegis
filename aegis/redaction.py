"""Fine-tuning icin disariya cikan verideki PII'yi maskeler. Ham
logs/events.jsonl'e DOKUNMAZ (orasi hala cikplak, yerel debug icindir) -
sadece export_finetune_dataset.py'nin urettigi record'lara uygulanir.

Kapsam: e-posta adresleri, dosya adlari, klasor adlari, VE (2026-08-10'dan
itibaren) `quoted_spans` (not/mail icerigi, etkinlik basligi). Once bu
sonuncusu bilerek disarida birakilmisti ("modelin ogrenmesi gereken asil
sinyal, redakte edilirse anlamsizlasir" varsayimiyla) - ama email/filename
icin zaten kullanilan AYNI teknik (gercek degeri TUTARLI bir placeholder'a
cevirmek, orn. [TEXT_1]) bu sinyali BOZMUYOR: modelin ogrenmesi gereken sey
"aday havuzundan hangi metni secip aynen kopyalayacagi" (yapisal iliski),
metnin GERCEK icerigi degil - o iliski placeholder'la da aynen korunuyor.
Gercek Gmail/Calendar entegrasyonuyla artik quoted_spans gercek kisisel
veri (mail govdesi, ozel etkinlik basligi) tasiyabildigi icin bu ayrim
onemli hale geldi. Tarih/saat/tekrar hala tek basina PII sayilmiyor.

Dosya/klasor adlari icin yeni bir regex/tahmin ICAT EDILMEDI - zaten her
istek icin loglanan "extraction" adiminin candidates'i (filenames,
folder_names) dogrudan kaynak olarak kullaniliyor (bkz.
export_finetune_dataset.py::_find_candidates). E-posta icin candidates
verilmemisse (eski loglarda extraction adimi yoksa) EMAIL_RE ile geriye
donuk regex-fallback calisir.

Ayni deger bir record icinde (kullanici mesajinda VE tool-call
argumaninda) birden fazla gecebilir - hepsi AYNI numarali placeholder'i
alir ([EMAIL_1], [FILENAME_1], [FOLDER_1], ...) ki "hangi dosya/klasor"
sinyali kaybolmasin, sadece gercek deger gizlensin. Farkli degerler farkli
numara alir.
"""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _autodetect_emails(record: dict) -> list[str]:
    seen: list[str] = []

    def _walk(value: object) -> None:
        if isinstance(value, str):
            for match in EMAIL_RE.findall(value):
                if match not in seen:
                    seen.append(match)
        elif isinstance(value, dict):
            for v in value.values():
                _walk(v)
        elif isinstance(value, list):
            for v in value:
                _walk(v)

    _walk(record)
    return seen


def _replace_all(value: object, mapping: dict[str, str], pattern: re.Pattern) -> object:
    if isinstance(value, str):
        return pattern.sub(lambda m: mapping[m.group(0)], value)
    if isinstance(value, dict):
        return {k: _replace_all(v, mapping, pattern) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_all(v, mapping, pattern) for v in value]
    return value


def redact_record(
    record: dict,
    emails: list[str] | None = None,
    filenames: list[str] | None = None,
    folder_names: list[str] | None = None,
    quoted_spans: list[str] | None = None,
) -> dict:
    """Bir fine-tuning record'undaki (user/system/tools/output) e-posta/
    dosya/klasor adlarini VE tirnakli/tetikleyici-kalipli metin parcalarini
    [KATEGORI_N] ile degistirir. `emails` verilmezse (None) EMAIL_RE ile
    geriye donuk regex-fallback calisir; `filenames`/`folder_names`/
    `quoted_spans` verilmezse o kategoriler icin hicbir redaksiyon yapilmaz
    (tahmin edilmez). Eslesme yoksa record oldugu gibi doner."""
    if emails is None:
        emails = _autodetect_emails(record)

    mapping: dict[str, str] = {}
    for category, values in (
        ("EMAIL", emails),
        ("FILENAME", filenames or []),
        ("FOLDER", folder_names or []),
        ("TEXT", quoted_spans or []),
    ):
        counter = 0
        for value in values:
            if value in mapping:
                continue
            counter += 1
            mapping[value] = f"[{category}_{counter}]"

    if not mapping:
        return record

    # Uzun degerler once eslessin diye siralanir - bir degerin baska birinin
    # alt-dizesi oldugu durumda (orn. "rapor.pdf" / "rapor.pdf.bak") yanlis
    # kismi eslesmeyi onler.
    pattern = re.compile("|".join(re.escape(v) for v in sorted(mapping, key=len, reverse=True)))
    return _replace_all(record, mapping, pattern)

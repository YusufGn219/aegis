"""Fine-tuning icin disariya cikan verideki e-posta adreslerini maskeler.
Ham logs/events.jsonl'e DOKUNMAZ (orasi hala cikplak, yerel debug icindir) -
sadece export_finetune_dataset.py'nin urettigi record'lara uygulanir.

Ayni adres bir record icinde (kullanici mesajinda VE tool-call argumaninda)
birden fazla gecebilir - hepsi AYNI numarali placeholder'i alir
([EMAIL_1], [EMAIL_2], ...) ki "kime gitti" sinyali kaybolmasin, sadece
gercek adres gizlensin. Farkli e-postalar farkli numara alir ki model
"ikisi ayni kisi mi" ayrimini ogrenebilsin.
"""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _collect_emails_in_order(value: object, seen: list[str]) -> None:
    if isinstance(value, str):
        for match in EMAIL_RE.findall(value):
            if match not in seen:
                seen.append(match)
    elif isinstance(value, dict):
        for v in value.values():
            _collect_emails_in_order(v, seen)
    elif isinstance(value, list):
        for v in value:
            _collect_emails_in_order(v, seen)


def _replace_emails(value: object, mapping: dict[str, str]) -> object:
    if isinstance(value, str):
        return EMAIL_RE.sub(lambda m: mapping[m.group(0)], value)
    if isinstance(value, dict):
        return {k: _replace_emails(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_emails(v, mapping) for v in value]
    return value


def redact_record(record: dict) -> dict:
    """Bir fine-tuning record'undaki (user/system/tools/output) e-posta
    adreslerini [EMAIL_N] ile degistirir. Eslesme yoksa record oldugu
    gibi doner."""
    seen: list[str] = []
    _collect_emails_in_order(record, seen)
    if not seen:
        return record
    mapping = {email: f"[EMAIL_{i + 1}]" for i, email in enumerate(seen)}
    return _replace_emails(record, mapping)

#!/usr/bin/env python3
"""Onceden tanimli, cesitli komutlari gercek Coordinator uzerinden (canli
vLLM'e karsi) otomatik calistirip logs/events.jsonl'i buyutur - fine-tuning
veri hacmini artirmak icin. Kendi izole (gecici) sandbox'ini kurar, gercek
workspace_sandbox/'a DOKUNMAZ. Her senaryodan sonra, senaryoyu yazarken
bilinen "dogru cevap" (beklenen tool + beklenen basari) ile gercek sonucu
karsilastirip otomatik bir "feedback" event'i loglar - export_finetune_
dataset.py bunu "label" olarak kullanir.

ONEMLI: send_email/list_inbox_emails/add_event/list_events/
list_upcoming_events/update_event/delete_event/create_note/list_notes/
update_note/delete_note artik GERCEK Google API'lerine (Gmail/Calendar/
Drive) baglaniyor (bkz. Sprint 121-124). Bu script'in amaci gercek hesaba
DEGIL, LLM'in tool-secimi/arguman-uretimi davranisina veri toplamak - bu
yuzden _mock_live_integrations() bu tool'larin GERCEK ag cagrisi yapan alt
katmanini (aegis.integrations.*) sabit/deterministik fake'lerle degistirir.
LLM cagrisi hala tamamen GERCEK (canli vLLM) - sadece Google tarafi mock'lu.

Ambiguous path-resolution gerektiren senaryolar KASITLI OLARAK yok (otomatik
etiketlemeyi bulaniklastirir, bkz. README/vault notlari). Tekrar tekrar
calistirilabilir - her calistirma yeni request_id'lerle yeni, gecerli
kayitlar ekler (temperature=0 oldugundan sonuclar genelde tutarlidir, ama
her satir bagimsiz bir egitim ornegidir).

Calistirmak icin: python run_scenarios.py (vLLM ayakta olmali)."""

from __future__ import annotations

import builtins
import shutil
import uuid
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from aegis import config
from aegis.coordinator.coordinator import Coordinator
from aegis.logging_.event_log import LogEvent, StructuredLogger
from export_finetune_dataset import load_events

# Her giris: (prompt, beklenen_tool (None = "hicbir tool cagrilmamali"),
# permission_answers (input() kuyrugu), beklenen_basari).
SCENARIOS: list[tuple[str, str | None, list[str], bool]] = [
    ("Downloads klasorundeki dosyalari listele.", "list_files", [], True),
    ("list files in the Belgeler folder", "list_files", [], True),
    ("Arsiv klasorundeki dosyalari listele.", "list_files", [], True),
    ("rapor.pdf dosyasini Arsiv klasorune tasi.", "move_file", ["y"], True),
    ("move rapor.pdf to the Belgeler folder", "move_file", ["y"], True),
    ("rapor.pdf dosyasini Belgeler klasorune tasi.", "move_file", ["y"], True),
    ("rapor.pdf dosyasini Arsiv klasorune kopyala.", "copy_file", ["y"], True),
    ("copy fatura_2026.xlsx to the Belgeler directory", "copy_file", ["y"], True),
    ("fatura_2026.xlsx dosyasini sil.", "delete_file", ["y"], True),
    ("tatil_fotograf.jpg dosyasini sil.", "delete_file", ["n"], False),
    # Mesajda hicbir aday yok (ne dosya ne klasor) - model tahmin etmek
    # yerine hicbir tool cagirmiyor (guvenli/beklenen davranis).
    ("Bir dosyayi sil.", None, [], False),
    ("Yedek klasoru olustur.", "create_folder", ["y"], True),
    # create_folder, is_filesystem_path=False oldugu icin PathResolver'in
    # aksan-normalizasyon kademesinden GECMIYOR - "zaten var" carpismasini
    # yakalamak icin var olan klasorun TAM (aksanli) adiyla yazilmali.
    ("Arşiv klasoru olustur.", "create_folder", ["y"], False),
    ("create the Yedek2026 directory", "create_folder", ["y"], True),
    (
        "ahmet@example.com adresine 'Toplanti' konulu, "
        "'Yarin saat 10da toplanti var' icerikli bir mail gonder.",
        "send_email",
        ["y"],
        True,
    ),
    ("Bugun hava nasil?", None, [], False),
    ("Yarin ne yapmaliyim?", None, [], False),
    ("Bir dosyayi Arsiv klasorune tasi.", "move_file", ["y"], False),
    # --- Notes / Calendar (notes_agent, calendar_agent) ---
    (
        "'Alisveris listesi' basligiyla 'sut, ekmek, yumurta' icerikli bir not yaz.",
        "create_note",
        ["y"],
        True,
    ),
    ("Notlarimi listele.", "list_notes", [], True),
    ("15.08.2026 tarihinde 'Toplanti' etkinligi ekle.", "add_event", ["y"], True),
    ("20.09.2026 tarihinde 'Doktor randevusu' ekle.", "add_event", ["y"], True),
    ("Etkinliklerimi listele.", "list_events", [], True),
    # Mesajda hicbir aday yok - "Bir dosyayi sil." ile ayni desen (model
    # tahmin etmek yerine tool cagirmiyor).
    ("Bir not yaz.", None, [], False),
    # "olustur" hem workspace'in (create_folder) hem notes'un (create_note)
    # dogal fiili - agent_router bunu belirsiz sayip LLM'e birakir (bkz.
    # tests/integration/test_multi_agent_routing.py). Bu senaryo LLM-
    # fallback routing yolunu da loglara ekler.
    (
        "'Alisveris listesi' basligiyla 'sut, ekmek' icerikli bir not olustur.",
        "create_note",
        ["y"],
        True,
    ),
    # Mesajda hicbir aday yok (ne baslik ne tarih) - "Bir dosyayi sil."/
    # "Bir not yaz." ile ayni guvenli-red deseni.
    ("Bir etkinlik ekle.", None, [], False),
    # Saat + tekrar etiketi (bkz. 08 sonrasi calendar genislemesi).
    (
        "15.08.2026 saat 07:30 'Spor' etkinligini haftalik olarak ekle.",
        "add_event",
        ["y"],
        True,
    ),
    ("20.09.2026 tarihinde 'Yil donumu' etkinligini her ay ekle.", "add_event", ["y"], True),
    # "hatirlat"/"goster" modeli karistirabiliyor (bkz. tests/integration/
    # test_multi_agent_routing.py) - "listele" ile tutarli sekilde calisiyor.
    ("Yaklasan etkinliklerimi listele.", "list_upcoming_events", [], True),
    # --- Ek cesitlilik (veri hacmi artirma oturumu, 2026-08-03) ---
    # Ayni "X klasorundeki" kalibi, Downloads/Arsiv disinda baska bir gercek
    # klasor (Belgeler) uzerinde de dogrulaniyor.
    ("Belgeler klasorundeki dosyalari listele.", "list_files", [], True),
    # Buyuk harf ASCII girdi - hem case-insensitive hem normalize (aksan)
    # eslesme kademesini ayni anda tetikliyor (gercek klasor "Arşiv").
    ("ARSIV klasorundeki dosyalari listele.", "list_files", [], True),
    # 2 gercek klasor adayi (Arsiv VE Belgeler) - invocation_policy
    # skip_llm=False donup akisi LLM'e dusuruyor (gercek belirsizlik).
    ("fatura_2026.xlsx dosyasini Arsiv ya da Belgeler klasorune tasi.", "move_file", ["y"], True),
    # Opsiyonel slotlarin KISMEN doldugu durumlar - bugunku invocation_policy
    # duzeltmesini (bkz. 08 nolu vault notu) canli vLLM'e karsi da dogruluyor:
    # sadece "time" var (recurrence yok) skip_llm yolunda dahi kaybolmamali.
    ("15.08.2026 saat 09:00 'Sabah toplantisi' ekle.", "add_event", ["y"], True),
    # sadece "recurrence" var (time yok).
    (
        "20.09.2026 tarihinde 'Fatura odemesi' etkinligini aylik olarak ekle.",
        "add_event",
        ["y"],
        True,
    ),
    (
        "'Market listesi' basligiyla 'sut, yumurta, ekmek' icerikli bir not ekle.",
        "create_note",
        ["y"],
        True,
    ),
    # --- Gercek Gmail/Calendar/Drive entegrasyonu (Sprint 121-124) - mock'lu ---
    ("Gelen kutumu ozetle.", "list_inbox_emails", [], True),
    # delete_event/update_event ayni tek slotu (title) add_event ile
    # paylastigi icin fiil ("sil"/"guncelle") LLM'e dusuyor, bkz.
    # tool_selection_engine._specificity_score().
    ("'Toplanti' etkinligini sil.", "delete_event", ["y"], True),
    ("'Toplanti' etkinligini saat 14:00'e guncelle.", "update_event", ["y"], True),
    ("'Alisveris listesi' notunu sil.", "delete_note", ["y"], True),
    ("'Alisveris listesi' notunu 'sut, ekmek, peynir' olarak guncelle.", "update_note", ["y"], True),
]

SEED_FOLDERS = ["Downloads", "Arşiv", "Belgeler"]
SEED_FILES = {
    "Downloads/rapor.pdf": "dummy pdf content",
    "Downloads/fatura_2026.xlsx": "dummy xlsx content",
    "Downloads/tatil_fotograf.jpg": "dummy jpg content",
}


def _seed(sandbox_root: Path) -> None:
    """seed_sandbox.py ile ayni mantik - her senaryodan once sifirdan
    kurulur, boylece senaryolar birbirinden bagimsiz (sira onemsiz) olur.
    Notes/Calendar artik local dosyaya yazmiyor (gercek Google API'lerine
    baglaniyor, bkz. _mock_live_integrations()) - burada sadece dosya-
    sistemi tabanli workspace_organizer senaryolari icin sandbox kuruluyor."""
    for folder in SEED_FOLDERS:
        path = sandbox_root / folder
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    for rel_path, content in SEED_FILES.items():
        (sandbox_root / rel_path).write_text(content, encoding="utf-8")


def _fake_event(title: str) -> dict:
    return {"id": "fake-event-1", "title": title, "when": "2026-01-01T10:00:00+03:00", "recurring": False}


def _fake_note(title: str) -> dict:
    return {"id": "fake-note-1", "title": title, "modified": "2026-01-01T10:00:00Z"}


def _mock_live_integrations() -> ExitStack:
    """send_email/add_event/create_note vb. artik GERCEK Google API'lerine
    yaziyor - bu fonksiyon o tool'larin cagirdigi aegis.integrations.*
    fonksiyonlarini (tool modullerindeki import edilmis isimleri, bkz. unit
    testlerindeki ayni patch hedefleri) sabit fake'lerle degistirir. LLM
    cagrisi (tool secimi/arguman uretimi) MOCK'LANMAZ - hala gercek vLLM'e
    gider, sadece Google tarafi devre disi. find_events_by_title/
    find_notes_by_title HER ZAMAN sorgulanan basligi yankilayan TEK bir
    sahte eslesme donerek delete/update senaryolarinin 'basarili' yolunu
    genel olarak calistirir."""
    stack = ExitStack()
    targets = [
        ("aegis.tools.send_email_tool.send_email", {"return_value": "fake-msg-1"}),
        (
            "aegis.tools.list_inbox_emails_tool.list_recent_emails",
            {
                "return_value": [
                    {
                        "from": "ornek@example.com",
                        "subject": "Ornek konu",
                        "date": "2026-01-01",
                        "snippet": "ornek onizleme",
                    }
                ]
            },
        ),
        ("aegis.tools.add_event_tool.add_event", {"return_value": "fake-event-1"}),
        ("aegis.tools.list_events_tool.list_all_events", {"return_value": [_fake_event("Ornek Etkinlik")]}),
        (
            "aegis.tools.list_upcoming_events_tool.list_upcoming_events",
            {"return_value": [_fake_event("Ornek Etkinlik")]},
        ),
        (
            "aegis.tools.update_event_tool.find_events_by_title",
            {"side_effect": lambda title, max_results=10: [_fake_event(title)]},
        ),
        ("aegis.tools.update_event_tool.update_event", {"return_value": _fake_event("Guncellenmis")}),
        (
            "aegis.tools.delete_event_tool.find_events_by_title",
            {"side_effect": lambda title, max_results=10: [_fake_event(title)]},
        ),
        ("aegis.tools.delete_event_tool.delete_event", {"return_value": None}),
        ("aegis.tools.create_note_tool.create_note", {"return_value": "fake-note-1"}),
        ("aegis.tools.list_notes_tool.list_notes", {"return_value": [_fake_note("Ornek Not")]}),
        (
            "aegis.tools.update_note_tool.find_notes_by_title",
            {"side_effect": lambda title, max_results=10: [_fake_note(title)]},
        ),
        ("aegis.tools.update_note_tool.update_note", {"return_value": _fake_note("Guncellenmis")}),
        (
            "aegis.tools.delete_note_tool.find_notes_by_title",
            {"side_effect": lambda title, max_results=10: [_fake_note(title)]},
        ),
        ("aegis.tools.delete_note_tool.delete_note", {"return_value": None}),
    ]
    for target, kwargs in targets:
        stack.enter_context(patch(target, **kwargs))
    return stack


def _fake_input_queue(answers: list[str]):
    queue = list(answers)

    def _input(prompt: str = "") -> str:
        if not queue:
            raise AssertionError(f"Senaryo beklenenden fazla input() cagirdi: {prompt!r}")
        return queue.pop(0)

    return _input


def _actual_tool(events: list[dict], request_id: str) -> str | None:
    tool = None
    for event in events:
        if event.get("request_id") != request_id:
            continue
        if event.get("step") in ("llm_call", "invocation_decision", "tool_execute") and event.get(
            "tool"
        ):
            tool = event["tool"]
    return tool


def run_scenario(
    prompt: str,
    expected_tool: str | None,
    permission_answers: list[str],
    expected_success: bool,
    coordinator: Coordinator,
    logger: StructuredLogger,
    sandbox_root: Path,
) -> tuple[bool, str | None, bool]:
    _seed(sandbox_root)
    request_id = str(uuid.uuid4())

    original_input = builtins.input
    builtins.input = _fake_input_queue(permission_answers)
    try:
        result = coordinator.route(prompt, request_id, logger)
    finally:
        builtins.input = original_input

    events = load_events(Path(logger.path))
    actual_tool = _actual_tool(events, request_id)
    is_correct = actual_tool == expected_tool and result.success == expected_success

    logger.log(
        LogEvent(
            request_id=request_id,
            step="feedback",
            decision="otomatik senaryo degerlendirmesi",
            success=True,
            user_feedback="dogru" if is_correct else "yanlis",
        )
    )
    return is_correct, actual_tool, result.success


def main() -> None:
    logger = StructuredLogger()
    coordinator = Coordinator()

    with TemporaryDirectory() as tmp, _mock_live_integrations():
        sandbox_root = Path(tmp)
        config.SANDBOX_ROOT = sandbox_root

        passed = 0
        for prompt, expected_tool, permission_answers, expected_success in SCENARIOS:
            is_correct, actual_tool, actual_success = run_scenario(
                prompt, expected_tool, permission_answers, expected_success, coordinator, logger, sandbox_root
            )
            passed += is_correct
            status = "OK" if is_correct else "FARK"
            print(
                f"[{status}] {prompt!r} -> tool={actual_tool!r} success={actual_success} "
                f"(beklenen: tool={expected_tool!r} success={expected_success})"
            )

    print(f"\n{passed}/{len(SCENARIOS)} senaryo beklenen sonuca ulasti.")
    print(f"Loglar: {logger.path}")


if __name__ == "__main__":
    main()

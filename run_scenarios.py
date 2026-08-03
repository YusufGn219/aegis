#!/usr/bin/env python3
"""Onceden tanimli, cesitli komutlari gercek Coordinator uzerinden (canli
vLLM'e karsi) otomatik calistirip logs/events.jsonl'i buyutur - fine-tuning
veri hacmini artirmak icin. Kendi izole (gecici) sandbox'ini kurar, gercek
workspace_sandbox/'a DOKUNMAZ. Her senaryodan sonra, senaryoyu yazarken
bilinen "dogru cevap" (beklenen tool + beklenen basari) ile gercek sonucu
karsilastirip otomatik bir "feedback" event'i loglar - export_finetune_
dataset.py bunu "label" olarak kullanir.

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
from pathlib import Path
from tempfile import TemporaryDirectory

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
    Notes/Calendar tool'larinin yazdigi Notlar/ ve calendar.json da (varsa,
    onceki senaryolardan kalma) temizlenir - aksi halde ayni basligi
    kullanan iki senaryo yapay bir "zaten var" carpismasi yasar."""
    for folder in SEED_FOLDERS:
        path = sandbox_root / folder
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    for rel_path, content in SEED_FILES.items():
        (sandbox_root / rel_path).write_text(content, encoding="utf-8")

    notes_dir = sandbox_root / "Notlar"
    if notes_dir.exists():
        shutil.rmtree(notes_dir)
    calendar_path = sandbox_root / "calendar.json"
    if calendar_path.exists():
        calendar_path.unlink()


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

    with TemporaryDirectory() as tmp:
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

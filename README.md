# aegis

Yerel-öncelikli (local-first) kişisel AI işletim katmanının ilk dikey dilimi:
Coordinator → Agent → Skill → deterministik extraction → enum-kısıtlı LLM
seçimi → Permission Engine → Tool execution.

Model sunucusu olarak ayrı bir `vLLM_projects` reposundaki vLLM sunucusunu
(Qwen2.5-1.5B-Instruct, `http://localhost:8000/v1`) HTTP üzerinden kullanır.

## Kurulum

```bash
pip install -e ".[dev]"
```

vLLM sunucusunun `--enable-auto-tool-choice --tool-call-parser hermes` ile
ayakta olduğundan emin olun (bkz. `vLLM_projects/docker-compose.yml`).

## Sandbox'ı hazırlama

Tool'lar (`list_files`, `move_file`) **gerçek Masaüstü/İndirilenler'e asla
dokunmaz** — sadece `workspace_sandbox/` içindeki izole test verisiyle çalışır.

```bash
python seed_sandbox.py
```

Bu, `workspace_sandbox/Downloads`, `Arşiv`, `Belgeler` klasörlerini sıfırlayıp
sahte dosyalarla doldurur. İdempotenttir, istediğiniz kadar tekrar
çalıştırabilirsiniz.

## Çalıştırma

```bash
python -m aegis "Downloads klasöründeki dosyaları listele"
python -m aegis "rapor.pdf dosyasını Arşiv klasörüne taşı"
python -m aegis "ahmet@example.com adresine 'Toplantı' konulu, 'Yarın saat 10da toplantı var' içerikli bir mail gönder."
```

- `list_files` (LOW risk) onaysız çalışır.
- `move_file`/`send_email` (MEDIUM risk) gerçek çözümlenmiş değerleri
  gösterip `[y/N]` onayı ister.
- `send_email` bu sürümde **mock** — gerçekten mail göndermez, sadece
  loglar.

## Testler

```bash
python -m pytest tests/ -m "not integration"   # LLM/ağ gerektirmez
python -m pytest tests/ -m integration          # canlı vLLM sunucusu gerekir
```

## Loglar

Her adım `logs/events.jsonl` dosyasına tek satır JSON olarak yazılır
(extraction, invocation_decision, llm_call, path_resolution, permission,
tool_execute). İleride DuckDB ile analiz edilebilecek düz bir şemada.

## Mimari İlke

LLM sadece "hangi tool" ve "birden fazla aday arasından hangisi" gibi seçim
kararları verir. Path/içerik gibi serbest metin alanları LLM'e hiç
**üretme** yetkisi olarak verilmez — bunun yerine kullanıcının mesajından
deterministik regex ile çıkarılan gerçek adaylar arasından, JSON schema
`enum` kısıtıyla seçim yaptırılır. Bu, serbest üretimin yol açtığı
halüsinasyonu (uydurma path, bozulan içerik) yapısal olarak imkansız hale
getirir — ayrıntılı gerekçe için `vLLM_projects/scripts/tool_call_test.py`
prototipine bakılabilir.

## Kapsam Dışı (İleri Fazlar)

Memory (working/long-term/episodic/semantic), Learning Engine, DuckDB
Analytics, Vector/Graph arama, gerçek Mail entegrasyonu (Graph API/IMAP),
çoklu-Agent yönlendirmesi, FastAPI/PySide6/web UI — hepsi bilerek bu
dilimin dışında. Arayüzler (`Coordinator.route`, `Agent.handle`) bunlara
hazır şekilde tasarlandı ama kod yazılmadı.

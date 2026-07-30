# aegis

Doğal dil komutlarıyla dosya işlemleri yapan, yerel bir vLLM sunucusu
kullanan asistan (V1.0.0). Verileriniz bilgisayarınızdan çıkmaz; komutunuz
sadece kendi makinenizde çalışan modele gider. `aegis`, "dosyayı taşı" gibi
bir isteği aldığında modelin kendi başına path/içerik uydurmasına izin
vermez — önce mesajınızdan gerçek dosya/klasör adlarını çıkarır, modele
sadece bunlar arasından seçim yaptırır ve riskli işlemlerden (taşıma,
gönderme gibi) önce size gerçek değerleri gösterip onay ister. Şu an
desteklenen işlemler: bir klasördeki dosyaları listeleme, bir dosyayı başka
bir klasöre taşıma ve (deneysel/mock) e-posta gönderme.

## Gereksinimler

- Python 3.10+
- Bilgisayarda Docker üzerinde aktif olarak çalışan bir vLLM modeli olmalı
  (tool-calling için `--enable-auto-tool-choice --tool-call-parser hermes`
  ile başlatılmış). Varsayılan adres `http://localhost:8000/v1`'dir, farklı
  bir port/adres kullanıyorsanız `AEGIS_VLLM_BASE_URL` ortam değişkeniyle
  belirtebilirsiniz. Bu repo model içermez, sadece var olan bir vLLM
  sunucusuna bağlanır.

## Kurulum

```bash
pip install -e ".[dev]"
```

## Sandbox'ı hazırlama

```bash
python seed_sandbox.py
```

`workspace_sandbox/` içindeki test klasörlerini (Downloads, Arşiv, Belgeler)
sahte dosyalarla sıfırlar. Tekrar tekrar çalıştırılabilir.

## Çalıştırma

```bash
python -m aegis "Downloads klasöründeki dosyaları listele"
python -m aegis "rapor.pdf dosyasını Arşiv klasörüne taşı"
```

`move_file`/`send_email` gibi işlemler öncesinde onay ister (`[y/N]`).

Gerçek bir klasörle çalışmak için `AEGIS_SANDBOX_ROOT` ortam değişkenini
ayarlayın:

```bash
export AEGIS_SANDBOX_ROOT="C:/Users/<kullanici_adi>"
```

## Testler

```bash
python -m pytest tests/ -m "not integration"   # LLM/ağ gerektirmez
python -m pytest tests/ -m integration          # canlı vLLM sunucusu gerekir
```

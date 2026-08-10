# aegis

Doğal dil komutlarıyla dosya işlemleri yapan, yerel bir vLLM sunucusu
kullanan asistan (V1.0.0). Verileriniz bilgisayarınızdan çıkmaz; komutunuz
sadece kendi makinenizde çalışan modele gider. `aegis`, "dosyayı taşı" gibi
bir isteği aldığında modelin kendi başına path/içerik uydurmasına izin
vermez — önce mesajınızdan gerçek dosya/klasör adlarını çıkarır, modele
sadece bunlar arasından seçim yaptırır ve riskli işlemlerden (taşıma,
gönderme gibi) önce size gerçek değerleri gösterip onay ister. Şu an
desteklenen işlemler: bir klasördeki dosyaları listeleme, bir dosyayı başka
bir klasöre taşıma, Gmail üzerinden e-posta gönderme/gelen kutusu özetleme
ve Google Calendar üzerinde etkinlik ekleme/listeleme.

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

## Google Kurulumu (Gmail + Calendar için)

`send_email`/`list_inbox_emails`/`add_event`/`list_events`/
`list_upcoming_events` tool'ları TEK bir Google OAuth client'ı ve TEK bir
`token.json` üzerinden 3 scope kullanır: `gmail.send`, `gmail.readonly`,
`calendar.events` (takvim ayarlarına/paylaşıma dokunmaz, sadece etkinlik
oluşturma/okuma). Bunların hepsi Google'ın "hassas scope" sınıfına girer —
uygulama "Testing" modunda ve hesap test kullanıcısı olarak eklendiği
sürece Google'ın ayrı bir doğrulama sürecine gerek kalmaz. Tek seferlik
kurulum:

1. [Google Cloud Console](https://console.cloud.google.com/)'da bir proje
   açın (veya var olanı kullanın) ve **Gmail API** + **Google Calendar
   API**'yi etkinleştirin (APIs & Services → Library).
2. **APIs & Services → OAuth consent screen**'i "External" + "Testing"
   modunda ayarlayıp kullanılacak Google hesabını test kullanıcısı olarak
   ekleyin.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**,
   uygulama tipi **Desktop app** seçin, indirin.
4. İndirilen dosyayı proje köküne `credentials.json` adıyla koyun (repo'ya
   commit edilmez, `.gitignore`'da).
5. İlk canlı çağrıda (send_email/add_event/...) tarayıcı açılır, hesabınızla
   giriş yapıp **3 scope'un tamamı için** izin verin. Onay sonrası
   `token.json` oluşur ve sonraki çalıştırmalarda otomatik yenilenir
   (tekrar tarayıcı açılmaz).

Farklı bir dosya konumu istiyorsanız `AEGIS_GOOGLE_CREDENTIALS_PATH` /
`AEGIS_GOOGLE_TOKEN_PATH` ortam değişkenleriyle override edebilirsiniz.

Scope seti değiştiğinde (örn. ileride yeni bir Google izni eklenirse) var
olan `token.json` eski scope'larla üretilmiş olduğundan geçersiz kalır —
dosyayı silip ilk çağrıda tarayıcı onayını tekrar vermeniz gerekir.

Takvim etkinlikleri `Europe/Istanbul` saat diliminde oluşturulur
(`aegis/integrations/calendar_client.py`'de sabit); saat verilmezse
gün-boyu (all-day) etkinlik oluşur, tekrar (`gunluk`/`haftalik`/`aylik`)
Google'ın kendi RRULE mekanizmasına devredilir.

## Çalıştırma

```bash
python -m aegis "Downloads klasöründeki dosyaları listele"
python -m aegis "rapor.pdf dosyasını Arşiv klasörüne taşı"
```

`move_file`/`send_email`/`add_event` gibi işlemler öncesinde onay ister (`[y/N]`).

**E-posta konu/gövdesi tek tırnak içinde yazılmalı** — `aegis` bu metni
LLM'in kendi kelimeleriyle üretmesine izin vermez, sadece sizin mesajınızda
tırnak içinde geçen ifadeleri kullanabilir (bkz. "Nasıl Çalışır"). Örnek:

```powershell
python -m aegis "ahmet@example.com adresine 'Toplanti' konulu 'Yarin saat 10da gorusuruz' icerikli mail gonder"
```

Tırnaksız yazarsanız ("...ahmete merhaba diye bir mail at" gibi) `aegis`
konu/gövdeyi kendi başına uydurmak yerine eksik bilgi hatası verir.

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

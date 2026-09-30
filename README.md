# Genç MMG Etkinlik Onay Platformu

Şube başkanlarının etkinlik taleplerini Genel Merkez onayına sunduğu, onay sürecini ve yanıt sürelerini takip eden Streamlit uygulaması.

## Roller

| Rol | Değer (Sheets) | Erişim |
|---|---|---|
| Şube Başkanı | `Sube_Baskani` | Yalnızca kendi ili: talep oluşturur, ilinin taleplerini takip eder |
| Genel Merkez YK Üyesi | `YK_Uyesi` | Tüm illerin taleplerini ve raporları görür; onay vermez |
| Genel Merkez Yöneticisi | `Admin` | Tüm sayfalar; talepleri onaylayan/reddeden tek rol, kullanıcılar ve sistem ayarları |

Şube başkanlarının `il_kodu` değeri `core/provinces.py` içindeki illerden biri olmalıdır; aksi hâlde giriş yapamazlar. Genel Merkez hesapları için `il_kodu` `00` kullanılır.

Eski sürümlerden kalan değerler otomatik eşlenir: `Il_Temsilcisi` → Şube Başkanı, `Merkez_Onayci` → YK Üyesi (onay yetkisi yalnızca yöneticilerde olduğundan). Tanınmayan rol değerine sahip hesaplar giriş yapamaz.

Giriş, kayıtlı e-posta adresine gönderilen 6 haneli tek kullanımlık kodla yapılır.

## Proje yapısı

```
app.py                 Giriş noktası; oturum ve role göre navigasyon
core/
  auth.py              OTP girişi, oturum, rol kontrolü
  domain.py            Roller, durumlar, Sheets şeması
  event_requests.py    Talep oluşturma, karar, SLA hesapları
  notifications.py     Gmail SMTP ve e-posta şablonları
  repository.py        Google Sheets erişimi (cache'li)
  settings.py          secrets.toml okuma
  provinces.py         Talep açabilen iller
  validation.py        Form doğrulama kuralları
  attachments.py       Talep eklerinin Google Drive'a yüklenmesi
ui/                    Tema ve ortak bileşenler
views/                 Sayfalar
scripts/setup_sheets.py     Sheets tablolarını ve kullanıcıları hazırlar
scripts/apps_script/Code.gs Talep eklerini Drive'a kaydeden Apps Script
```

## Yerel kurulum

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # değerleri doldurun
python scripts/setup_sheets.py  # ilk kurulumda bir kez
streamlit run app.py
```

Python 3.11 veya üstü gerekir.

## Yapılandırma

`.streamlit/secrets.toml` (git'e eklenmez; Streamlit Cloud'da **Settings → Secrets**):

- `[gcp_service_account]`: Service account JSON anahtarı. Hesabın e-postasına Sheets dosyasında düzenleme yetkisi verin.
- `[sheets] spreadsheet_id`: Hedef Google Sheets dosyasının kimliği.
- `[email]`: Gönderen Gmail adresi, [uygulama şifresi](https://myaccount.google.com/apppasswords) ve bildirimlerin gideceği merkez adresi.
- `[admin]` / `[[admins]]`: Yönetici hesapları.
- `[drive]`: Talep ekleri için Apps Script adresi ve anahtarı (aşağıya bakın).
- `[[users]]` (isteğe bağlı): Sheets dışında tanımlanan kullanıcılar.

Diğer kullanıcılar Sheets'teki `Kullanici_Rolleri` sayfasından (`email`, `il_kodu`, `rol`) okunur.

## Talep ekleri (Google Drive)

Talep oluştururken en fazla 5 dosya (dosya başına 10 MB) eklenebilir. Dosya eklenmezse nedeninin yazılması zorunludur. Dosyalar Sheets'teki `ek_dosyalar` kolonuna `ad | link` satırları olarak, nedenler de `ek_dosya_yok_gerekce` kolonuna yazılır.

Service account'ların Drive depolama kotası olmadığı için dosyaları, sahibi olacak hesapta (ör. kurumun Gmail hesabı) çalışan küçük bir Apps Script kaydeder:

1. Dosyaların sahibi olacak hesapla [script.google.com](https://script.google.com) → **Yeni proje**.
2. `scripts/apps_script/Code.gs` içeriğini editöre yapıştırıp kaydedin.
3. Üstteki fonksiyon listesinden `setup` seçip **Çalıştır**. İzin isteğini onaylayın ("doğrulanmamış uygulama" uyarısında *Gelişmiş → devam et*). Yürütme günlüğündeki `UPLOAD_TOKEN` değerini kopyalayın.
4. **Dağıt → Yeni dağıtım → Web uygulaması**: *Şu kullanıcı olarak yürüt:* Ben, *Erişimi olanlar:* Herkes. Web uygulaması URL'sini kopyalayın.
5. `secrets.toml` (ve Streamlit Cloud secrets) içinde `[drive]` bölümüne `upload_url` ve `upload_token` değerlerini yazın.
6. Uygulamayı yeniden başlatıp Yönetim paneli → Sistem → **Drive'ı test et** ile doğrulayın.

Dosyalar Drive'da "Genç MMG Talep Ekleri" klasörüne kaydedilir ve "bağlantıya sahip olan herkes görüntüleyebilir" olarak paylaşılır; linkler yalnızca oturum açmış kullanıcılara gösterilir. Script'i güncellerseniz **Dağıtımları yönet → Düzenle → Yeni sürüm** ile aynı URL'yi koruyun.

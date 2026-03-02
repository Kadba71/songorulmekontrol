# Telegram Son Görülme Takip Botu

Bu proje, Telegram üzerinde tanımladığınız personellerin son görülme bilgisini izler ve eşik süre aşıldığında rapor mesajı gönderir.

## Önemli Teknik Not
Telegram Bot API tek başına kullanıcıların `last seen` bilgisini güvenilir şekilde vermez. Bu yüzden:

- Komutlar için **Bot Token** kullanılır.
- Son görülme kontrolü için **Telethon + User API session** kullanılır.

Bu yüzden `.env` içinde hem bot hem de Telethon ayarları gerekir.

## Kurulum

1. Python 3.11+ kurulu olsun.
2. Proje klasöründe:

```bash
pip install -r requirements.txt
```

3. `.env.example` dosyasını `.env` olarak kopyalayıp doldurun.

	Notlar:
	- `ALERT_CHAT_ID` zorunludur. Alarm ve günlük raporlar yalnızca bu sohbete gider.
	- `APP_TIMEZONE` ile zaman dilimini belirleyin (varsayılan: `Europe/Istanbul`).

4. Botu çalıştırın:

```bash
python bot.py
```

## Komutlar

- `/sure 20, satısekibi1`
- `/sureguncelle 25, satısekibi1`
- `/personelekle @ahmet_taha, @ayse_su, satısekibi2`
- `/silpersonel @ahmet_taha`
- `/eklesorumlu @ayse_su, satısekibi1`
- `/silsorumlu @ayse_su, satısekibi1`
- `/ekledepartman satısekibi1`
- `/sildepartman satısekibi1`
- `/haftalikizin satısekibi1, çarşamba`
- `/izin @ahmet_taha`
- `/saatlikizin @ahmet_taha, 2 saat`
- `/yukle` (Excel dosyasını açıklama/caption olarak `/yukle` yazarak gönderin)
- `/rapor satısekibi1` (ilgili departmanın gün içi kural ihlali adedi)
- `/listele`
- `/help`

## Excel ile Toplu Personel Ekleme

`/yukle` komutu için dosyayı gruba **doküman** olarak gönderin ve açıklama kısmına `/yukle` yazın.

Desteklenen format: `.xlsx` / `.xlsm`

Sütun düzeni:

- A sütunu: Personel Telegram kullanıcı adı (örn: `@mertcantest`)
- B sütunu: Sorumlu Telegram kullanıcı adı (örn: `@murat1`)
- C sütunu: Departman adı (örn: `SATISEKIBI1`)

Boş satırlar atlanır, eksik hücreli satırlar raporda "hatalı satır" olarak listelenir.

## Alarm Mesajı Formatı

```text
Personel : @ahmet_tahta
Son görülme : 17 dakika
Sorumlu : @ayse_su
Departman : satısekibi3
```

## Çalışma Mantığı

- Bot, `CHECK_INTERVAL_SECONDS` aralığında personelleri tarar.
- Son görülme dakikası departman eşik değerini aşarsa alarm üretir.
- Aynı personel için tekrar alarm üretimi `ALERT_COOLDOWN_MINUTES` ile sınırlandırılır.
- Haftalık izin günü tanımlanan departmanlar o gün taranmaz.
- `/izin` ile işaretlenen personel gün boyu taranmaz.
- `/saatlikizin` ile işaretlenen personel belirtilen süre boyunca taranmaz.

## Dikkat

- Kullanıcı gizlilik ayarları nedeniyle bazı hesaplarda dakika bazlı son görülme alınamayabilir (`yakınlarda`, `son 1 hafta içinde` vb.).
- Bu durumlarda sistem dakika bazlı eşik kontrolü yapamaz.

## Güvenlik

- `.env` dosyasını asla repoya göndermeyin.
- Token veya `TELETHON_STRING_SESSION` sızıntısı şüphesinde hemen rotate/revoke edin.
- Üretim ortamında düzenli gizli anahtar yenileme (rotation) uygulayın.

## Railway ile Yayınlama (Gizli Bilgileri GitHub'da Açmadan)

1. GitHub'a sadece kaynak kodu gönderin. `.env` ve benzeri dosyalar `.gitignore` ile hariç tutulur.
2. Railway'de projeyi GitHub reposundan bağlayın.
3. Railway > Project > Variables bölümünden aşağıdaki değişkenleri ekleyin:
	- `BOT_TOKEN`
	- `ALERT_CHAT_ID`
	- `TELEGRAM_API_ID`
	- `TELEGRAM_API_HASH`
	- `TELETHON_STRING_SESSION`
	- `APP_TIMEZONE` (ör. `Europe/Istanbul`)
	- İhtiyaca göre diğer ayarlar (`CHECK_INTERVAL_SECONDS`, `ALERT_COOLDOWN_MINUTES` vb.)
4. Bu repo içindeki `railway.json` dosyası ile Railway botu `python bot.py` komutuyla worker olarak başlatır.

### Önemli Not (Daha önce sızdırıldıysa)

- Eğer token/session bilgilerini daha önce bir yere yüklediyseniz, yalnızca `.gitignore` yetmez.
- İlgili token/session değerlerini hemen yenileyin (rotate/revoke).

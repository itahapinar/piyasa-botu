# Sabah Piyasa Botu

Her sabah Telegram'a tek bir mesaj gönderen küçük bir bot. Mesajda iki bölüm var:

1. **Değerli metaller** — gram/ons altın ve gram/ons gümüşün son fiyatı ve 1 haftalık % değişimi
2. **Yükselenler** — Borsa İstanbul'da belirlenen eşiğin üzerinde kapatan hisseler, pazarına göre gruplanmış ve BIST Katılım Tüm (XKTUM) kapsamındakiler ☪️ ile işaretlenmiş

Sunucuya ihtiyaç yok: GitHub Actions her gün 09:00 TSİ'de çalıştırıyor.

## Örnek mesaj

```
📊 Günaydın — 22.08.2026

💰 Değerli Metaller (21.08.2026 kapanışı)
🟢 Gram Altın: 4.312 TL  (1H: +1,84%)
🟢 Ons Altın: 3.421 $  (1H: +0,92%)
🔴 Gram Gümüş: 49 TL  (1H: -2,10%)
🔴 Ons Gümüş: 38 $  (1H: -2,74%)

🚀 %9+ kapatanlar (21.08.2026)

— Yıldız Pazar (2)
• ABCDE:  14,72 TL  +9,84%  (1H: +12,3%) ☪️
• FGHIJ:  8,05 TL  +9,21%  (1H: ~+9,2%)

— Ana / Alt Pazar (1)
• KLMNO:  3,41 TL  +9,97%  (1H: +18,5%) ☪️

— Diğer (1)
• PQRST:  306,75 TL  +9,55%  (1H: -2,9%)

☪️ = BIST Katılım Tüm (XKTUM) kapsamında

~ = 7 günlük geçmiş yok; en eski kayda göre hesaplandı.
```

## Kurulum

### 1. Telegram botunu aç

1. Telegram'da [@BotFather](https://t.me/BotFather) ile konuş, `/newbot` de, sana bir **token** verecek.
2. Kendi botunla bir sohbet başlat (`/start` yaz) — bot sana ilk mesajı ancak sen yazdıktan sonra gönderebilir.
3. **Chat ID**'ni öğren: `https://api.telegram.org/bot<TOKEN>/getUpdates` adresini tarayıcıda aç, `"chat":{"id":...}` alanına bak.

### 2. Repo'yu fork'la ve secret'ları gir

`Settings → Secrets and variables → Actions → New repository secret`:

| Secret | Açıklama |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather'ın verdiği token |
| `TELEGRAM_CHAT_ID` | Mesajın gideceği sohbetin ID'si |

### 3. Workflow'u test et

`Actions → Sabah Piyasa Botu → Run workflow`. Buradan eşiği elle de girebilirsin (varsayılan `9.0`).

Fork'larda zamanlanmış workflow'lar varsayılan olarak kapalıdır; Actions sekmesinde bir kez etkinleştirmen gerekir.

## Yerelde çalıştırma

```bash
pip install -r requirements.txt

# Sadece ekrana yaz, Telegram'a gönderme (token gerekmez)
python bot.py --dry

# Gerçekten gönder
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="987654321"
python bot.py
```

Windows PowerShell'de `export` yerine `$env:TELEGRAM_BOT_TOKEN = "..."`.

## Ayarlar

Hepsi ortam değişkeni:

| Değişken | Zorunlu | Varsayılan | Ne işe yarar |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | evet* | — | Bot token'ı |
| `TELEGRAM_CHAT_ID` | evet* | — | Hedef sohbet |
| `TAVAN_ESIK` | hayır | `9.0` | Bu yüzdenin üstünde kapatan hisseler listelenir |

\* `--dry` ile çalıştırırken gerekmez.

`TAVAN_ESIK` ondalık ayırıcı olarak virgülü de kabul eder (`9,5`), bozuk bir değer gelirse varsayılana döner.

### Çalışma saatini değiştirme

`.github/workflows/daily.yml` içindeki cron **UTC**'dir, Türkiye UTC+3:

```yaml
- cron: "0 6 * * *"   # 09:00 TSİ, her gün
- cron: "0 6 * * 1-5" # 09:00 TSİ, sadece hafta içi
```

GitHub'ın tam saatleri (`:00`) yoğun olduğu için gecikme büyüyebilir; dakikayı kaydırmak (`"7 6 * * *"`) daha isabetli sonuç verir.

## Nasıl çalışıyor

Veriler [`borsapy`](https://pypi.org/project/borsapy/) üzerinden alınıyor.

### Metaller

Her sembolün 1 aylık kapanış serisi çekiliyor, son fiyat ile 7 gün öncesinin (ya da ondan eski en yakın kaydın — tatile denk gelebilir) farkı yüzde olarak hesaplanıyor. 7 günlük geçmiş yoksa en eski kayda göre hesaplanıp `~` ile işaretleniyor.

Ons altın bir istisna: `borsapy`'nin `ons-altin` serisi canlidoviz'in `METAL_IDS` listesinden geliyor ve TL cinsinden fiyat veriyor, dolar diye göstermek ~25 kat hatalı sonuç üretiyordu. Bu yüzden ons altın doğrudan TradingView'daki `OANDA:XAUUSD`'den çekiliyor. Ons gümüş (`XAG-USD`) `COMMODITY_IDS`'ten geldiği için zaten gerçek USD.

### Hisseler

1. `XYLDZ`, `XUTUM` ve `XYORT` endeks bileşenlerinden pazar etiketleri çıkarılıyor (Yıldız Pazar / Ana-Alt Pazar / Yatırım Ortaklıkları), ardından tarama evreni `bp.companies()` ile BIST'in tamamına genişletiliyor. Endekslerde yer almayan hisseler **Diğer** başlığı altında listeleniyor — sadece endeks bileşenlerine bakmak, endekslere henüz girmemiş yeni şirketleri ve Yakın İzleme Pazarı'ndakileri kaçırıyordu.
2. `bp.scan(...)` ile eşiği aşanlar **tek istekte** bulunuyor (filtreleme TradingView sunucusunda yapılıyor).
3. Adaylar gerçek kapanış verisiyle tek tek doğrulanıyor, haftalık değişim de burada çıkarılıyor.
4. Sonuçlar pazara göre gruplanıp günlük değişime göre sıralanıyor.

### Katılım işareti (☪️)

`XKTUM` (BIST Katılım Tüm) bileşenleri her çalıştırmada taze çekiliyor, listedeki hisselere ☪️ konuyor. Elle bakım gerekmiyor: `borsapy` bu veriyi Borsa İstanbul'un kendi yayınladığı bileşen dosyasından (`borsaistanbul.com/datum/hisse_endeks_ds.csv`) alıyor, dolayısıyla kaynak resmî ve dönemsel endeks revizyonlarını kendiliğinden takip ediyor.

**Ne anlama gelmediğine dikkat.** ☪️ yokluğu "katılım finans ilkelerine uygun değil" demek değil, sadece "XKTUM'da değil" demek. XKTUM yalnızca Yıldız, Ana ve Alt Pazar'daki uygun payları kapsıyor; bu yüzden mesajdaki **Diğer** grubundaki hisseler (henüz endekse girmemiş yeni şirketler, Yakın İzleme Pazarı'ndakiler) uygun olsalar bile hiçbir zaman ☪️ alamaz. Kesin karar için şirketin KAP'taki Katılım Finans İlkeleri Bilgi Formu'na bakmak gerekir.

Liste hiç gelmezse mesaj sessizce işaretsiz gitmiyor; dipnotun yerine açık bir uyarı satırı konuyor, yoksa işaretsiz liste "bugün hiçbiri uygun değil" diye okunurdu.

### Dayanıklılık

- Tarama boş dönerse `change_percent > 0.5` ile sağlama yapılıyor — "kimse yükselmedi" ile "veri hiç gelmedi" ayırt ediliyor, ikincisinde mesaja uyarı düşülüyor.
- Aday sayısı 100'ü aşarsa (`MAX_DOGRULAMA`) tek tek doğrulama atlanıyor, sadece kodlar listeleniyor.
- Bir metal kaynağı çökerse o satır `⚠️ veri alınamadı` olup mesajın geri kalanı yine gidiyor.
- Katılım listesi alınamazsa ☪️ işaretleri düşüyor ama mesaja bunu söyleyen bir uyarı ekleniyor.
- Endeks bileşenlerinin **hiçbiri** alınamazsa iş hataya düşürülüyor; yarım evrenle yanıltıcı liste üretilmiyor.
- Telegram'ın 4096 karakter sınırına takılmamak için uzun listeler 4000 karakterde kırpılıyor.

## Dosyalar

```
bot.py                       tüm mantık (veri çekme, biçimlendirme, gönderme)
requirements.txt             borsapy, pandas, requests
.github/workflows/daily.yml  günlük cron + elle tetikleme
```

## Not

Veriler halka açık kaynaklardan alınıyor, doğruluğu ya da sürekliliği garanti edilmez. Bu bot yatırım tavsiyesi değildir.

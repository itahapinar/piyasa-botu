# Sabah Piyasa Botu

Her sabah Telegram'a tek bir mesaj gönderen küçük bir bot. Mesajda iki bölüm var:

1. **Değerli metaller** — gram/ons altın ve gram/ons gümüşün son kapanışı ve 1 haftalık % değişimi
2. **Yükselenler** — Borsa İstanbul'da belirlenen eşiğin üzerinde kapatan hisseler, pazarına göre gruplanmış ve BIST Katılım Tüm (XKTUM) kapsamındakiler ☪️ ile işaretlenmiş

Her iki bölüm de **son kapanmış seansa** ait; bot saat kaçta çalışırsa çalışsın rakamlar değişmez.

Sunucuya ihtiyaç yok: iş GitHub Actions'ta çalışıyor, her sabah 08:50 TSİ'de dışarıdan tetikleniyor ([neden dışarıdan?](#4-günlük-tetikleyiciyi-kur)).

## Örnek mesaj

```
📊 Günaydın — 22.08.2026

💰 Değerli Metaller (21.08.2026 kapanışı)
🟢 Gram Altın: 4.312 TL  (1H: +1,84%)
🟢 Ons Altın: 3.421 $  (1H: +0,92%)
🔴 Gram Gümüş: 49,17 TL  (1H: -2,10%)
🔴 Ons Gümüş: 38,04 $  (1H: -2,74%)

🚀 %9+ kapatanlar (21.08.2026)

— Yıldız Pazar (2)
• ABCDE:  14,72 TL  +9,84%  (1H: +12,3%)  🔥3 gün ☪️
• FGHIJ:  8,05 TL  +9,21%  (1H: ~+9,2%)

— Ana / Alt Pazar (1)
• KLMNO:  3,41 TL  +9,97%  (1H: +18,5%) ☪️

— Diğer (1)
• PQRST:  306,75 TL  +9,55%  (1H: -2,9%)

🔥 = üst üste %9+ kapattığı gün sayısı

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

Bu adım aynı zamanda bir sonraki adımın ön koşulu: `workflow_dispatch` bir kez çalışmadan GitHub API'si o workflow'u tetiklenebilir görmeyebiliyor.

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

Windows konsolu varsayılan olarak cp1252 kullanıyor; `--dry` çıktısındaki emojiler `UnicodeEncodeError` verirse önce `$env:PYTHONIOENCODING = "utf-8"` deyin. Telegram'a gönderim bundan etkilenmiyor, sorun sadece ekrana yazarken çıkıyor.

## Ayarlar

Hepsi ortam değişkeni:

| Değişken | Zorunlu | Varsayılan | Ne işe yarar |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | evet* | — | Bot token'ı |
| `TELEGRAM_CHAT_ID` | evet* | — | Hedef sohbet |
| `TAVAN_ESIK` | hayır | `9.0` | Bu yüzdenin üstünde kapatan hisseler listelenir |

\* `--dry` ile çalıştırırken gerekmez.

`TAVAN_ESIK` ondalık ayırıcı olarak virgülü de kabul eder (`9,5`), bozuk bir değer gelirse varsayılana döner.

### 4. Günlük tetikleyiciyi kur

**Bu adım olmadan otomatik mesaj gelmez.** Workflow'da bilerek `schedule` yok.

GitHub'ın kendi zamanlayıcısı bu repoda güvenilir çalışmadı. Cron `"50 5 * * *"` (08:50 TSİ) yerinde dururken:

| Gün | Beklenen | Gerçekleşen |
|---|---|---|
| 25.08.2026 | 05:50 UTC | **hiç çalışmadı** |
| 26.08.2026 | 05:50 UTC | 06:19 UTC (30 dk geç) |
| 27.08.2026 | 05:50 UTC | 16:49 UTC (**11 saat geç**) |

GitHub `schedule`'ı garanti etmiyor: yoğunlukta geciktiriyor, bazen tamamen düşürüyor, private repolarda önceliği daha düşük. Buna karşılık `workflow_dispatch` ile tetiklenen çalışmaların hepsi saniyesinde başladı. O yüzden zamanlama dışarıdan yapılıyor.

**a) GitHub token'ı üret.** [Fine-grained token](https://github.com/settings/personal-access-tokens/new) oluşturun:

- *Repository access* → Only select repositories → `piyasa-botu`
- *Permissions* → Repository permissions → **Actions: Read and write**
- Süreyi uzun tutun; dolduğunda tetikleyici sessizce durur

**b) [cron-job.org](https://console.cron-job.org)'da iş oluşturun** (ücretsiz):

| Alan | Değer |
|---|---|
| URL | `https://api.github.com/repos/<kullanıcı>/piyasa-botu/actions/workflows/daily.yml/dispatches` |
| Method | `POST` |
| Zaman | Her gün 08:50, timezone **Europe/Istanbul** |
| Body | `{"ref":"main"}` |

Header'lar:

```
Authorization: Bearer <token>
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
Content-Type: application/json
```

**c) Test edin.** cron-job.org'da "Test run" deyin. Başarılıysa GitHub **204 No Content** döner (gövde boş olur, bu normaldir) ve Actions sekmesinde yeni bir çalışma belirir. 401/403 gelirse token yetkisi, 404 gelirse URL'deki kullanıcı adı ya da dosya adı yanlıştır.

Saati değiştirmek isterseniz cron-job.org tarafından ayarlayın; repoda saat bilgisi tutulmuyor. 08:50 seçilmesinin sebebi BIST'in o saatte kapalı olması (açılış seansı 09:40, ilk işlem ~10:00) — tarama dünkü kapanışı görüyor ve liste tam geliyor.

Gecikirse felaket değil: rakamlar son kapanmış seansa sabitlenir (aşağıdaki *Hedef seans*), sadece aday listesi eksik kalabilir ve mesaja uyarı düşer.

## Nasıl çalışıyor

Veriler [`borsapy`](https://pypi.org/project/borsapy/) üzerinden alınıyor.

### Hedef seans

Botun tek bir çıpası var: **son kapanmış seans**. Bütün rakamlar o güne sabitleniyor.

Bu gerekli, çünkü TradingView'in günlük barı seans açılır açılmaz oluşuyor ve gün boyunca canlı güncelleniyor — `Close` sütununun son satırı "dünkü kapanış" değil, "şu anki fiyat" olabiliyor. `kapanmis()` bu yüzden devam eden günün barını atıyor; `bist_seansi()` de geriye kalan son günü hedef ilan ediyor. Kıyaslamalar konumla (`iloc[-1]`) değil tarihle yapıldığı için sonuç, botun saat kaçta çalıştığından bağımsız.

Barın ne zaman "kapandı" sayılacağı piyasaya göre değişiyor:

| | Sınır | Sonuç |
|---|---|---|
| BIST | `BIST_KAPANIS = 18:15` | Kapanış seansı 18:10'da bitiyor, 5 dk pay. 18:15'ten önce çalıştırırsanız dünkü kapanışı, sonra çalıştırırsanız bugünkünü alırsınız. |
| Metaller | `FX_KAPANIS = None` | Forex günü gece yarısı kapandığı için bugüne ait bar gün boyunca "devam ediyor" sayılır; metaller hep bir önceki günün kapanışını gösterir. |

Bu yüzden akşam 18:15 ile gece yarısı arasında çalıştırırsanız hisseler bugünü, metaller dünü gösterir — ikisi de kendi piyasasının son kapanışı olduğu için doğru, ama başlıklardaki tarihler farklı çıkar.

> Bu davranış eskiden çalışma saatine bağlıydı: 09:00'da BIST kapalı olduğu için son bar gerçekten dünkü kapanıştı. 24.08.2026'da GitHub Actions gecikip iş 10:12'de çalışınca mesaja dünkü kapanışlar yerine o andaki tavanlar girdi (TKNKA 21.08'i +%9,90 ile kapattığı hâlde listede 24.08'in anlık +%9,98'iyle göründü).

### Metaller

Dördü de tek kaynaktan, TradingView spot fiyatlarından geliyor:

| Satır | Kaynak |
|---|---|
| Ons Altın | `OANDA:XAUUSD` |
| Ons Gümüş | `OANDA:XAGUSD` |
| Gram Altın | `XAUUSD × FX:USDTRY ÷ 31,1035` |
| Gram Gümüş | `XAGUSD × FX:USDTRY ÷ 31,1035` |

1 aylık kapanış serisi çekiliyor, son kapanış ile 7 gün öncesinin (ya da ondan eski en yakın kaydın — tatile denk gelebilir) farkı yüzde olarak hesaplanıyor. 7 günlük geçmiş yoksa en eski kayda göre hesaplanıp `~` ile işaretleniyor.

Önceden sadece ons altın TradingView'den geliyordu, diğer üçü `borsapy`'nin FX geçmişinden (canlidoviz). O kaynak hafta sonu için de bar üretiyor ve bir işlem günü geriden geliyor: 24.08.2026 akşamı gram altının son kaydı hâlâ 22.08 (cumartesi), ons gümüşünki 21.08'di. Yani üç satır donuk dururken ons altın canlı fiyatla oynuyordu — üstelik başlıktaki tarih serilerin **en yenisine** göre yazıldığı için mesaj "24.08 kapanışı" diyordu.

Tek kaynağın bedeli: türetilen gram fiyatlar Kapalıçarşı'nın yaklaşık %0,2'lik yerel priminden yoksun, dolayısıyla banka kotasyonundan bir tık düşük çıkabiliyor. Yön ve yüzde değişim aynı.

### Hisseler

1. `XYLDZ`, `XUTUM` ve `XYORT` endeks bileşenlerinden pazar etiketleri çıkarılıyor (Yıldız Pazar / Ana-Alt Pazar / Yatırım Ortaklıkları), ardından tarama evreni `bp.companies()` ile BIST'in tamamına genişletiliyor. Endekslerde yer almayan hisseler **Diğer** başlığı altında listeleniyor — sadece endeks bileşenlerine bakmak, endekslere henüz girmemiş yeni şirketleri ve Yakın İzleme Pazarı'ndakileri kaçırıyordu.
2. `bp.scan(...)` ile eşiği aşanlar **tek istekte** bulunuyor (filtreleme TradingView sunucusunda yapılıyor).
3. Adaylar **hedef seansın** kapanışıyla tek tek doğrulanıyor, haftalık değişim de burada çıkarılıyor. O gün işlem görmemiş kodlar eleniyor.
4. Sonuçlar pazara göre gruplanıp günlük değişime göre sıralanıyor.

### Yükseliş serisi (🔥)

`yukselis_serisi()` her hissenin serisini sondan geriye tarayıp eşiği aşan ardışık gün sayısını çıkarıyor; 2 ve üzeri olduğunda satıra `🔥3 gün` düşüyor. Art arda tavan yapmak tek günlük sıçramadan farklı bir şey anlattığı için ayrı gösteriliyor. `1 gün` yazılmıyor — satırın kendisi zaten o günü anlatıyor.

Ek maliyeti yok: `dogrula()` haftalık değişim için zaten 1 aylık seriyi çekiyor, sayım aynı seriden yapılıyor.

Sayım **işlem günü** bazında. Hisse bir gün işlem görmezse (tedbir, sıra bekleme) o günün barı hiç oluşmuyor, dolayısıyla seri kesilmiş sayılmıyor. Eşik `TAVAN_ESIK`'e bağlı olduğu için eşiği düşürürseniz sayı da gevşer — o yüzden dipnot "tavan" değil "üst üste %9+ kapattığı gün sayısı" diyor.

Görebildiğimiz seri elimizdeki geçmişle sınırlı (`period="1mo"`, ~22 işlem günü). Yeni halka arzlarda geçmişin tamamı seri olabiliyor; o durumda da sayı olduğu gibi yazılıyor, çünkü seri gerçekten listelenme gününde başlamış oluyor.

### Tarama penceresi

İkinci adımdaki `change_percent`, TradingView'de **içinde bulunulan seansın** değişimi. Seans kapalıyken bu tam olarak istediğimiz şey. Seans açıkken ise anlık değişim demek; üçüncü adım yanlış adayları eliyor ama dün tavan yapıp bugün düşen bir hisse taramaya hiç giremediği için liste **eksik** kalabiliyor. Bot bunu saklamıyor, mesaja açık bir uyarı satırı koyuyor. Cron'un açılıştan uzak tutulmasının sebebi de bu.

### Katılım işareti (☪️)

`XKTUM` (BIST Katılım Tüm) bileşenleri her çalıştırmada taze çekiliyor, listedeki hisselere ☪️ konuyor. Elle bakım gerekmiyor: `borsapy` bu veriyi Borsa İstanbul'un kendi yayınladığı bileşen dosyasından (`borsaistanbul.com/datum/hisse_endeks_ds.csv`) alıyor, dolayısıyla kaynak resmî ve dönemsel endeks revizyonlarını kendiliğinden takip ediyor.

**Ne anlama gelmediğine dikkat.** ☪️ yokluğu "katılım finans ilkelerine uygun değil" demek değil, sadece "XKTUM'da değil" demek. XKTUM yalnızca Yıldız, Ana ve Alt Pazar'daki uygun payları kapsıyor; bu yüzden mesajdaki **Diğer** grubundaki hisseler (henüz endekse girmemiş yeni şirketler, Yakın İzleme Pazarı'ndakiler) uygun olsalar bile hiçbir zaman ☪️ alamaz. Kesin karar için şirketin KAP'taki Katılım Finans İlkeleri Bilgi Formu'na bakmak gerekir.

Liste hiç gelmezse mesaj sessizce işaretsiz gitmiyor; dipnotun yerine açık bir uyarı satırı konuyor, yoksa işaretsiz liste "bugün hiçbiri uygun değil" diye okunurdu.

### Dayanıklılık

- TradingView bağlantıyı ara sıra kapatıyor (ölçtüğümüz kadarıyla ~12 istekte 1). Her veri çağrısı hata alınca 2 saniye arayla tekrar deneniyor (`yeniden_dene`). Seans tarihini okuyan adım üç referans hisseyi sırayla deniyor, her biri üç kez: yani mesajın hisse bölümünün düşmesi için 9 ardışık hata gerekiyor. `dogrula()` yüzlerce hisseyi dolaştığı için orada deneme sayısı 2 — aksi hâlde geniş bir kesintide iş 25 dakikalık timeout'a dayanırdı.
- Tarama boş dönerse `change_percent > 0.5` ile sağlama yapılıyor — "kimse yükselmedi" ile "veri hiç gelmedi" ayırt ediliyor, ikincisinde mesaja uyarı düşülüyor.
- Aday sayısı 100'ü aşarsa (`MAX_DOGRULAMA`) tek tek doğrulama atlanıyor, sadece kodlar listeleniyor. Seans açıkken bu mümkün değil: doğrulama yapılamıyorsa elde sadece anlık veri kalır, onu "kapanış" diye yazmaktansa liste hiç yazılmıyor.
- Bir metal kaynağı çökerse o satır `⚠️ veri alınamadı` olup mesajın geri kalanı yine gidiyor. USDTRY düşerse sadece gram satırları kayboluyor, ons satırları kalıyor.
- Seans açıkken çalışılırsa mesaja "liste eksik kalmış olabilir" uyarısı ekleniyor.
- Katılım listesi alınamazsa ☪️ işaretleri düşüyor ama mesaja bunu söyleyen bir uyarı ekleniyor.
- Endeks bileşenlerinin **hiçbiri** alınamazsa iş hataya düşürülüyor; yarım evrenle yanıltıcı liste üretilmiyor.
- Telegram'ın 4096 karakter sınırına takılmamak için uzun listeler 4000 karakterde kırpılıyor.

## Dosyalar

```
bot.py                       tüm mantık (veri çekme, biçimlendirme, gönderme)
test_seans.py                seans sabitlemesinin testleri (ağ gerekmez)
requirements.txt             borsapy, pandas, requests
.github/workflows/daily.yml  günlük cron + elle tetikleme
```

Testler saati donduruyor, bu yüzden internetsiz de çalışıyor:

```bash
python test_seans.py
```

## Not

Veriler halka açık kaynaklardan alınıyor, doğruluğu ya da sürekliliği garanti edilmez. Bu bot yatırım tavsiyesi değildir.

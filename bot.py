"""
Sabah Piyasa Botu
=================
Her sabah Telegram'a gönderir:
  1. Gram/ons altın, gram/ons gümüş -> son fiyat + 1 haftalık % değişim
  2. Borsa genelinde eşiği aşarak kapatan hisseler, pazarına göre gruplanmış

Ortam değişkenleri:
  TELEGRAM_BOT_TOKEN   (zorunlu)
  TELEGRAM_CHAT_ID     (zorunlu)
  TAVAN_ESIK           (opsiyonel, varsayılan 9.0)

Kullanım:
  python bot.py          -> hesapla ve Telegram'a gönder
  python bot.py --dry    -> sadece ekrana yaz, gönderme
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import borsapy as bp

# ---------------------------------------------------------------- ayarlar

DRY_RUN = "--dry" in sys.argv

def _esik_oku(varsayilan=9.0):
    """Boş veya bozuk değer gelirse çökmek yerine varsayılana döner."""
    ham = (os.environ.get("TAVAN_ESIK") or "").strip()
    try:
        return float(ham.replace(",", "."))   # '9,5' yazılırsa da kabul et
    except ValueError:
        return varsayilan


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ESIK = _esik_oku()

if not DRY_RUN and (not TOKEN or not CHAT_ID):
    sys.exit("HATA: TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID tanımlı değil.")

TR = timezone(timedelta(hours=3))   # Türkiye UTC+3, yaz saati uygulaması yok
MAX_DOGRULAMA = 100                 # aday sayısı bunu aşarsa tek tek doğrulama atlanır

METALLER = [
    ("gram-altin", "Gram Altın", "TL"),
    ("ons-altin", "Ons Altın", "$"),
    ("gram-gumus", "Gram Gümüş", "TL"),
    ("XAG-USD", "Ons Gümüş", "$"),
]

# ---------------------------------------------------------------- yardımcı


def log(msg):
    """stderr'e yazıyoruz ki asıl mesaj çıktısıyla karışmasın."""
    print(msg, file=sys.stderr)


def tr_sayi(x, ondalik=2):
    """1234.5 -> '1.234,50'  (Python ABD formatı kullanıyor, TR'ye çeviriyoruz)"""
    s = f"{x:,.{ondalik}f}"
    return s.replace(",", "#").replace(".", ",").replace("#", ".")


def tr_yuzde(x, ondalik=2):
    """9.99 -> '+9,99'   (işaret her zaman görünür, ondalık virgülle)"""
    return f"{x:+.{ondalik}f}".replace(".", ",")


def _sutun_bul(df, adaylar):
    """Kütüphane sürümleri arasında sütun adı değişebiliyor."""
    for ad in adaylar:
        if ad in df.columns:
            return ad
    return None


# ---------------------------------------------------------------- metaller


def haftalik_degisim(seri: pd.Series):
    """(son_fiyat, yüzde_değişim, tam_hafta_mı) döndürür.

    Üçüncü değer False ise elimizde 7 günlük geçmiş yok (yeni halka arz gibi);
    hesap en eski kayda göre yapılmıştır, "1 haftalık" demek yanıltıcı olur.
    """
    seri = seri.dropna()
    if len(seri) < 2:
        return None, None, False

    son = float(seri.iloc[-1])
    hedef = seri.index[-1] - pd.Timedelta(days=7)
    # Tam 7 gün öncesi tatile denk gelebilir; ondan eski en yakın kaydı alıyoruz
    gecmis = seri.index[seri.index <= hedef]

    if len(gecmis):
        onceki, tam = float(seri.loc[gecmis[-1]]), True
    else:
        onceki, tam = float(seri.iloc[0]), False

    return son, (son - onceki) / onceki * 100, tam


def metal_serisi(sembol):
    """Metalin kapanış serisini döndürür.

    borsapy'nin günlük "ons-altin" serisi canlidoviz'in METAL_IDS listesinden
    geliyor; o liste TL cinsinden fiyat veriyor (ve altınla da tutmuyor:
    ~114.000, oysa ons altın TL karşılığı ~221.000). "$" diye göstermek
    yaklaşık 25 kat hatalı sonuç üretiyordu. Ons gümüş (XAG-USD) ise
    COMMODITY_IDS'ten geldiği için gerçekten USD; o yüzden gümüş doğruydu.

    borsapy'de USD ons altın için emtia ID'si yok. Doğru kaynak TradingView'daki
    OANDA:XAUUSD - history() bunu sadece saatlik/dakikalık isteklerde kullanıyor,
    biz günlük için doğrudan çağırıyoruz.
    """
    fx = bp.FX(sembol)
    if sembol == "ons-altin":
        df = fx._tradingview.get_history(
            symbol="XAUUSD", exchange="OANDA", period="1mo", interval="1d"
        )
    else:
        df = fx.history(period="1mo")

    seri = df["Close"].dropna()
    # TradingView tz bilgisi olan indeks döndürüyor, diğer kaynaklar tz'siz.
    # Karıştırınca tarih karşılaştırması patlıyor; TR saatine çevirip düşürüyoruz.
    if seri.index.tz is not None:
        seri.index = seri.index.tz_convert(TR).tz_localize(None)
    return seri


def metal_satirlari():
    """(veri_tarihi, satır_listesi) döndürür."""
    satirlar, tarihler = [], []
    for sembol, ad, birim in METALLER:
        try:
            seri = metal_serisi(sembol)
            son, degisim, tam = haftalik_degisim(seri)
            if son is None:
                raise ValueError("yeterli veri yok")

            tarihler.append(seri.index[-1])   # verinin gerçekten ait olduğu gün
            ok = "🟢" if degisim >= 0 else "🔴"
            isaret = "" if tam else "~"       # tam hafta yoksa yaklaşık olduğunu belirt
            satirlar.append(
                f"{ok} <b>{ad}:</b> {tr_sayi(son, 0)} {birim}  "
                f"<i>(1H: {isaret}{tr_yuzde(degisim)}%)</i>"
            )
        except Exception as e:
            # Tek kaynak çökerse mesajın tamamı gitmesin
            satirlar.append(f"⚠️ <b>{ad}:</b> veri alınamadı ({type(e).__name__})")

    return (max(tarihler) if tarihler else None), satirlar


# ---------------------------------------------------------------- hisseler


def evreni_kur():
    """{hisse_kodu: pazar_adi}. XUTUM = Yıldız+Ana+Alt, XYORT = yatırım ortaklıkları."""
    def bilesenler(endeks):
        try:
            return set(bp.Index(endeks).component_symbols)
        except Exception as e:
            log(f"  {endeks} alınamadı: {type(e).__name__}")
            return set()

    yildiz, tum, yat_ort = bilesenler("XYLDZ"), bilesenler("XUTUM"), bilesenler("XYORT")
    if not tum and not yildiz:
        raise RuntimeError("Hiçbir endeks bileşeni alınamadı.")

    evren = {}
    for kod in yildiz:
        evren[kod] = "Yıldız Pazar"
    for kod in tum - yildiz:                    # küme farkı
        evren[kod] = "Ana / Alt Pazar"
    for kod in yat_ort - tum - yildiz:
        evren[kod] = "Yatırım Ortaklıkları"

    log(f"Evren: {len(evren)} hisse (Yıldız {len(yildiz)})")
    return evren


class VeriYok(Exception):
    """Seans verisi hiç gelmemiş - 'sonuç yok' ile karıştırılmamalı."""


def adaylari_bul(evren, esik):
    """Eşiği aşanları tek istekte bulur (filtreleme TradingView sunucusunda)."""
    kodlar = list(evren.keys())
    df = bp.scan(kodlar, f"change_percent > {esik}", limit=300)

    if df is None or df.empty:
        # Sağlama: gerçekten kimse yükselmedi mi, yoksa veri mi gelmedi?
        # Normal bir seansta yüzlerce hisse %0.5'ten fazla yükselir.
        kontrol = bp.scan(kodlar, "change_percent > 0.5", limit=10)
        if kontrol is None or kontrol.empty:
            raise VeriYok("tarama tamamen boş döndü")
        return []

    kod_sutunu = _sutun_bul(df, ["symbol", "ticker", "name"])
    if kod_sutunu is None:
        raise RuntimeError(f"Sembol sütunu yok. Gelen sütunlar: {list(df.columns)}")
    return [str(k).upper() for k in df[kod_sutunu].tolist()]


def dogrula(kodlar, esik):
    """Adayları gerçek kapanış verisiyle teyit eder, haftalık değişimi de çıkarır."""
    sonuc = []
    for kod in kodlar:
        try:
            # 5d yerine 1mo: aynı istek sayısı, ama haftalık hesap için yeterli geçmiş
            kapanis = bp.Ticker(kod).history(period="1mo")["Close"].dropna()
            if len(kapanis) < 2:
                continue

            son, onceki = float(kapanis.iloc[-1]), float(kapanis.iloc[-2])
            gunluk = (son - onceki) / onceki * 100
            if gunluk < esik:
                continue

            # Metaller için yazdığımız fonksiyonu aynen kullanıyoruz
            _, haftalik, tam = haftalik_degisim(kapanis)

            sonuc.append((kod, son, gunluk, haftalik, tam, kapanis.index[-1]))
        except Exception as e:
            log(f"  {kod} doğrulanamadı: {type(e).__name__}")
    return sonuc


def hisse_satirlari(esik):
    """(tarih, satır_listesi) döndürür."""
    evren = evreni_kur()
    try:
        adaylar = adaylari_bul(evren, esik)
    except VeriYok as e:
        log(f"Veri yok: {e}")
        return None, ["⚠️ <i>Seans verisi alınamadı. Piyasa kapalı olabilir "
                      "ya da veri kaynağı henüz hazır değil.</i>"]
    log(f"Aday: {len(adaylar)}")

    if not adaylar:
        return None, ["<i>Eşiği aşan hisse yok.</i>"]

    if len(adaylar) <= MAX_DOGRULAMA:
        kayitlar, not_ = dogrula(adaylar, esik), ""
    else:
        nan = float("nan")
        kayitlar = [(k, nan, nan, nan, False, None) for k in adaylar]
        not_ = "\n<i>(Aday sayısı yüksek, kapanış doğrulaması atlandı.)</i>"

    if not kayitlar:
        return None, ["<i>Eşiği aşan hisse yok.</i>"]

    gruplar = {"Yıldız Pazar": [], "Ana / Alt Pazar": [], "Yatırım Ortaklıkları": []}
    for kod, fiyat, gunluk, haftalik, tam, _ in kayitlar:
        gruplar.setdefault(evren.get(kod, "Diğer"), []).append(
            (kod, fiyat, gunluk, haftalik, tam)
        )

    tarihler = [t for *_, t in kayitlar if t is not None]
    tarih = max(tarihler) if tarihler else None

    satirlar = []
    for pazar, liste in gruplar.items():
        if not liste:
            continue
        liste.sort(key=lambda x: -x[2] if x[2] == x[2] else 0)   # NaN güvenli
        satirlar.append(f"\n<b>— {pazar}</b> ({len(liste)})")

        for kod, fiyat, gunluk, haftalik, tam in liste:
            if gunluk != gunluk:                 # NaN ise doğrulama yapılmamış
                satirlar.append(f"• <b>{kod}</b>")
                continue

            satir = (f"• <b>{kod}:</b>  {tr_sayi(fiyat)} TL  "
                     f"{tr_yuzde(gunluk)}%")
            if haftalik is not None and haftalik == haftalik:
                isaret = "" if tam else "~"
                satir += f"  <i>(1H: {isaret}{tr_yuzde(haftalik, 1)}%)</i>"
            satirlar.append(satir)

    if not_:
        satirlar.append(not_)
    return tarih, satirlar


# ---------------------------------------------------------------- mesaj


def mesaj_olustur():
    bugun = datetime.now(TR).strftime("%d.%m.%Y")
    parcalar = [f"📊 <b>Günaydın — {bugun}</b>", ""]

    m_tarih, m_satirlar = metal_satirlari()
    m_etiket = m_tarih.strftime("%d.%m.%Y") if m_tarih is not None else "?"
    parcalar.append(f"<b>💰 Değerli Metaller</b> <i>({m_etiket} kapanışı)</i>")
    parcalar += m_satirlar
    parcalar.append("")

    try:
        tarih, satirlar = hisse_satirlari(ESIK)
        etiket = tarih.strftime("%d.%m.%Y") if tarih is not None else "son seans"
        parcalar.append(f"<b>🚀 %{ESIK:g}+ kapatanlar ({etiket})</b>")
        parcalar += satirlar
    except Exception as e:
        parcalar.append(f"⚠️ Hisse verisi alınamadı: {type(e).__name__}: {e}")

    metin = "\n".join(parcalar)
    # '~' işareti hem metal hem hisse satırlarında çıkabiliyor; kullanıldıysa
    # ne demek olduğunu mesajın sonunda bir kez açıklıyoruz.
    if "1H: ~" in metin:
        metin += "\n\n<i>~ = 7 günlük geçmiş yok; en eski kayda göre hesaplandı.</i>"
    return metin


def gonder(metin):
    # Telegram tek mesajda 4096 karakter kabul ediyor. Liste uzun bir günde
    # sınırı aşarsak API mesajın tamamını reddeder; o yüzden kendimiz kısaltıyoruz.
    if len(metin) > 4000:
        metin = metin[:3900].rsplit("\n", 1)[0] + "\n\n<i>… liste kısaltıldı.</i>"

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": metin,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        r.raise_for_status()
        log("Gönderildi.")
    except requests.HTTPError as e:
        # Telegram hatanın açıklamasını gövdede döndürüyor; teşhis için değerli
        log(f"HATA: {e} | {e.response.text}")
        raise


if __name__ == "__main__":
    metin = mesaj_olustur()
    print(metin)
    if DRY_RUN:
        log("--dry: gönderilmedi.")
    else:
        gonder(metin)

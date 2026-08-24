"""Seans sabitlemesinin testleri.

Ağ istemez: barlar elle kuruluyor, saat de sahte bir datetime ile dondurulıyor.

Çalıştırmak için:  python test_seans.py
"""

import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

sys.argv.append("--dry")          # token kontrolünü atlat
import bot                        # noqa: E402

TR = timezone(timedelta(hours=3))

# TradingView'den gelen gerçek TKNKA kapanışları (24.08.2026 barı canlı)
TKNKA = pd.Series(
    [93.9, 103.2, 113.5],
    index=pd.to_datetime(["2026-08-20", "2026-08-21", "2026-08-24"]),
)


class SahteDatetime(datetime):
    """bot.datetime.now(TR) çağrısını istediğimiz ana sabitler."""
    _an = None

    @classmethod
    def now(cls, tz=None):
        return cls._an


def saat(metin):
    """'2026-08-24 10:12' -> o anı bot modülüne dayat."""
    SahteDatetime._an = datetime.strptime(metin, "%Y-%m-%d %H:%M").replace(tzinfo=TR)
    bot.datetime = SahteDatetime


def gunluk_degisim(seri):
    """dogrula() içindeki hesabın aynısı."""
    son, onceki = float(seri.iloc[-1]), float(seri.iloc[-2])
    return (son - onceki) / onceki * 100


gecti = basarisiz = 0


def kontrol(ad, gercek, beklenen, tolerans=0.01):
    global gecti, basarisiz
    ok = abs(gercek - beklenen) <= tolerans if isinstance(beklenen, float) \
        else gercek == beklenen
    if ok:
        gecti += 1
        print(f"  OK   {ad}: {gercek}")
    else:
        basarisiz += 1
        print(f"  HATA {ad}: {gercek!r} != {beklenen!r}")


print("1) Seans açıkken (24.08 10:12 - hatanın yaşandığı an)")
saat("2026-08-24 10:12")
# Hatanın kendisi: kırpılmamış seri bugünün canlı barını kapanış sanıyor.
kontrol("kırpılmamış seri +%9,98 (bildirilen hatalı değer)",
        gunluk_degisim(TKNKA), 9.98)
kapali = bot.kapanmis(TKNKA, bot.BIST_KAPANIS)
kontrol("canlı bar atıldı", len(kapali), 2)
kontrol("hedef seans 21.08", kapali.index[-1], pd.Timestamp("2026-08-21"))
kontrol("21.08 kapanış değişimi", gunluk_degisim(kapali), 9.90)

print("\n2) Seans kapandıktan sonra (24.08 20:00)")
saat("2026-08-24 20:00")
kapali = bot.kapanmis(TKNKA, bot.BIST_KAPANIS)
kontrol("bugünün barı korundu", len(kapali), 3)
kontrol("hedef seans 24.08", kapali.index[-1], pd.Timestamp("2026-08-24"))

print("\n3) Açılıştan önce (24.08 06:20 - bugünün barı henüz yok)")
saat("2026-08-24 06:20")
kapali = bot.kapanmis(TKNKA.iloc[:-1], bot.BIST_KAPANIS)
kontrol("seri değişmedi", len(kapali), 2)
kontrol("hedef seans 21.08", kapali.index[-1], pd.Timestamp("2026-08-21"))

print("\n4) Kapanış sınırı (kapanış seansı 18:10'da biter)")
saat("2026-08-24 18:00")               # kapanış seansı sürüyor, fiyat kesin değil
kontrol("18:00 hâlâ dün", bot.kapanmis(TKNKA, bot.BIST_KAPANIS).index[-1],
        pd.Timestamp("2026-08-21"))
saat("2026-08-24 18:30")               # 18:10 bitti, bugünkü kapanış kesinleşti
kontrol("18:30 bugüne geçti", bot.kapanmis(TKNKA, bot.BIST_KAPANIS).index[-1],
        pd.Timestamp("2026-08-24"))

print("\n5) Hafta sonu: cuma kapanışında kalmalı")
# Cumartesi sabahı elimizdeki en yeni bar cumanın (21.08) barı olur
CUMA = TKNKA.iloc[:-1]
saat("2026-08-22 08:50")
kontrol("cumartesi -> cuma", bot.kapanmis(CUMA, bot.BIST_KAPANIS).index[-1],
        pd.Timestamp("2026-08-21"))
saat("2026-08-23 20:00")
kontrol("pazar akşamı -> cuma", bot.kapanmis(CUMA, bot.BIST_KAPANIS).index[-1],
        pd.Timestamp("2026-08-21"))

print("\n6) Metal/forex ekseni: bugünün barı saat kaç olursa olsun düşer")
for an in ("2026-08-24 06:00", "2026-08-24 18:30", "2026-08-24 23:30"):
    saat(an)
    kontrol(f"{an[-5:]} forex barı atıldı",
            bot.kapanmis(TKNKA, bot.FX_KAPANIS).index[-1],
            pd.Timestamp("2026-08-21"))

print("\n7) tr_fiyat: küçük fiyatlarda ondalık korunuyor")
kontrol("ons gümüş", bot.tr_fiyat(69.02), "69,02")
kontrol("gram gümüş", bot.tr_fiyat(105.95), "105,95")
kontrol("gram altın", bot.tr_fiyat(7163.35), "7.163")

print(f"\n{gecti} geçti, {basarisiz} başarısız")
sys.exit(1 if basarisiz else 0)

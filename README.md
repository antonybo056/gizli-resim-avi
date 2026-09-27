# Gizli Resim Avı

Kartları çevir, çiftleri eşleştir. Her eşleşen çift kalkınca arkadaki gizli resmin bir parçası açılır. Bütün çiftleri bulunca resmin tamamı ortaya çıkar.

**Oyna:** https://antonybo056.github.io/gizli-resim-avi/

## Özellikler

- Kendi gizli resmini yükle ya da örnek resimlerden birini seç
- Kart resimleri: Hayvanlar, Meyveler, Doğa & Uzay
- 4 zorluk seviyesi: Kolay (6 çift), Orta (8), Zor (12), Uzman (15)
- Süre, hamle ve bulunan çift sayacı, oyun sonunda isabet oranı
- Her seviye için en iyi süre ve en az hamle rekoru
- Kart çevirme, eşleşme ve resim açılma animasyonları, sesler

## Çalıştırma

İki sürümü var: tarayıcı sürümü ve Python sürümü.

### Tarayıcı sürümü

Kurulum gerekmez. `index.html` dosyasını tarayıcıda açman yeterli. Resmi sürükleyip bırakabilir ya da Ctrl+V ile yapıştırabilirsin.

### Python sürümü (pygame)

Python 3.8 veya üstü gerekir.

```bash
pip install -r requirements.txt
python eslestirme.py
```

- Gizli resmi seçmek için **Yeni oyun** düğmesine, ardından **Resim yükle**'ye bas ya da resim dosyasını pencereye sürükleyip bırak.
- Rekorlar ve ayarlar oyunun yanındaki `eslestirme_rekorlar.json` dosyasına kaydedilir.

| Tuş | İşlev |
| --- | --- |
| R | Aynı ayarlarla yeniden karıştır |
| N | Yeni oyun ekranı |
| Enter | Kurulum ekranında oyunu başlat |
| Esc | Geri dön / çık |

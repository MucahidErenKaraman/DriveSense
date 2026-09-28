```markdown
# 🚗 DriveSense — Telematics & AI-Powered Driving Analytics

DriveSense, araç telemetri verilerini (İvmeölçer, Jiroskop, GPS) işleyerek sürüş davranışlarını analiz eden, trafik kuralları ihlallerini tespit eden ve üretken yapay zekâ (Google Gemini) ile kişiselleştirilmiş sürücü koçluğu sunan yeni nesil bir telematik analiz platformudur.

## 📌 Temel Özellikler

- **Çok Boyutlu Sensör Füzyonu (Sensor Fusion):** İvme, açısal dönüş (jiroskop) ve GPS verilerini ortak zaman tünelinde (`merge_asof`) milisaniyelik hassasiyetle senkronize eder.
- **Sinyal İşleme & Gürültü Filtreleme:** Sensörlerdeki mekanik gürültüleri ve mikro titreşimleri ortadan kaldırmak için 4. derece Butterworth Alçak Geçiren Filtre (Low-Pass Filter) kullanır.
- **Gelişmiş Olay Tespiti (Peak Detection):**
  - 🛑 **Sert Fren:** Y eksenindeki ani negatif ivme zirvelerinin tespiti.
  - 🚀 **Ani Hızlanma / Kalkış:** Y eksenindeki ani pozitif ivme sıçramalarının tespiti.
  - 🔄 **Tehlikeli Sert Viraj / Manevra:** X eksenindeki merkezkaç ivmesinin tespiti.
- **💥 Akıllı Kaza & Çarpışma Doğrulaması:** Şiddetli darbe sonrası aracın hareketsiz kalıp kalmadığını denetleyen, kasis ve çukurlardan kaynaklı sahte alarmları eleyen doğrulama mekanizması.
- **TomTom Dinamik Hız Limiti Entegrasyonu:** GPS koordinatlarını TomTom Reverse Geocoding API ile eşleyerek güzergâhın yasal hız sınırlarını çeker ve idari ceza kademelerine göre dinamik puan kesintisi uygular.
- **İnteraktif Telemetri Haritası:** Sürüş rotasını ve tespit edilen tüm ihlalleri Folium üzerinde katman bazlı filtreleme (LayerControl) imkanıyla sunar.
- **Robotik Sürüş Koçu (Gemini AI):** Sürüş istatistiklerini Gemini modeline aktararak sürücüye özel profesyonel geri bildirim raporu üretir.
- **Yerel Veritabanı & Tekrar Oynatma:** SQLite altyapısıyla geçmiş sürüşleri isim bazlı saklar ve oturumları yeniden analiz etme olanağı tanır.

## 🛠️ Mimari ve Teknolojiler

- **Arayüz:** Streamlit
- **Veri & Sinyal İşleme:** Pandas, NumPy, SciPy (`signal.butter`, `signal.filtfilt`, `signal.find_peaks`)
- **Görselleştirme:** Plotly Graph Objects, Folium, Streamlit-Folium
- **Harita & Limit Servisi:** TomTom Reverse Geocode API
- **Yapay Zekâ Motoru:** Google Generative AI (gemini-1.5-flash)
- **Veritabanı:** SQLite3

## 🚀 Kurulum ve Çalıştırma

### 1. Depoyu Klonlayın
```bash
git clone [https://github.com/KULLANICI_ADINIZ/DriveSense.git](https://github.com/KULLANICI_ADINIZ/DriveSense.git)
cd DriveSense

```

### 2. Sanal Ortam Oluşturun ve Bağımlılıkları Yükleyin

```bash
# Sanal ortam oluşturma
python -m venv .venv

# Ortamı aktif etme (Windows)
.venv\Scripts\activate

# Ortamı aktif etme (macOS / Linux)
source .venv/bin/activate

# Gerekli paketlerin yüklenmesi
pip install -r requirements.txt

```

### 3. API Anahtarlarının Yapılandırılması

Uygulama, API anahtarlarını güvenli tutmak için Streamlit Secrets mimarisini kullanır.

Proje ana dizininde `.streamlit` adında bir klasör oluşturun (veya mevcut olanı kullanın). İçinde `secrets.toml` dosyası oluşturun ve anahtarlarınızı tanımlayın:

```toml
# .streamlit/secrets.toml
GEMINI_API_KEY = "BURAYA_GEMINI_API_ANAHTARINIZI_YAZIN"
TOMTOM_API_KEY = "BURAYA_TOMTOM_API_ANAHTARINIZI_YAZIN"

```

*Repoda yer alan `.streamlit/secrets.example.toml` dosyasını referans şablon olarak kullanabilirsiniz.*

### 4. Uygulamayı Başlatın

```bash
streamlit run app.py

```

## 📂 Veri Formatı Gereksinimleri

Sisteme yüklenecek CSV dosyalarında bulunması gereken asgari sütunlar:

| Sensör Dosyası | Zorunlu Sütunlar | Açıklama |
| --- | --- | --- |
| `Accelerometer.csv` | `seconds_elapsed, x, y, z` | Aracın eksenel ivme değerleri (m/s²) |
| `Gyroscope.csv` | `seconds_elapsed, x, y, z` | Açısal dönüş hızları (rad/s) |
| `Location.csv` | `seconds_elapsed, latitude, longitude, speed` | GPS koordinatları ve anlık hız verisi |

## 👥 Geliştirici Ekibi

Bu proje, telematik veri analizi ve sürüş güvenliği odağında geliştirilmiştir:

* **Özberk Harman** — [GitHub](https://github.com/ozberkko) • [LinkedIn](www.linkedin.com/in/özberk-harman)
* **Burak Sıkı** — [GitHub](https://github.com/buraksk511) • [LinkedIn](https://www.linkedin.com/in/burak-siki/)
* **Mücahid Eren Karaman** — [GitHub](https://www.google.com/search?q=URL_BURAYA&utm_source=gemini) • [LinkedIn](https://www.linkedin.com/in/m%C3%BCcahid-eren-karaman-20b876332/)

## 📄 Yasal Uyarı ve Telif Hakkı (Copyright)

Copyright (c) 2026 Özberk Harman, Burak Sıkı, Mücahid Eren Karaman. All rights reserved.

Bu projenin kaynak kodları yalnızca portfolyo sergileme, akademik inceleme ve eğitim amacıyla GitHub üzerinde herkese açık (public) olarak paylaşılmıştır. Kodların izinsiz kopyalanması, değiştirilmesi, başka projelere entegre edilmesi veya herhangi bir ticari amaçla kullanılması kesinlikle yasaktır. Her türlü kullanım veya iş birliği için geliştirici ekiple iletişime geçilerek yazılı izin alınması gerekmektedir.

```

```

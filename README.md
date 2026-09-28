
# 🚗 DriveSense — Smart Telematics & Driving Analytics

*(🇹🇷 Türkçe versiyon için aşağı kaydırın / Scroll down for the Turkish version)*

DriveSense is a next-generation telematics analytics platform that processes vehicle telemetry data (Accelerometer, Gyroscope, GPS) to analyze driving behavior, detect traffic violations, and provide personalized driver coaching using generative AI.

## 📌 Key Features

- **Multi-Dimensional Sensor Fusion:** Synchronizes acceleration, angular rotation (gyroscope), and GPS data on a common timeline (`merge_asof`) with millisecond precision.
- **Signal Processing & Noise Filtering:** Utilizes a 4th-order Butterworth Low-Pass Filter to eliminate mechanical noise and micro-vibrations from the sensors.
- **Advanced Peak Detection:**
  - 🛑 **Hard Braking:** Detection of sudden negative acceleration peaks on the Y-axis.
  - 🚀 **Sudden Acceleration / Launch:** Detection of sudden positive acceleration spikes on the Y-axis.
  - 🔄 **Dangerous Hard Cornering / Maneuvering:** Detection of centrifugal acceleration on the X-axis.
- **💥 Smart Accident & Collision Verification:** A verification mechanism that checks if the vehicle remains stationary after a severe impact, effectively eliminating false alarms caused by speed bumps and potholes.
- **TomTom Dynamic Speed Limit Integration:** Matches GPS coordinates using the TomTom Reverse Geocoding API to fetch the legal speed limits of the route in real-time, applying dynamic point deductions based on traffic penalty tiers.
- **Interactive Telemetry Map:** Displays the driving route and all detected violations on a Folium map with layer-based filtering capabilities (LayerControl).
- **Robotic Driving Coach (Gemini AI):** Feeds driving statistics into the Gemini AI model to generate a personalized and professional safety feedback report for the driver.
- **Local Database & Session Replay:** Stores past driving sessions by name using SQLite infrastructure, allowing users to reload and re-analyze previous trips.

## 🛠️ Architecture and Technologies

- **UI Framework:** Streamlit
- **Data & Signal Processing:** Pandas, NumPy, SciPy (`signal.butter`, `signal.filtfilt`, `signal.find_peaks`)
- **Data Visualization:** Plotly Graph Objects, Folium, Streamlit-Folium
- **Mapping & Speed Limit Service:** TomTom Reverse Geocode API
- **AI Engine:** Google Generative AI (gemini-1.5-flash)
- **Database:** SQLite3

## 🚀 Installation and Usage

### 1. Clone the Repository
```bash
git clone [https://github.com/buraksk511/DriveSense.git](https://github.com/buraksk511/DriveSense.git)
cd DriveSense

```

### 2. Create a Virtual Environment and Install Dependencies

```bash
# Create a virtual environment
python -m venv .venv

# Activate the environment (Windows)
.venv\Scripts\activate

# Activate the environment (macOS / Linux)
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt

```

### 3. API Key Configuration

The application uses the Streamlit Secrets architecture to keep API keys secure.

Create a `.streamlit` folder in the main directory of the project (or use the existing one). Inside it, create a `secrets.toml` file and define your keys:

```toml
# .streamlit/secrets.toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
TOMTOM_API_KEY = "YOUR_TOMTOM_API_KEY_HERE"

```

*You can use the `.streamlit/secrets.example.toml` file included in the repository as a reference template.*

### 4. Run the Application

```bash
streamlit run app.py

```

## 📂 Data Format Requirements

The CSV files to be uploaded to the system must contain the following minimum columns:

| Sensor File | Required Columns | Description |
| --- | --- | --- |
| `Accelerometer.csv` | `seconds_elapsed, x, y, z` | Axial acceleration values of the vehicle (m/s²) |
| `Gyroscope.csv` | `seconds_elapsed, x, y, z` | Angular rotation speeds (rad/s) |
| `Location.csv` | `seconds_elapsed, latitude, longitude, speed` | GPS coordinates and real-time speed data |

## 👥 Developer Team

This project was developed with a focus on telematics data analysis and driving safety:

* **Burak Sıkı** — [GitHub](https://github.com/buraksk511) • [LinkedIn](https://www.linkedin.com/in/burak-siki/)
* *Algorithm Design and API Integration:* Core signal processing architecture (SciPy/Butterworth filtering), TomTom API connections, and foundational rule violation detection algorithms.


* **Özberk Harman** — [GitHub](https://github.com/ozberkko) • [LinkedIn](https://www.linkedin.com/in/%C3%B6zberk-harman/)
* *Data Engineering, Algorithm Optimization, and UI:* ESP32 telemetry data preprocessing/type conversion pipeline, accident verification and dynamic scoring engine, Streamlit SaaS dashboard (interactive Folium/Plotly), SQLite data layer, and Gemini AI integration.


* **Mücahid Eren Karaman** — [GitHub](https://github.com/MucahidErenKaraman) • [LinkedIn](https://www.linkedin.com/in/m%C3%BCcahid-eren-karaman-20b876332/)
* *Sensor Hardware and IoT Integration:* ESP32 microcontroller, MPU6050 accelerometer/gyroscope, and GPS module circuit design alongside the data collection infrastructure.



## 📄 Legal Disclaimer and Copyright

Copyright (c) 2026 Özberk Harman, Burak Sıkı, Mücahid Eren Karaman. All rights reserved.

The source code of this project is published publicly on GitHub solely for portfolio demonstration, academic review, and educational purposes. Unauthorized copying, modification, integration into other projects, or use for any commercial purpose is strictly prohibited. Written permission must be obtained by contacting the development team for any kind of use or collaboration.

---

---

# 🚗 DriveSense — Smart Telematics & Driving Analytics (Türkçe Versiyon)

DriveSense, araç telemetri verilerini (İvmeölçer, Jiroskop, GPS) işleyerek sürüş davranışlarını analiz eden, trafik kuralları ihlallerini tespit eden ve üretken yapay zekâ (Google Gemini) ile kişiselleştirilmiş sürücü koçluğu sunan yeni nesil bir telematik analiz platformudur.

## 📌 Temel Özellikler

* **Çok Boyutlu Sensör Füzyonu (Sensor Fusion):** İvme, açısal dönüş (jiroskop) ve GPS verilerini ortak zaman tünelinde (`merge_asof`) milisaniyelik hassasiyetle senkronize eder.
* **Sinyal İşleme & Gürültü Filtreleme:** Sensörlerdeki mekanik gürültüleri ve mikro titreşimleri ortadan kaldırmak için 4. derece Butterworth Alçak Geçiren Filtre (Low-Pass Filter) kullanır.
* **Gelişmiş Olay Tespiti (Peak Detection):**
* 🛑 **Sert Fren:** Y eksenindeki ani negatif ivme zirvelerinin tespiti.
* 🚀 **Ani Hızlanma / Kalkış:** Y eksenindeki ani pozitif ivme sıçramalarının tespiti.
* 🔄 **Tehlikeli Sert Viraj / Manevra:** X eksenindeki merkezkaç ivmesinin tespiti.


* **💥 Akıllı Kaza & Çarpışma Doğrulaması:** Şiddetli darbe sonrası aracın hareketsiz kalıp kalmadığını denetleyen, kasis ve çukurlardan kaynaklı sahte alarmları eleyen doğrulama mekanizması.
* **TomTom Dinamik Hız Limiti Entegrasyonu:** GPS koordinatlarını TomTom Reverse Geocoding API ile eşleyerek güzergâhın yasal hız sınırlarını çeker ve idari ceza kademelerine göre dinamik puan kesintisi uygular.
* **İnteraktif Telemetri Haritası:** Sürüş rotasını ve tespit edilen tüm ihlalleri Folium üzerinde katman bazlı filtreleme (LayerControl) imkanıyla sunar.
* **Robotik Sürüş Koçu (Gemini AI):** Sürüş istatistiklerini Gemini modeline aktararak sürücüye özel profesyonel geri bildirim raporu üretir.
* **Yerel Veritabanı & Tekrar Oynatma:** SQLite altyapısıyla geçmiş sürüşleri isim bazlı saklar ve oturumları yeniden analiz etme olanağı tanır.

## 🛠️ Mimari ve Teknolojiler

* **Arayüz:** Streamlit
* **Veri & Sinyal İşleme:** Pandas, NumPy, SciPy (`signal.butter`, `signal.filtfilt`, `signal.find_peaks`)
* **Görselleştirme:** Plotly Graph Objects, Folium, Streamlit-Folium
* **Harita & Limit Servisi:** TomTom Reverse Geocode API
* **Yapay Zekâ Motoru:** Google Generative AI (gemini-1.5-flash)
* **Veritabanı:** SQLite3

## 🚀 Kurulum ve Çalıştırma

### 1. Depoyu Klonlayın

```bash
git clone [https://github.com/buraksk511/DriveSense.git](https://github.com/buraksk511/DriveSense.git)
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

* **Burak Sıkı** — [GitHub](https://github.com/buraksk511) • [LinkedIn](https://www.linkedin.com/in/burak-siki/)
* *Algoritma Tasarımı ve API Entegrasyonu:* Temel sinyal işleme mimarisi (SciPy/Butterworth filtreleme), TomTom API bağlantıları ve temel kural ihlali tespit algoritmaları.


* **Özberk Harman** — [GitHub](https://github.com/ozberkko) • [LinkedIn](https://www.linkedin.com/in/%C3%B6zberk-harman/)
* *Veri Mühendisliği, Algoritma Optimizasyonu ve Arayüz:* ESP32 telemetri verisi ön işleme/tip dönüşüm boru hattı, kaza doğrulama ve dinamik puanlama motoru, Streamlit SaaS paneli (interaktif Folium/Plotly), SQLite veri katmanı ve Gemini AI entegrasyonu.


* **Mücahid Eren Karaman** — [GitHub](https://github.com/MucahidErenKaraman) • [LinkedIn](https://www.linkedin.com/in/m%C3%BCcahid-eren-karaman-20b876332/)
* *Sensör Donanımı ve IoT Entegrasyonu:* ESP32 mikrodenetleyici, MPU6050 ivmeölçer/jiroskop ve GPS modülü devre tasarımı ile veri toplama altyapısı.



## 📄 Yasal Uyarı ve Telif Hakkı (Copyright)

Copyright (c) 2026 Özberk Harman, Burak Sıkı, Mücahid Eren Karaman. All rights reserved.

Bu projenin kaynak kodları yalnızca portfolyo sergileme, akademik inceleme ve eğitim amacıyla GitHub üzerinde herkese açık (public) olarak paylaşılmıştır. Kodların izinsiz kopyalanması, değiştirilmesi, başka projelere entegre edilmesi veya herhangi bir ticari amaçla kullanılması kesinlikle yasaktır. Her türlü kullanım veya iş birliği için geliştirici ekiple iletişime geçilerek yazılı izin alınması gerekmektedir.

```

```

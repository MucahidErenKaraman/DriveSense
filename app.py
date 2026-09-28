import re
import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import butter, filtfilt, find_peaks
import sqlite3
from datetime import datetime
import io
import time
import requests
import google.generativeai as genai

# set_page_config, Streamlit'te ilk çağrılan komut olmalı
st.set_page_config(page_title="DriveSense", page_icon="🚗", layout="wide")

# ==========================================
# API ANAHTARLARI (.streamlit/secrets.toml içinden okunur)
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    TOMTOM_API_KEY = st.secrets["TOMTOM_API_KEY"]
except Exception:
    st.error("API anahtarları bulunamadı. `.streamlit/secrets.example.toml` dosyasını "
             "`.streamlit/secrets.toml` olarak kopyalayıp kendi anahtarlarınızı ekleyin.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = 'gemini-3.8-flash'

# --- 1. SQL VERİTABANI KURULUMU ---
def init_db():
    conn = sqlite3.connect('surus_verileri.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS gecmis_surusler_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            accel_csv TEXT,
            gyro_csv TEXT,
            loc_csv TEXT,
            surus_adi TEXT DEFAULT 'İsimsiz Sürüş'
        )
    ''')
    try:
        c.execute("ALTER TABLE gecmis_surusler_v2 ADD COLUMN surus_adi TEXT DEFAULT 'İsimsiz Sürüş'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

# --- 2. DIŞ API VE YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=3600, show_spinner=False)
def hiz_limiti_al(lat, lon):
    url = f"https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json"
    params = {"key": TOMTOM_API_KEY, "returnSpeedLimit": "true"}
    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            addr = r.json().get('addresses', [{}])[0].get('address', {})
            sl = addr.get('speedLimit')
            if sl:
                m = re.match(r'([\d.]+)', sl)
                if m:
                    return round(float(m.group(1)))
    except Exception:
        pass
    # Limit alınamazsa tahmin yürütmeyiz; NaN olan noktalar ihlal hesabına katılmaz
    return np.nan

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371000
    return c * r

def ihlal_kademesi(fark, limit):
    """Hız aşımını Hafif / Orta / Ağır olarak sınıflandırır."""
    if limit <= 50:
        if fark <= 20: return "Hafif"
        elif fark <= 45: return "Orta"
        return "Ağır"
    else:
        if fark <= 25: return "Hafif"
        elif fark <= 50: return "Orta"
        return "Ağır"

# YENİ DETAYLI CEZA SİSTEMİ
def hiz_ceza_puani(hiz, limit):
    if pd.isna(limit) or limit <= 0: return 0.0
    fark = hiz - limit
    if fark <= 0: return 0.0

    if limit <= 50:
        if fark <= 5: return 0.0
        elif fark <= 10: return 2.0
        elif fark <= 15: return 3.0
        elif fark <= 20: return 4.0
        elif fark <= 25: return 5.0
        elif fark <= 35: return 6.0
        elif fark <= 45: return 7.0
        elif fark <= 55: return 8.0
        elif fark <= 65: return 9.0
        else: return 10.0
    else:
        if fark <= 10: return 0.0
        elif fark <= 15: return 2.0
        elif fark <= 20: return 3.0
        elif fark <= 25: return 4.0
        elif fark <= 30: return 5.0
        elif fark <= 40: return 6.0
        elif fark <= 50: return 7.0
        elif fark <= 60: return 8.0
        elif fark <= 70: return 9.0
        else: return 10.0

# --- 3. SENSÖR VERİ İŞLEME VE DİNAMİK CEZA MOTORU ---
@st.cache_data
def verileri_isle(df_a_raw, df_g_raw, df_l_raw):
    df_a = df_a_raw.copy()
    df_g = df_g_raw.copy()
    df_l = df_l_raw.copy()

    def temizle_ve_sayi_yap(df, sutunlar):
        for col in sutunlar:
            if col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    df_a = temizle_ve_sayi_yap(df_a, ['seconds_elapsed', 'x', 'y', 'z'])
    df_g = temizle_ve_sayi_yap(df_g, ['seconds_elapsed', 'x', 'y', 'z'])
    df_l = temizle_ve_sayi_yap(df_l, ['seconds_elapsed', 'latitude', 'longitude', 'speed'])

    df_a.dropna(subset=['seconds_elapsed', 'y'], inplace=True)
    df_g.dropna(subset=['seconds_elapsed', 'z'], inplace=True)
    df_l.dropna(subset=['seconds_elapsed'], inplace=True)

    def alca_geciren_filtre(veri, kesim, hiz, derece=4):
        if len(veri) < 15: return veri
        nyq = 0.5 * hiz
        b, a = butter(derece, kesim / nyq, btype='low', analog=False)
        return filtfilt(b, a, veri)

    df_accel = df_a.sort_values('seconds_elapsed').copy()
    df_gyro = df_g.sort_values('seconds_elapsed').copy()
    df_loc = df_l.sort_values('seconds_elapsed').copy()

    df_accel['y'] = df_accel['y'].ffill().fillna(0)
    df_accel['x'] = df_accel['x'].ffill().fillna(0)
    df_gyro['z'] = df_gyro['z'].ffill().fillna(0)

    df_accel['temiz_y'] = alca_geciren_filtre(df_accel['y'], 2.0, 50)
    df_accel['temiz_x'] = alca_geciren_filtre(df_accel['x'], 2.0, 50)
    df_gyro['temiz_z'] = alca_geciren_filtre(df_gyro['z'], 2.0, 50)

    df_loc.dropna(subset=['latitude', 'longitude'], inplace=True)
    df_loc['prev_lat'] = df_loc['latitude'].shift(1)
    df_loc['prev_lon'] = df_loc['longitude'].shift(1)
    df_loc['prev_time'] = df_loc['seconds_elapsed'].shift(1)
    df_loc['mesafe_m'] = haversine(df_loc['prev_lat'], df_loc['prev_lon'], df_loc['latitude'], df_loc['longitude'])
    df_loc['zaman_farki'] = df_loc['seconds_elapsed'] - df_loc['prev_time']
    df_loc['zaman_farki'] = np.where(df_loc['zaman_farki'] < 0.5, np.nan, df_loc['zaman_farki'])

    if 'speed' in df_loc.columns and df_loc['speed'].notna().any():
        df_loc['hiz_kmh'] = df_loc['speed'] * 3.6
        df_loc['hiz_kmh'] = np.where(df_loc['hiz_kmh'] < 0, 0, df_loc['hiz_kmh'])
        df_loc['hiz_kmh'] = df_loc['hiz_kmh'].fillna(0)
    else:
        df_loc['hiz_kmh'] = (df_loc['mesafe_m'] / df_loc['zaman_farki']) * 3.6
        df_loc['hiz_kmh'] = np.where(df_loc['hiz_kmh'] > 200.0, np.nan, df_loc['hiz_kmh'])
        df_loc['hiz_kmh'] = df_loc['hiz_kmh'].ffill().fillna(0).rolling(window=3, min_periods=1).mean()

    return df_accel, df_gyro, df_loc

def yapay_zeka_yorumu_olustur(puan, fren, kalkis, viraj, hiz, kaza):
    prompt = f"""
    Sen otomotiv sektörü için çalışan uzman bir 'Yapay Zeka Sürüş Koçu'sun.
    Aşağıda bir sürücünün araç sensörlerinden (İvme, Jiroskop, GPS) elde edilen sürüş istatistikleri yer alıyor.
    Bu verileri analiz ederek sürücüye kısa, profesyonel ve doğrudan hitap eden (sen/siz) bir sürüş değerlendirme raporu yaz. (Maksimum 3-4 cümle).

    Sürüş İstatistikleri:
    - Genel Puan: {puan} / 100
    - Sert Fren Sayısı: {fren}
    - Ani Kalkış/Hızlanma Sayısı: {kalkis}
    - Tehlikeli Sert Viraj / Manevra Sayısı: {viraj}
    - Hız İhlali Sayısı: {hiz}
    - Kaza / Şiddetli Darbe: {kaza}
    """
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            yield chunk.text
            time.sleep(0.02)
    except Exception as e:
        yield f"Sistemsel bir hata oluştu. Hata detayı: {str(e)}"

# --- 4. ANA ANALİZ VE ÇİZİM FONKSİYONU ---
def analizi_yap_ve_ciz(df_a, df_g, df_l, surus_id_icin_key=""):
    df_accel, df_gyro, df_loc = verileri_isle(df_a, df_g, df_l)

    FREN_ESIGI = 2.94
    HIZ_ESIGI = 2.94
    VIRAJ_TESPIT = 2.0
    VIRAJ_CEZA = 3.5
    KAZA_IVME_ESIGI = 6.0
    KAZA_JIRO_ESIGI = 1.5

    fren_ind, fren_pro = find_peaks(-df_accel['temiz_y'], height=FREN_ESIGI, distance=100)
    hiz_ind, hiz_pro = find_peaks(df_accel['temiz_y'], height=HIZ_ESIGI, distance=100)

    fren_baslangiclari = df_accel.iloc[fren_ind].copy()
    hiz_baslangiclari = df_accel.iloc[hiz_ind].copy()
    fren_baslangiclari['siddet'] = fren_pro['peak_heights']
    hiz_baslangiclari['siddet'] = hiz_pro['peak_heights']

    sag_viraj_ind, sag_pro = find_peaks(df_accel['temiz_x'], height=VIRAJ_TESPIT, distance=100)
    sol_viraj_ind, sol_pro = find_peaks(-df_accel['temiz_x'], height=VIRAJ_TESPIT, distance=100)

    sag_df = df_accel.iloc[sag_viraj_ind].copy(); sag_df['siddet'] = sag_pro['peak_heights']
    sol_df = df_accel.iloc[sol_viraj_ind].copy(); sol_df['siddet'] = sol_pro['peak_heights']
    tum_virajlar = pd.concat([sag_df, sol_df]).sort_values('seconds_elapsed')
    sert_virajlar = tum_virajlar[tum_virajlar['siddet'] >= VIRAJ_CEZA]

    st.info("📡 GPS verileri TomTom Harita Servisleri ile eşleştirilip gerçek hız limitleri çekiliyor...")
    DOWNSAMPLE = 60
    loc_hiz = df_loc.copy()
    loc_sampled = loc_hiz.iloc[::DOWNSAMPLE].copy()
    loc_sampled['hiz_limiti'] = loc_sampled.apply(lambda row: hiz_limiti_al(row['latitude'], row['longitude']), axis=1)

    loc_hiz = pd.merge_asof(loc_hiz.sort_values('seconds_elapsed'),
                            loc_sampled[['seconds_elapsed', 'hiz_limiti']].sort_values('seconds_elapsed'),
                            on='seconds_elapsed', direction='nearest')

    loc_hiz['fark'] = loc_hiz.apply(lambda r: r['hiz_kmh'] - r['hiz_limiti'] if pd.notna(r['hiz_limiti']) and r['hiz_limiti'] > 0 else -1, axis=1)
    loc_hiz['ihlal'] = loc_hiz.apply(lambda r: (r['hiz_limiti'] <= 50 and r['fark'] > 5) or (r['hiz_limiti'] > 50 and r['fark'] > 10), axis=1)

    hiz_olaylari = []
    i, n = 0, len(loc_hiz)
    MIN_SURDURME_SN = 4
    while i < n:
        if loc_hiz['ihlal'].iloc[i]:
            j = i
            while j < n and loc_hiz['ihlal'].iloc[j]: j += 1
            sure = loc_hiz['seconds_elapsed'].iloc[j-1] - loc_hiz['seconds_elapsed'].iloc[i]
            if sure >= MIN_SURDURME_SN:
                idx_peak = loc_hiz['fark'].iloc[i:j].idxmax()
                hiz_olaylari.append(loc_hiz.loc[idx_peak])
            i = j
        else:
            i += 1

    df_hiz_ihlalleri = pd.DataFrame(hiz_olaylari)

    # --- KAZA VE ÇARPIŞMA DOĞRULAMA MOTORU ---
    df_sensor_fusion = pd.merge_asof(df_accel[['seconds_elapsed', 'y']], df_gyro[['seconds_elapsed', 'z']], on='seconds_elapsed', direction='nearest')

    df_sensor_fusion['is_kaza_sensor'] = (abs(df_sensor_fusion['y']) > KAZA_IVME_ESIGI) & (abs(df_sensor_fusion['z']) > KAZA_JIRO_ESIGI)
    df_kaza_adaylari = df_sensor_fusion[df_sensor_fusion['is_kaza_sensor']].copy()
    kaza_aday_baslangiclari = df_kaza_adaylari[df_kaza_adaylari['seconds_elapsed'].diff().fillna(999) > 5] if not df_kaza_adaylari.empty else pd.DataFrame(columns=df_sensor_fusion.columns)

    kesin_kazalar = []
    for _, aday in kaza_aday_baslangiclari.iterrows():
        kaza_ani = aday['seconds_elapsed']
        sonrasi_hizlar = loc_hiz[(loc_hiz['seconds_elapsed'] > kaza_ani) & (loc_hiz['seconds_elapsed'] <= kaza_ani + 10)]
        son_5_saniye = loc_hiz[(loc_hiz['seconds_elapsed'] > kaza_ani + 5) & (loc_hiz['seconds_elapsed'] <= kaza_ani + 10)]

        if not sonrasi_hizlar.empty:
            if sonrasi_hizlar['hiz_kmh'].min() <= 1.0:
                if not son_5_saniye.empty and son_5_saniye['hiz_kmh'].max() > 5.0:
                    pass
                else:
                    kesin_kazalar.append(aday)

    kaza_baslangiclari = pd.DataFrame(kesin_kazalar) if kesin_kazalar else pd.DataFrame(columns=df_sensor_fusion.columns)

    # --- PUANLAMA ---
    fren_ceza = sum(min(5.0 * max(0, s - FREN_ESIGI), 10.0) for s in fren_baslangiclari['siddet'])
    hizlanma_ceza = sum(min(4.0 * max(0, s - HIZ_ESIGI), 8.0) for s in hiz_baslangiclari['siddet'])
    viraj_ceza = sum(min(3.0 * max(0, s - VIRAJ_CEZA), 6.0) for s in sert_virajlar['siddet']) if not sert_virajlar.empty else 0

    hiz_ihlali_ceza = 0
    if not df_hiz_ihlalleri.empty:
        hiz_ihlali_ceza = sum(hiz_ceza_puani(satir['hiz_kmh'], satir['hiz_limiti']) for _, satir in df_hiz_ihlalleri.iterrows())

    ham_toplam_ceza = fren_ceza + hizlanma_ceza + viraj_ceza + hiz_ihlali_ceza
    toplam_ceza = min(ham_toplam_ceza, 100.0)
    toplam_puan = 100.0 - toplam_ceza

    if len(kaza_baslangiclari) > 0: toplam_puan = 0
    elif toplam_puan < 0: toplam_puan = 0

    if len(kaza_baslangiclari) > 0:
        st.error(f"🚨 DİKKAT: Sürüş sırasında {len(kaza_baslangiclari)} adet AĞIR ÇARPIŞMA tespit edildi! Puan sıfırlandı.")

    # ==========================================
    # SAAS GÖRÜNÜMÜ: SÜRÜŞ ÖZETİ
    # ==========================================
    toplam_sure_sn = df_loc['seconds_elapsed'].max() - df_loc['seconds_elapsed'].min()
    dakika = int(toplam_sure_sn // 60)
    saniye = int(toplam_sure_sn % 60)
    toplam_mesafe_km = df_loc['mesafe_m'].sum() / 1000.0
    ortalama_hiz = df_loc['hiz_kmh'].mean()
    maksimum_hiz = df_loc['hiz_kmh'].max()

    st.markdown("### 📊 Sürüş Genel Özeti")
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("⏱️ Sürüş Süresi", f"{dakika}:{saniye:02d}")
    o2.metric("🛣️ Toplam Mesafe", f"{toplam_mesafe_km:.2f} km")
    o3.metric("📈 Ortalama Hız", f"{ortalama_hiz:.1f} km/h")
    o4.metric("🚀 Maksimum Hız", f"{maksimum_hiz:.1f} km/h")

    st.divider()

    st.markdown("### 🚨 Ceza ve İhlal Raporu")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🏆 Sürüş Puanı", f"{int(toplam_puan)} / 100", f"-{toplam_ceza:.1f}")
    m2.metric("🛑 Sert Fren", len(fren_baslangiclari))
    m3.metric("🚀 Ani Hızlanma", len(hiz_baslangiclari))
    m4.metric("🔄 Sert Viraj / Manevra", len(sert_virajlar))
    m5.metric("⚡ Hız İhlali", len(df_hiz_ihlalleri))

    with st.expander("🔻 Puan Kesinti Detaylarını Gör (Güncel Kanun Kademelerine Göre)", expanded=False):
        if ham_toplam_ceza <= 0:
            st.success("Tebrikler! Sürüşünüzde hiçbir kural ihlali bulunmuyor. Kusursuz bir sürüş!")
        else:
            detaylar = f"**Hesaplanan Brüt Ceza: -{ham_toplam_ceza:.1f} Puan**\n\n"
            if ham_toplam_ceza > 100: detaylar += "*(Not: Sistem, toplam kesintiyi maksimum 100 puan ile sınırlandırmıştır.)*\n\n"
            detaylar += f"**Yansıtılan Net Ceza Puanı: -{toplam_ceza:.1f}**\n"

            if fren_ceza > 0: detaylar += f"* 🛑 Sert Frenlerden Kesilen: **-{fren_ceza:.1f}** Puan\n"
            if hizlanma_ceza > 0: detaylar += f"* 🚀 Ani Hızlanmalardan Kesilen: **-{hizlanma_ceza:.1f}** Puan\n"
            if viraj_ceza > 0: detaylar += f"* 🔄 Sert Viraj / Manevradan Kesilen: **-{viraj_ceza:.1f}** Puan\n"
            if hiz_ihlali_ceza > 0:
                detaylar += f"* ⚡ Hız İhlallerinden Kesilen: **-{hiz_ihlali_ceza:.1f}** Puan\n"
                hafif = 0; orta = 0; agir = 0
                for _, satir in df_hiz_ihlalleri.iterrows():
                    kademe = ihlal_kademesi(satir['fark'], satir['hiz_limiti'])
                    if kademe == "Hafif": hafif += 1
                    elif kademe == "Orta": orta += 1
                    else: agir += 1
                if hafif > 0: detaylar += f"  > {hafif} Adet Hafif İhlal (İdari Para Cezası Kademesi)\n"
                if orta > 0: detaylar += f"  > {orta} Adet Orta İhlal (İdari Para Cezası Kademesi)\n"
                if agir > 0: detaylar += f"  > {agir} Adet Ağır İhlal (Ehliyete El Koyma Kademesi)\n"

            st.markdown(detaylar)

    with st.expander("🤖 AI Sürüş Asistanı", expanded=True):
        st.markdown("Sürüş verilerinizi analiz ederek kişiselleştirilmiş güvenlik önerileri oluşturun.")
        if st.button("🧠 Sürüş Raporumu Üret", use_container_width=True, key=f"ai_btn_{surus_id_icin_key}"):
            st.write_stream(yapay_zeka_yorumu_olustur(toplam_puan, len(fren_baslangiclari), len(hiz_baslangiclari), len(sert_virajlar), len(df_hiz_ihlalleri), len(kaza_baslangiclari)))

    st.write("")

    # ==========================================
    # SAAS GÖRÜNÜMÜ: SEKMELER VE İNTERAKTİF HARİTA
    # ==========================================
    tab_harita, tab_grafik = st.tabs(["🗺️ Olay Haritası", "📈 Sensör Dinamikleri"])

    with tab_harita:
        gecerli_konumlar = df_loc[(df_loc['latitude'] != 0) & (df_loc['latitude'].notna())]
        if not gecerli_konumlar.empty:

            harita = folium.Map(
                location=[gecerli_konumlar['latitude'].iloc[0], gecerli_konumlar['longitude'].iloc[0]],
                zoom_start=14,
                tiles='http://mt0.google.com/vt/lyrs=m&hl=tr&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Harita'
            )
            Fullscreen(position='topleft').add_to(harita)
            folium.PolyLine(list(zip(df_loc['latitude'], df_loc['longitude'])), color="blue", weight=5, opacity=0.9).add_to(harita)

            # --- ŞEFFAF FİLTRE (LEGEND) GRUPLARI ---
            fg_hizlanma = folium.FeatureGroup(name="🟠 Ani Hızlanma", show=True)
            fg_fren = folium.FeatureGroup(name="🔴 Sert Fren", show=True)
            fg_savrulma = folium.FeatureGroup(name="🟣 Sert Viraj / Manevra", show=True)
            fg_hiz_ihlali = folium.FeatureGroup(name="🔵 Hız İhlali", show=True)

            def ekle_isaretleyici_katmana(df_olay, renk_adi, yazi_sabiti, ikon_adi, hedef_katman):
                if df_olay.empty: return
                olay_loc = pd.merge_asof(df_olay, df_loc, on='seconds_elapsed', direction='nearest')
                for _, satir in olay_loc.iterrows():
                    zaman_sn = satir['seconds_elapsed']
                    siddet = satir.get('siddet', 0)
                    hiz = satir.get('hiz_kmh', 0)
                    popup_metni = f"<b>{yazi_sabiti}</b><br>Zaman: {zaman_sn:.1f}. Saniye<br>Şiddet: {siddet:.2f}<br>Hız: {hiz:.0f} km/h"
                    folium.Marker(
                        location=[satir['latitude'], satir['longitude']],
                        popup=popup_metni,
                        icon=folium.Icon(color=renk_adi, icon=ikon_adi)
                    ).add_to(hedef_katman)

            ekle_isaretleyici_katmana(fren_baslangiclari, 'red', 'Ani Fren', 'info-sign', fg_fren)
            ekle_isaretleyici_katmana(hiz_baslangiclari, 'orange', 'Ani Hızlanma', 'info-sign', fg_hizlanma)
            ekle_isaretleyici_katmana(sert_virajlar, 'purple', 'Sert Viraj / Manevra', 'info-sign', fg_savrulma)

            if not df_hiz_ihlalleri.empty:
                for _, satir in df_hiz_ihlalleri.iterrows():
                    f = satir['fark']; lim = satir['hiz_limiti']
                    ihlal_tipi = ihlal_kademesi(f, lim)

                    popup_hiz = f"<b>Hız İhlali ({ihlal_tipi})</b><br>Zaman: {satir['seconds_elapsed']:.1f}. Saniye<br>Hız: {satir['hiz_kmh']:.0f} km/h (Limit: {lim:.0f})<br>Sınır Aşımı: +{f:.0f} km/h"
                    folium.Marker(
                        location=[satir['latitude'], satir['longitude']],
                        popup=popup_hiz,
                        icon=folium.Icon(color='blue', icon='warning', prefix='fa')
                    ).add_to(fg_hiz_ihlali)

            fg_hizlanma.add_to(harita)
            fg_fren.add_to(harita)
            fg_savrulma.add_to(harita)
            fg_hiz_ihlali.add_to(harita)

            if len(kaza_baslangiclari) > 0:
                kaza_loc = pd.merge_asof(kaza_baslangiclari, df_loc, on='seconds_elapsed', direction='nearest')
                for _, satir in kaza_loc.iterrows():
                    hiz = satir.get('hiz_kmh', 0)
                    popup_kaza = f"<b>💥 KAZA / SAVRULMA NOKTASI</b><br>Zaman: {satir['seconds_elapsed']:.1f}. Saniye<br>Hız: {hiz:.0f} km/h"
                    folium.Marker(
                        location=[satir['latitude'], satir['longitude']],
                        popup=popup_kaza,
                        icon=folium.Icon(color="black", icon="remove")
                    ).add_to(harita)

            folium.LayerControl(position='topright', collapsed=False).add_to(harita)

            # --- CSS: Yarı Saydam (Glassmorphism) Arka Plan ---
            seffaf_css = """
            <style>
            .leaflet-control-layers {
                background: rgba(20, 20, 30, 0.75) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                border-radius: 8px !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
                color: white !important;
                font-family: 'Arial', sans-serif;
                font-size: 14px;
                font-weight: 500;
            }
            .leaflet-control-layers-expanded {
                background: rgba(20, 20, 30, 0.75) !important;
                padding: 10px 15px !important;
            }
            .leaflet-control-layers-overlays label {
                margin-bottom: 5px;
                cursor: pointer;
            }
            .leaflet-control-layers-overlays input[type="checkbox"] {
                margin-right: 8px;
                cursor: pointer;
            }
            .leaflet-control-layers-base {
                display: none !important;
            }
            .leaflet-control-layers-separator {
                display: none !important;
            }
            </style>
            """
            harita.get_root().html.add_child(folium.Element(seffaf_css))

            min_lat, max_lat = gecerli_konumlar['latitude'].min(), gecerli_konumlar['latitude'].max()
            min_lon, max_lon = gecerli_konumlar['longitude'].min(), gecerli_konumlar['longitude'].max()
            harita.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
            st_folium(harita, use_container_width=True, height=550, returned_objects=[])

    with tab_grafik:
        if not fren_baslangiclari.empty:
            fren_baslangiclari['ceza'] = fren_baslangiclari['siddet'].apply(lambda s: min(5.0 * max(0, s - FREN_ESIGI), 10.0))
        if not hiz_baslangiclari.empty:
            hiz_baslangiclari['ceza'] = hiz_baslangiclari['siddet'].apply(lambda s: min(4.0 * max(0, s - HIZ_ESIGI), 8.0))
        if not sert_virajlar.empty:
            sert_virajlar['ceza'] = sert_virajlar['siddet'].apply(lambda s: min(3.0 * max(0, s - VIRAJ_CEZA), 6.0))
        if not df_hiz_ihlalleri.empty:
            df_hiz_ihlalleri['ceza'] = df_hiz_ihlalleri.apply(lambda r: hiz_ceza_puani(r['hiz_kmh'], r['hiz_limiti']), axis=1)

        fig = make_subplots(rows=3, cols=1, shared_xaxes=False,
                            subplot_titles=('İleri/Geri İvme (Y Ekseni)',
                                            'Sert Viraj / Merkezkaç İvmesi (X Ekseni)',
                                            'GPS Hızı ve TomTom Gerçek Hız Limitleri'),
                            vertical_spacing=0.12)

        fig.add_trace(go.Scatter(x=df_accel['seconds_elapsed'], y=df_accel['y'], mode='lines', name='Ham İvme (Y)', line=dict(color='rgba(255,255,255,0.2)'), visible='legendonly', hoverinfo='skip'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_accel['seconds_elapsed'], y=df_accel['temiz_y'], mode='lines', name='Filtreli İvme (Y)', line=dict(color='#00d2ff', width=2), fill='tozeroy', fillcolor='rgba(0, 210, 255, 0.05)', hoverinfo='none'), row=1, col=1)

        fig.add_hline(y=FREN_ESIGI, line_dash="dot", line_color="rgba(255, 255, 255, 0.3)", row=1, col=1)
        fig.add_hline(y=-FREN_ESIGI, line_dash="dot", line_color="rgba(255, 255, 255, 0.3)", row=1, col=1)
        fig.add_hline(y=KAZA_IVME_ESIGI, line_dash="dot", line_width=2, line_color="rgba(255, 255, 255, 0.5)", row=1, col=1)
        fig.add_hline(y=-KAZA_IVME_ESIGI, line_dash="dot", line_width=2, line_color="rgba(255, 255, 255, 0.5)", row=1, col=1)

        if not fren_baslangiclari.empty:
            fig.add_trace(go.Scatter(
                x=fren_baslangiclari['seconds_elapsed'], y=fren_baslangiclari['temiz_y'], mode='markers', name='Sert Fren Tespit',
                customdata=np.stack((fren_baslangiclari['siddet'], fren_baslangiclari['ceza']), axis=-1),
                hovertemplate="<b>🛑 Sert Fren</b><br>Zaman: %{x:.1f} sn<br>İvme Şiddeti: %{customdata[0]:.2f} m/s²<br><br><b>🚨 Kesilen Puan: -%{customdata[1]:.1f}</b><extra></extra>",
                marker=dict(color='#ff0055', size=9, line=dict(color='#ffffff', width=1.5), symbol='circle'),
                selected=dict(marker=dict(size=18, color='#ff0055')),
                unselected=dict(marker=dict(opacity=1.0))
            ), row=1, col=1)

        if not hiz_baslangiclari.empty:
            fig.add_trace(go.Scatter(
                x=hiz_baslangiclari['seconds_elapsed'], y=hiz_baslangiclari['temiz_y'], mode='markers', name='Ani Hızlanma Tespit',
                customdata=np.stack((hiz_baslangiclari['siddet'], hiz_baslangiclari['ceza']), axis=-1),
                hovertemplate="<b>🚀 Ani Hızlanma</b><br>Zaman: %{x:.1f} sn<br>İvme Şiddeti: %{customdata[0]:.2f} m/s²<br><br><b>🚨 Kesilen Puan: -%{customdata[1]:.1f}</b><extra></extra>",
                marker=dict(color='#ffdd00', size=9, line=dict(color='#ffffff', width=1.5), symbol='circle'),
                selected=dict(marker=dict(size=18, color='#ffdd00')),
                unselected=dict(marker=dict(opacity=1.0))
            ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df_accel['seconds_elapsed'], y=df_accel['x'], mode='lines', name='Ham Yanal İvme (X)', line=dict(color='rgba(255,255,255,0.2)'), visible='legendonly', hoverinfo='skip'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_accel['seconds_elapsed'], y=df_accel['temiz_x'], mode='lines', name='Filtreli Yanal İvme (X)', line=dict(color='#b82eff', width=2), fill='tozeroy', fillcolor='rgba(184, 46, 255, 0.05)', hoverinfo='none'), row=2, col=1)

        fig.add_hline(y=VIRAJ_CEZA, line_dash="dot", line_color="rgba(255, 255, 255, 0.3)", row=2, col=1)
        fig.add_hline(y=-VIRAJ_CEZA, line_dash="dot", line_color="rgba(255, 255, 255, 0.3)", row=2, col=1)
        fig.add_hline(y=KAZA_IVME_ESIGI, line_dash="dot", line_width=2, line_color="rgba(255, 255, 255, 0.5)", row=2, col=1)
        fig.add_hline(y=-KAZA_IVME_ESIGI, line_dash="dot", line_width=2, line_color="rgba(255, 255, 255, 0.5)", row=2, col=1)

        if not sert_virajlar.empty:
            fig.add_trace(go.Scatter(
                x=sert_virajlar['seconds_elapsed'], y=sert_virajlar['temiz_x'], mode='markers', name='Cezalı Sert Viraj',
                customdata=np.stack((sert_virajlar['siddet'], sert_virajlar['ceza']), axis=-1),
                hovertemplate="<b>🔄 Sert Viraj / Manevra</b><br>Zaman: %{x:.1f} sn<br>Viraj Şiddeti: %{customdata[0]:.2f} m/s²<br><br><b>🚨 Kesilen Puan: -%{customdata[1]:.1f}</b><extra></extra>",
                marker=dict(color='#ff0055', size=9, line=dict(color='#ffffff', width=1.5), symbol='circle'),
                selected=dict(marker=dict(size=18, color='#ff0055')),
                unselected=dict(marker=dict(opacity=1.0))
            ), row=2, col=1)

        fig.add_trace(go.Scatter(x=loc_hiz['seconds_elapsed'], y=loc_hiz['hiz_kmh'], mode='lines', name='Araç Hızı (km/h)', line=dict(color='#39ff14', width=2.5), fill='tozeroy', fillcolor='rgba(57, 255, 20, 0.08)', hoverinfo='none'), row=3, col=1)
        fig.add_trace(go.Scatter(x=loc_hiz['seconds_elapsed'], y=loc_hiz['hiz_limiti'], mode='lines', name='Tabela Limiti', line=dict(color='#ff0055', dash='dash', width=1.5), hoverinfo='none'), row=3, col=1)

        if not df_hiz_ihlalleri.empty:
            fig.add_trace(go.Scatter(
                x=df_hiz_ihlalleri['seconds_elapsed'], y=df_hiz_ihlalleri['hiz_kmh'], mode='markers', name='Hız İhlali',
                customdata=np.stack((df_hiz_ihlalleri['hiz_limiti'], df_hiz_ihlalleri['ceza']), axis=-1),
                hovertemplate="<b>⚡ Hız İhlali!</b><br>Zaman: %{x:.1f} sn<br>Araç Hızı: %{y:.1f} km/h<br>Yasal Limit: %{customdata[0]:.0f} km/h<br><br><b>🚨 Kesilen Puan: -%{customdata[1]:.1f}</b><extra></extra>",
                marker=dict(color='rgba(0,0,0,0)', size=12, symbol='circle', line=dict(width=2.5, color='#ff0055')),
                selected=dict(marker=dict(size=20, color='rgba(0,0,0,0)')),
                unselected=dict(marker=dict(opacity=1.0))
            ), row=3, col=1)

        fig.update_layout(
            template="plotly_dark",
            clickmode='event+select',
            height=750,
            hovermode="closest",
            margin=dict(l=10, r=10, t=40, b=20),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5, bgcolor='rgba(0,0,0,0)'),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(15,15,20,1)'
        )

        fig.update_xaxes(showgrid=True, gridcolor='rgba(255, 255, 255, 0.05)', zeroline=False)
        fig.update_yaxes(showgrid=True, gridcolor='rgba(255, 255, 255, 0.05)', zeroline=True, zerolinecolor='rgba(255, 255, 255, 0.15)')
        fig.update_xaxes(title_text="Zaman (Saniye)", row=3, col=1)

        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})

# --- 5. ARAYÜZ YÖNETİMİ ---

# SOL PANEL (SİDEBAR) - LOGO VE MARKA
try:
    st.sidebar.image("assets/logo.jpeg", use_container_width=True)
except Exception:
    pass  # Logo yüklenmezse uygulama çalışmaya devam etsin

st.sidebar.title("DriveSense")
st.sidebar.divider()

st.sidebar.subheader("SÜRÜŞ ANALİZİ")
sayfa = st.sidebar.radio("Seçim Yapın:", ["🚀 Yeni Sürüş Analizi", "📂 Sürüş Geçmişi"])

if sayfa == "🚀 Yeni Sürüş Analizi":
    st.title("🚗 DriveSense Analiz Paneli")
    st.markdown("Sürüş verilerinizi analiz edin, güvenli sürüş alışkanlıklarınızı geliştirin.")

    st.divider()
    st.markdown("### 📂 Sensör Verilerini Yükle")

    col_up1, col_up2, col_up3 = st.columns(3)
    file_accel = col_up1.file_uploader("📈 İvmeölçer (Accelerometer)", type=['csv'], help="İleri/geri ivme verilerini içerir.")
    file_gyro = col_up2.file_uploader("⚖️ Jiroskop (Gyroscope)", type=['csv'], help="Aracın açısal dönüş ve savrulma verilerini içerir.")
    file_loc = col_up3.file_uploader("📍 Konum (Location)", type=['csv'], help="Enlem, boylam ve sensör tabanlı hız verilerini içerir.")

    if file_accel and file_gyro and file_loc:
        df_a, df_g, df_l = pd.read_csv(file_accel), pd.read_csv(file_gyro), pd.read_csv(file_loc)
        analizi_yap_ve_ciz(df_a, df_g, df_l, surus_id_icin_key="yeni")

        st.divider()
        st.markdown("### 💾 Raporu Veritabanına Kaydet")
        surus_adi_input = st.text_input("Bu sürüşe bir isim verin:", placeholder="Örn: Kadıköy-Bostancı Sürüşü", key="yeni_surus_isim_input")
        if st.button("💾 Kaydet", use_container_width=True, key="yeni_surus_kaydet_btn"):
            conn = sqlite3.connect('surus_verileri.db')
            c = conn.cursor()
            c.execute("INSERT INTO gecmis_surusler_v2 (tarih, accel_csv, gyro_csv, loc_csv, surus_adi) VALUES (?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), df_a.to_csv(index=False), df_g.to_csv(index=False), df_l.to_csv(index=False), surus_adi_input.strip() or "İsimsiz Sürüş"))
            conn.commit()
            conn.close()
            st.success("✅ Veritabanına başarıyla kaydedildi!")

elif sayfa == "📂 Sürüş Geçmişi":
    st.title("📂 Kayıtlı DriveSense Raporları")
    conn = sqlite3.connect('surus_verileri.db')
    df_gecmis = pd.read_sql_query("SELECT id, tarih, surus_adi FROM gecmis_surusler_v2 ORDER BY id DESC", conn)

    if not df_gecmis.empty:
        secenekler = {f"[{row['tarih']}] {row['surus_adi']}": row['id'] for _, row in df_gecmis.iterrows()}
        secilen_gosterim = st.selectbox("İncelemek istediğiniz raporu seçin:", options=list(secenekler.keys()), index=None)

        if secilen_gosterim:
            secilen_id = secenekler[secilen_gosterim]
            mevcut_isim = secilen_gosterim.split("] ")[1]
            with st.expander("⚙️ Rapor Yönetimi (İsim Düzenle / Sil)"):
                c1, c2, c3 = st.columns([2, 1, 1])
                yeni_isim = c1.text_input("Yeni İsim:", value=mevcut_isim, key=f"isim_input_{secilen_id}")
                if c2.button("İsmi Güncelle", use_container_width=True):
                    c = conn.cursor(); c.execute("UPDATE gecmis_surusler_v2 SET surus_adi = ? WHERE id = ?", (yeni_isim, secilen_id)); conn.commit()
                    st.rerun()
                if c3.button("🗑️ Sil", type="primary", use_container_width=True):
                    c = conn.cursor(); c.execute("DELETE FROM gecmis_surusler_v2 WHERE id = ?", (secilen_id,)); conn.commit()
                    st.rerun()

            c = conn.cursor(); c.execute("SELECT accel_csv, gyro_csv, loc_csv FROM gecmis_surusler_v2 WHERE id = ?", (secilen_id,))
            kayit = c.fetchone(); conn.close()

            if kayit:
                analizi_yap_ve_ciz(pd.read_csv(io.StringIO(kayit[0])), pd.read_csv(io.StringIO(kayit[1])), pd.read_csv(io.StringIO(kayit[2])), surus_id_icin_key=str(secilen_id))
    else:
        conn.close()
        st.warning("Sistemde henüz kayıtlı bir sürüş raporu bulunamadı.")
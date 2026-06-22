import streamlit as st
import requests
import datetime
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
import matplotlib.font_manager as fm
import pandas as pd
import os

# --- 폰트 캐시 강제 삭제 및 나눔 폰트 설정 ---
def setup_font():
    # 폰트 캐시 강제 삭제
    cachedir = matplotlib.get_cachedir()
    if os.path.exists(cachedir):
        for f in os.listdir(cachedir):
            if f.startswith('fontlist'):
                try: os.remove(os.path.join(cachedir, f))
                except: pass
    
    # 폰트 경로 설정
    font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = 'NanumGothic'
    else:
        # 로컬 환경 대응
        import platform
        sys_name = platform.system()
        if sys_name == "Windows": plt.rcParams['font.family'] = 'Malgun Gothic'
        elif sys_name == "Darwin": plt.rcParams['font.family'] = 'AppleGothic'
        else: plt.rcParams['font.family'] = 'sans-serif'
    
    matplotlib.rcParams['axes.unicode_minus'] = False

setup_font()

# --- 앱 로직 ---
TARGET_LEVEL = 300

def interpolate_tide_cosine(h1, h2, total_minutes, current_minute):
    if total_minutes == 0: return h1
    t = current_minute / total_minutes
    ratio = (1 - math.cos(math.pi * t)) / 2
    return h1 + (h2 - h1) * ratio

def fetch_tide_data(formatted_date):
    params = {
        "serviceKey": "ac77a9b1ecff31d6eb96a3e27f6bfd18210d06cbb8a1cece5f0272be11fc71c7",
        "obsCode": "SO_1258",
        "reqDate": formatted_date,
        "type": "json"
    }
    try:
        res = requests.get("https://apis.data.go.kr/1192136/tideFcstHghLw/GetTideFcstHghLwApiService", params=params)
        res.raise_for_status()
        return res.json().get("body", {}).get("items", {}).get("item", [])
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류 발생: {e}")
        return []

st.set_page_config(page_title="런칭 시간 분석기", layout="centered")
st.title("🌊 런칭 시간 분석기")

target_date = st.date_input("날짜를 선택하세요", datetime.date.today())
formatted_date = target_date.strftime("%Y%m%d")

items = fetch_tide_data(formatted_date)

if not items:
    st.warning("데이터가 없습니다.")
else:
    st.write(f"### 📅 {formatted_date} 물때 정보")
    
    # 데이터 표
    tide_data = [{"시간": i['predcDt'], "수위(cm)": float(i.get("predcTdlvVl", 0)), "구분": "만조" if float(i.get("predcTdlvVl", 0)) > 400 else "간조"} for i in items]
    st.table(pd.DataFrame(tide_data))

    # 분석 로직
    plot_times, plot_tides = [], []
    entry_times, exit_times = [], []
    for i in range(len(items) - 1):
        t1, t2 = datetime.datetime.strptime(items[i]['predcDt'], "%Y-%m-%d %H:%M"), datetime.datetime.strptime(items[i+1]['predcDt'], "%Y-%m-%d %H:%M")
        h1, h2 = float(items[i]['predcTdlvVl']), float(items[i+1]['predcTdlvVl'])
        diff_min = int((t2 - t1).total_seconds() / 60)
        prev_h = None
        for m in range(diff_min + 1):
            h = interpolate_tide_cosine(h1, h2, diff_min, m)
            curr_t = t1 + datetime.timedelta(minutes=m)
            plot_times.append(curr_t); plot_tides.append(h)
            if prev_h is not None:
                if prev_h < TARGET_LEVEL <= h: entry_times.append(curr_t)
                elif prev_h >= TARGET_LEVEL > h: exit_times.append(curr_t)
            prev_h = h

    st.write("### ✅ 분석 결과")
    c1, c2 = st.columns(2)
    with c1: 
        for et in entry_times: st.success(f"진입: {et.strftime('%H:%M:%S')}")
    with c2: 
        for xt in exit_times: st.warning(f"이탈: {xt.strftime('%H:%M:%S')}")

    # 그래프 출력
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(plot_times, plot_tides, color='blue', label='수위')
    ax.axhline(y=TARGET_LEVEL, color='red', linestyle='--', label=f'{TARGET_LEVEL}cm')
    ax.legend()
    ax.set_title("런칭 시간 분석 차트")
    ax.set_ylabel("수위(cm)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    st.pyplot(fig)
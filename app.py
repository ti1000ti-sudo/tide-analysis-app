import streamlit as st
import requests
import datetime
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
import pandas as pd
import platform

# --- 한글 폰트 설정 ---
system_name = platform.system()
if system_name == "Windows":
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif system_name == "Darwin":
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'NanumGothic'

matplotlib.rcParams['axes.unicode_minus'] = False

# --- 설정 ---
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

# --- 웹 UI ---
st.set_page_config(page_title="런칭 시간 분석기", layout="centered")
st.title("🌊 런칭 시간 분석기")

# 날짜 선택
target_date = st.date_input("분석할 날짜를 선택하세요", datetime.date.today())
formatted_date = target_date.strftime("%Y%m%d")

# 데이터 가져오기 및 분석
items = fetch_tide_data(formatted_date)

if not items:
    st.warning("해당 날짜에 데이터가 없거나 서버 응답이 없습니다.")
else:
    st.write(f"### 📅 {formatted_date} 물때 정보")
    
    tide_data = []
    for i in items:
        val = float(i.get("predcTdlvVl", 0))
        tide_type = "만조" if val > 400 else "간조"
        tide_data.append({"시간": i['predcDt'], "수위(cm)": val, "구분": tide_type})
    
    st.table(pd.DataFrame(tide_data))

    # 분석 로직
    plot_times, plot_tides = [], []
    entry_times, exit_times = [], []

    for i in range(len(items) - 1):
        t1 = datetime.datetime.strptime(items[i]['predcDt'], "%Y-%m-%d %H:%M")
        t2 = datetime.datetime.strptime(items[i + 1]['predcDt'], "%Y-%m-%d %H:%M")
        h1, h2 = float(items[i]['predcTdlvVl']), float(items[i + 1]['predcTdlvVl'])
        diff_min = int((t2 - t1).total_seconds() / 60)
        prev_h = None

        for m in range(diff_min + 1):
            h = interpolate_tide_cosine(h1, h2, diff_min, m)
            curr_t = t1 + datetime.timedelta(minutes=m)
            plot_times.append(curr_t)
            plot_tides.append(h)

            if prev_h is not None:
                if prev_h < TARGET_LEVEL <= h:
                    ratio = (TARGET_LEVEL - prev_h) / (h - prev_h)
                    ex = curr_t - datetime.timedelta(minutes=1) + datetime.timedelta(seconds=ratio * 60)
                    entry_times.append(ex)
                elif prev_h >= TARGET_LEVEL > h:
                    ratio = (prev_h - TARGET_LEVEL) / (prev_h - h)
                    ex = curr_t - datetime.timedelta(minutes=1) + datetime.timedelta(seconds=ratio * 60)
                    exit_times.append(ex)
            prev_h = h

    st.write("### ✅ 분석 결과")
    col1, col2 = st.columns(2)
    with col1:
        for et in entry_times: st.success(f"진입: {et.strftime('%H:%M:%S')}")
    with col2:
        for xt in exit_times: st.warning(f"이탈: {xt.strftime('%H:%M:%S')}")

    # 그래프 출력
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(plot_times, plot_tides, color='blue', label='수위(cm)')
    ax.axhline(y=TARGET_LEVEL, color='red', linestyle='--', label=f'{TARGET_LEVEL}cm')
    ax.legend()
    ax.set_title("Launching Time Prediction")
    ax.set_ylabel("수위(cm)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    st.pyplot(fig)
import streamlit as st
import requests
import datetime
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib

# --- 한글 폰트 설정 (웹 환경에서는 자동 적용되거나 별도 설정 필요) ---
matplotlib.rcParams['axes.unicode_minus'] = False

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
    res = requests.get("https://apis.data.go.kr/1192136/tideFcstHghLw/GetTideFcstHghLwApiService", params=params)
    return res.json().get("body", {}).get("items", {}).get("item", [])

# --- 웹 UI ---
st.set_page_config(page_title="런칭 시간 분석기", layout="centered")
st.title("🌊 런칭 시간 분석기")

# 날짜 선택
target_date = st.date_input("분석할 날짜를 선택하세요", datetime.date.today())
formatted_date = target_date.strftime("%Y%m%d")

if st.button("분석 실행"):
    items = fetch_tide_data(formatted_date)
    
    if not items:
        st.error("해당 날짜에 데이터가 없습니다.")
    else:
        st.write(f"### 📅 {formatted_date} 물때 정보")
        
        # 물때 정보 표시
        tide_data = []
        for i in items:
            val = float(i.get("predcTdlvVl", 0))
            tide_type = "만조" if val > 400 else "간조"
            tide_data.append({"시간": i['predcDt'], "수위(cm)": val, "구분": tide_type})
        
        st.table(pd.DataFrame(tide_data))

        # 분석 및 그래프
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

        # 결과 출력
        st.write("### ✅ 분석 결과")
        for et in entry_times: st.success(f"진입 가능 시간: {et.strftime('%H:%M:%S')}")
        for xt in exit_times: st.warning(f"이탈 주의 시간: {xt.strftime('%H:%M:%S')}")

        # 그래프 그리기
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(plot_times, plot_tides, color='blue', label='수위')
        ax.axhline(y=TARGET_LEVEL, color='red', linestyle='--', label=f'{TARGET_LEVEL}cm')
        ax.legend()
        ax.set_title("Launching Time Prediction")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        st.pyplot(fig)

import pandas as pd # 위쪽 import에 추가하는 것이 좋습니다.
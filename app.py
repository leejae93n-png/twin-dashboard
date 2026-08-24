import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta, timezone
import os
from PIL import Image

# 한국 표준시(KST: UTC+9) 정의
KST = timezone(timedelta(hours=9))

def get_now_kst():
    return datetime.now(KST)

st.set_page_config(page_title="쌍둥이 통합 수유 & 성장 대시보드", layout="wide")

FEEDING_FILE = "twin_feeding_data.csv"
POOP_FILE = "twin_poop_data.csv"
SLEEP_FILE = "twin_sleep_data.csv"

BIRTH_DATE = date(2026, 5, 14)
DUE_DATE = date(2026, 8, 12)

SCHEDULE_OPTIONS = {
    "일 8회 (3시간 텀)": ["01:00", "04:00", "07:00", "10:00", "13:00", "16:00", "19:00", "22:00"],
    "일 7회 (3.5시간 텀)": ["01:00", "04:30", "08:00", "11:30", "15:00", "18:30", "22:00"],
    "일 6회 (4시간 텀)": ["02:00", "06:00", "10:00", "14:00", "18:00", "22:00"],
    "일 5회 (4.5시간 텀)": ["06:00", "10:30", "15:00", "19:30", "23:00"]
}

def init_data():
    if not os.path.exists(FEEDING_FILE):
        records = []
        today_str = get_now_kst().strftime("%Y-%m-%d")
        all_possible_times = list(set([t for sch in SCHEDULE_OPTIONS.values() for t in sch]))
        for child in ["원빈", "현빈"]:
            row = {"날짜": today_str, "아동": child, "몸무게": 3.5 if child == "원빈" else 4.1}
            for t in all_possible_times:
                row[t] = 0
            records.append(row)
        df = pd.DataFrame(records)
        df.to_csv(FEEDING_FILE, index=False, encoding="utf-8-sig")
        
    if not os.path.exists(POOP_FILE):
        df_poop = pd.DataFrame(columns=["날짜", "아동", "시간", "종류"])
        df_poop.to_csv(POOP_FILE, index=False, encoding="utf-8-sig")

    if not os.path.exists(SLEEP_FILE):
        df_sleep = pd.DataFrame(columns=["날짜", "아동", "시작시간", "종류", "수면분"])
        df_sleep.to_csv(SLEEP_FILE, index=False, encoding="utf-8-sig")

init_data()

def load_feeding_data(): return pd.read_csv(FEEDING_FILE)
def load_poop_data(): return pd.read_csv(POOP_FILE)
def load_sleep_data(): return pd.read_csv(SLEEP_FILE)

def save_feeding_data(df): df.to_csv(FEEDING_FILE, index=False, encoding="utf-8-sig")
def save_poop_data(df): df.to_csv(POOP_FILE, index=False, encoding="utf-8-sig")
def save_sleep_data(df): df.to_csv(SLEEP_FILE, index=False, encoding="utf-8-sig")

st.title("👶 쌍둥이 이른둥이 맞춤 수유 & 성장 대시보드")

today_dt = get_now_kst().date()
chronological_days = (today_dt - BIRTH_DATE).days
corrected_days = (today_dt - DUE_DATE).days

st.info(
    f"🍼 **성장 기준일 안내** (오늘: {today_dt.strftime('%Y-%m-%d')}) | "
    f"**출생일령**: 생후 **{chronological_days}일차** | "
    f"**교정일령**: 교정 **{corrected_days}일차**"
)

df_feeding = load_feeding_data()
df_poop = load_poop_data()
df_sleep = load_sleep_data()

# --- 사이드바 ---
st.sidebar.header("⚙️ 수유 스케줄 설정")
selected_schedule_key = st.sidebar.selectbox("현재 적용할 수유 패턴", list(SCHEDULE_OPTIONS.keys()), index=0)
current_time_cols = SCHEDULE_OPTIONS[selected_schedule_key]

st.sidebar.divider()
st.sidebar.header("💾 데이터 백업")
col_b1, col_b2, col_b3 = st.sidebar.columns(3)
with col_b1: st.download_button("📥 수유", df_feeding.to_csv(index=False, encoding="utf-8-sig"), f"feeding_{today_dt}.csv", "text/csv")
with col_b2: st.download_button("📥 배변", df_poop.to_csv(index=False, encoding="utf-8-sig"), f"poop_{today_dt}.csv", "text/csv")
with col_b3: st.download_button("📥 수면", df_sleep.to_csv(index=False, encoding="utf-8-sig"), f"sleep_{today_dt}.csv", "text/csv")

col_left, col_right = st.columns(2)

def render_child_section(child_name, container):
    global df_feeding, df_poop, df_sleep
    
    with container:
        # --- 1. 프로필 영역 ---
        img_filename_png = f"profile_{child_name}.png"
        img_filename_jpg = f"profile_{child_name}.jpg"
        
        head_col1, head_col2 = st.columns([1.3, 3])
        with head_col1:
            if os.path.exists(img_filename_png):
                st.image(Image.open(img_filename_png), width=120)
            elif os.path.exists(img_filename_jpg):
                st.image(Image.open(img_filename_jpg), width=120)
            else:
                st.markdown("## 👶")
                
        with head_col2:
            st.markdown(f"<h2 style='margin-bottom:0px; padding-top:10px;'>이{child_name}</h2>", unsafe_allow_html=True)
            with st.expander("🖼️ 프로필 사진 변경", expanded=False):
                uploaded_file = st.file_uploader(f"{child_name} 사진 선택", type=["jpg", "png", "jpeg"], key=f"img_{child_name}")
                if uploaded_file is not None:
                    img = Image.open(uploaded_file)
                    img.save(img_filename_png)
                    st.toast("프로필 사진 저장 완료!", icon="🖼️")
                    st.rerun()

        today_str = get_now_kst().strftime("%Y-%m-%d")
        child_df = df_feeding[df_feeding["아동"] == child_name].copy().sort_values(by="날짜").reset_index(drop=True)
        
        if today_str not in child_df["날짜"].values:
            last_weight = child_df["몸무게"].dropna().iloc[-1] if len(child_df["몸무게"].dropna()) > 0 else (3.5 if child_name == "원빈" else 4.1)
            new_row = {"날짜": today_str, "아동": child_name, "몸무게": last_weight}
            for col in df_feeding.columns:
                if col not in ["날짜", "아동", "몸무게"]: new_row[col] = 0
            df_feeding = pd.concat([df_feeding, pd.DataFrame([new_row])], ignore_index=True)
            save_feeding_data(df_feeding)
            child_df = df_feeding[df_feeding["아동"] == child_name].copy().sort_values(by="날짜").reset_index(drop=True)

        child_df["몸무게_원본"] = child_df["몸무게"]
        child_df["몸무게_보간"] = child_df["몸무게"].interpolate(method="linear").bfill().ffill()
        child_df["추정여부"] = child_df["몸무게_원본"].isna().map({True: "(추정치)", False: ""})

        today_row = df_feeding[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == today_str)].iloc[0]
        weight = float(today_row["몸무게"]) if pd.notna(today_row["몸무게"]) else float(child_df[child_df["날짜"] == today_str].iloc[0]["몸무게_보간"])
        target_weight_for_next_step = 4.8
        
        if len(child_df) >= 2:
            days_diff = len(child_df) - 1
            weight_diff = weight - float(child_df.iloc[0]["몸무게_보간"])
            daily_gain = (weight_diff / days_diff) if days_diff > 0 else 0.03
            if daily_gain <= 0: daily_gain = 0.02
        else: daily_gain = 0.03

        if weight >= target_weight_for_next_step:
            predict_msg = f"💡 체중 {target_weight_for_next_step}kg 도달 완료! 수유 텀 연장(일 6~7회) 권장"
        else:
            days_left = max(int((target_weight_for_next_step - weight) / daily_gain), 1)
            predict_msg = f"💡 현재 성장 속도(일 {daily_gain*1000:.0f}g) 기준, **약 {days_left}일 후({target_weight_for_next_step}kg 도달 시)** 수유 텀 연장 권장"

        st.caption(predict_msg)

        today_poop_df = df_poop[(df_poop["아동"] == child_name) & (df_poop["날짜"] == today_str)]
        poop_cnt = len(today_poop_df[today_poop_df["종류"] == "대변"])
        pee_cnt = len(today_poop_df[today_poop_df["종류"] == "소변"])

        today_sleep_df = df_sleep[(df_sleep["아동"] == child_name) & (df_sleep["날짜"] == today_str)]
        total_sleep_min = today_sleep_df["수면분"].sum() if len(today_sleep_df) > 0 else 0

        target_total = min(int(weight * 180), 1000)
        actual_total = sum([int(today_row[c]) for c in current_time_cols if c in today_row and pd.notna(today_row[c])])

        # --- 현황 지표 ---
        k1, k2, k3 = st.columns([1.1, 1.3, 1.2])
        with k1: st.metric("체중 / 기준", f"{weight:.2f} kg", "1kg당 180ml")
        with k2: st.metric("현재 수유 달성", f"{actual_total} / {target_total} ml", f"{actual_total - target_total} ml")
        with k3: st.metric("오늘 배변/수면", f"💩{poop_cnt} 🟡{pee_cnt}", f"😴 {total_sleep_min//60}시간 {total_sleep_min%60}분")

        # --- 동적 스마트 육아 가이드 ---
        last_feed_time = None
        for c in reversed(current_time_cols):
            if c in today_row and pd.notna(today_row[c]) and int(today_row[c]) > 0:
                last_feed_time = c
                break
        
        next_feed_str = "시간 정보 없음"
        if last_feed_time:
            l_time = datetime.strptime(last_feed_time, "%H:%M")
            next_feed_str = (l_time + timedelta(hours=3)).strftime("%H:%M")

        next_diaper_str = "점검 권장"
        if len(today_poop_df) > 0:
            last_p_time_str = today_poop_df.iloc[-1]["시간"]
            try:
                l_p_time = datetime.strptime(last_p_time_str, "%H:%M")
                next_diaper_str = (l_p_time + timedelta(hours=2)).strftime("%H:%M")
            except: pass

        st.markdown(
            f'<div style="background-color:#1e293b; padding:10px 15px; border-radius:10px; border-left:5px solid #3b82f6; margin-bottom:10px;">'
            f'<span style="font-size:14px; font-weight:bold; color:#93c5fd;">🔔 맞춤 예측 가이드</span><br>'
            f'<span style="font-size:13px; color:#e2e8f0;">🍼 다음 권장 수유 시각: <b>{next_feed_str}</b> (3시간 텀) | '
            f'👶 다음 기저귀 점검: <b>{next_diaper_str}</b> (2시간 텀)</span>'
            f'</div>', unsafe_allow_html=True
        )

        last_recorded_idx = 0
        for i, c in enumerate(current_time_cols):
            if c in today_row and pd.notna(today_row[c]) and int(today_row[c]) > 0: last_recorded_idx = i

        # --- 2. 수유량 입력 및 저장 ---
        st.subheader("🍼 수유량 입력")
        
        q_c1, q_c2, q_c3 = st.columns([2, 2, 2])
        with q_c1: selected_slot = st.selectbox("수유 시간", current_time_cols, index=last_recorded_idx, key=f"q_slot_{child_name}")
        with q_c2:
            cur_val = int(today_row[selected_slot]) if selected_slot in today_row and pd.notna(today_row[selected_slot]) else 0
            feed_val = st.number_input("수유량 (ml)", value=cur_val if cur_val > 0 else 100, step=5, key=f"q_val_{child_name}")
        with q_c3:
            st.write("")
            st.write("")
            if st.button(f"💾 수유 저장", key=f"q_btn_{child_name}", type="primary", use_container_width=True):
                df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == today_str), selected_slot] = feed_val
                save_feeding_data(df_feeding)
                st.toast(f"✅ {child_name} [{selected_slot}] {feed_val}ml 저장 완료!", icon="🍼")
                st.rerun()

        # 수유 타임라인
        feed_badges = []
        for c in current_time_cols:
            v = int(today_row[c]) if c in today_row and pd.notna(today_row[c]) else 0
            if v > 0:
                feed_badges.append(
                    f'<span style="display:inline-block; background-color:#1e3a5f; border:1px solid #3b82f6; '
                    f'padding:3px 8px; margin:2px; border-radius:12px; font-size:13px; font-weight:bold;">'
                    f'🍼 {c}: {v}ml</span>'
                )
        if feed_badges: st.markdown("".join(feed_badges), unsafe_allow_html=True)

        # --- 3. 실시간 1초 원클릭 기록 ---
        st.markdown("---")
        st.subheader("⚡ 실시간 1초 원클릭 기록 (현재시간)")
        
        btn_c1, btn_c2, btn_c3 = st.columns(3)
        with btn_c1:
            if st.button(f"💩 대변 (지금)", key=f"now_poop_{child_name}", use_container_width=True):
                now_str = get_now_kst().strftime("%H:%M")
                new_poop = {"날짜": today_str, "아동": child_name, "시간": now_str, "종류": "대변"}
                df_poop = pd.concat([df_poop, pd.DataFrame([new_poop])], ignore_index=True)
                save_poop_data(df_poop)
                st.toast(f"💩 {child_name} 대변 ({now_str}) 저장!", icon="💩")
                st.rerun()
        with btn_c2:
            if st.button(f"🟡 소변 (지금)", key=f"now_pee_{child_name}", use_container_width=True):
                now_str = get_now_kst().strftime("%H:%M")
                new_poop = {"날짜": today_str, "아동": child_name, "시간": now_str, "종류": "소변"}
                df_poop = pd.concat([df_poop, pd.DataFrame([new_poop])], ignore_index=True)
                save_poop_data(df_poop)
                st.toast(f"🟡 {child_name} 소변 ({now_str}) 저장!", icon="🟡")
                st.rerun()
        with btn_c3:
            sleeping_row = df_sleep[(df_sleep["아동"] == child_name) & (df_sleep["날짜"] == today_str) & (df_sleep["수면분"] == 0)]
            if len(sleeping_row) == 0:
                if st.button(f"😴 잠들었음 (지금)", key=f"sleep_start_{child_name}", use_container_width=True):
                    now_str = get_now_kst().strftime("%H:%M")
                    new_sleep = {"날짜": today_str, "아동": child_name, "시작시간": now_str, "종류": "수면중", "수면분": 0}
                    df_sleep = pd.concat([df_sleep, pd.DataFrame([new_sleep])], ignore_index=True)
                    save_sleep_data(df_sleep)
                    st.toast(f"😴 {child_name} 수면 시작 ({now_str})", icon="😴")
                    st.rerun()
            else:
                if st.button(f"⏰ 깨어났음 (지금)", key=f"sleep_end_{child_name}", type="primary", use_container_width=True):
                    now_dt = get_now_kst()
                    start_str = sleeping_row.iloc[-1]["시작시간"]
                    start_dt = datetime.strptime(f"{today_str} {start_str}", "%Y-%m-%d %H:%M").replace(tzinfo=KST)
                    duration_min = int((now_dt - start_dt).total_seconds() / 60)
                    
                    target_idx = sleeping_row.index[-1]
                    df_sleep.loc[target_idx, "종류"] = now_dt.strftime("%H:%M")
                    df_sleep.loc[target_idx, "수면분"] = max(duration_min, 1)
                    save_sleep_data(df_sleep)
                    st.toast(f"⏰ {child_name} 깨어남! 총 {duration_min}분 수면", icon="⏰")
                    st.rerun()

        # 배변/수면 타임라인
        st.write("🕒 **오늘 배변 / 수면 타임라인**")
        combined_badges = []
        if len(today_poop_df) > 0:
            for _, r in today_poop_df.iterrows():
                icon = "💩" if r["종류"] == "대변" else "🟡"
                bg_color = "#3d2b1f" if r["종류"] == "대변" else "#3a351e"
                border_color = "#8d5b28" if r["종류"] == "대변" else "#8c7b27"
                combined_badges.append(
                    f'<span style="display:inline-block; background-color:{bg_color}; border:1px solid {border_color}; '
                    f'padding:3px 8px; margin:2px; border-radius:12px; font-size:13px; font-weight:bold;">'
                    f'{icon} {r["시간"]}</span>'
                )
        if len(today_sleep_df) > 0:
            for _, r in today_sleep_df.iterrows():
                if r["수면분"] == 0:
                    combined_badges.append(
                        f'<span style="display:inline-block; background-color:#3f2d1c; border:1px solid #f59e0b; '
                        f'padding:3px 8px; margin:2px; border-radius:12px; font-size:13px; font-weight:bold;">'
                        f'😴 {r["시작시간"]}부터 수면 중...</span>'
                    )
                else:
                    combined_badges.append(
                        f'<span style="display:inline-block; background-color:#1c2d37; border:1px solid #0284c7; '
                        f'padding:3px 8px; margin:2px; border-radius:12px; font-size:13px; font-weight:bold;">'
                        f'😴 {r["시작시간"]}~{r["종류"]} ({r["수면분"]}분)</span>'
                    )

        if combined_badges: st.markdown("".join(combined_badges), unsafe_allow_html=True)
        else: st.caption("오늘 기록된 배변 및 수면 내역이 없습니다.")

        # --- 4. 🛠️ 직관적인 기록 입력 & 수정 관리 (과거 날짜 선택 기능 추가) ---
        st.markdown("---")
        st.write("🛠️ **기록 세부 추가 / 과거 데이터 수정 관리**")
        
        tab1, tab2, tab3 = st.tabs(["➕ 지나간 기록 추가 (날짜선택)", "🗑️ 오늘 기록 수정/삭제", "⚙️ 과거/오늘 체중 & 수유 일괄 수정"])

        # TAB 1: 과거 날짜 포함 배변/수면 기록 추가
        with tab1:
            target_past_date = st.date_input("기록을 넣을 날짜 선택", get_now_kst().date(), key=f"past_date_sel_{child_name}")
            target_past_str = target_past_date.strftime("%Y-%m-%d")
            record_type = st.radio("추가할 기록 종류", ["💩/🟡 배변", "😴 수면"], horizontal=True, key=f"past_type_{child_name}")
            
            if "배변" in record_type:
                with st.form(key=f"past_poop_form_{child_name}"):
                    p_c1, p_c2 = st.columns(2)
                    with p_c1: p_kind = st.selectbox("종류", ["대변", "소변"], key=f"pk_{child_name}")
                    with p_c2: p_time = st.time_input("발생 시각", get_now_kst().time(), key=f"pt_{child_name}")
                    if st.form_submit_button(f"➕ {target_past_str} 배변 기록 추가"):
                        t_str = p_time.strftime("%H:%M")
                        new_p = {"날짜": target_past_str, "아동": child_name, "시간": t_str, "종류": p_kind}
                        df_poop = pd.concat([df_poop, pd.DataFrame([new_p])], ignore_index=True)
                        save_poop_data(df_poop)
                        st.toast(f"[{target_past_str}] {p_kind} ({t_str}) 기록 추가 완료!", icon="✅")
                        st.rerun()
            else:
                with st.form(key=f"past_sleep_form_{child_name}"):
                    s_c1, s_c2 = st.columns(2)
                    with s_c1: s_start = st.time_input("수면 시작 시각", get_now_kst().time(), key=f"st_s_{child_name}")
                    with s_c2: s_end = st.time_input("수면 종료 시각", get_now_kst().time(), key=f"st_e_{child_name}")
                    if st.form_submit_button(f"➕ {target_past_str} 수면 기록 추가"):
                        t_start = datetime.combine(target_past_date, s_start)
                        t_end = datetime.combine(target_past_date, s_end)
                        if t_end < t_start: t_end = t_end.replace(day=t_end.day + 1)
                        duration_min = int((t_end - t_start).total_seconds() / 60)
                        new_s = {"날짜": target_past_str, "아동": child_name, "시작시간": s_start.strftime("%H:%M"), "종류": s_end.strftime("%H:%M"), "수면분": duration_min}
                        df_sleep = pd.concat([df_sleep, pd.DataFrame([new_s])], ignore_index=True)
                        save_sleep_data(df_sleep)
                        st.toast(f"[{target_past_str}] 😴 수면 {duration_min}분 기록 추가 완료!", icon="😴")
                        st.rerun()

        # TAB 2: 오늘 기록 삭제
        with tab2:
            st.caption("잘못 입력된 내역 옆의 삭제 버튼을 누르면 즉시 제거됩니다.")
            if len(today_poop_df) > 0:
                st.markdown("##### 📌 **오늘 배변 기록**")
                for p_idx, p_row in today_poop_df.iterrows():
                    d_c1, d_c2 = st.columns([3, 1])
                    with d_c1: st.write(f"- {p_row['종류']} ({p_row['시간']})")
                    with d_c2:
                        if st.button("🗑️ 삭제", key=f"del_poop_{child_name}_{p_idx}"):
                            df_poop = df_poop.drop(p_idx).reset_index(drop=True)
                            save_poop_data(df_poop)
                            st.toast("배변 기록 삭제 완료!")
                            st.rerun()

            if len(today_sleep_df) > 0:
                st.markdown("##### 📌 **오늘 수면 기록**")
                for s_idx, s_row in today_sleep_df.iterrows():
                    d_c1, d_c2 = st.columns([3, 1])
                    with d_c1:
                        if s_row["수면분"] == 0: st.write(f"- 😴 {s_row['시작시간']}부터 수면 진행 중")
                        else: st.write(f"- 😴 {s_row['시작시간']} ~ {s_row['종류']} ({s_row['수면분']}분)")
                    with d_c2:
                        if st.button("🗑️ 삭제", key=f"del_sleep_{child_name}_{s_idx}"):
                            df_sleep = df_sleep.drop(s_idx).reset_index(drop=True)
                            save_sleep_data(df_sleep)
                            st.toast("수면 기록 삭제 완료!")
                            st.rerun()

            if len(today_poop_df) == 0 and len(today_sleep_df) == 0:
                st.info("오늘 삭제할 배변/수면 내역이 없습니다.")

        # TAB 3: 과거/오늘 체중 & 수유 일괄 수정
        with tab3:
            edit_date = st.date_input("수정할 날짜 선택", get_now_kst().date(), key=f"edit_date_sel_{child_name}")
            edit_date_str = edit_date.strftime("%Y-%m-%d")
            
            # 해당 날짜 행 가져오기
            target_df = df_feeding[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == edit_date_str)]
            
            if len(target_df) == 0:
                target_w_val = weight
                target_row_dict = {}
            else:
                target_row_dict = target_df.iloc[0]
                target_w_val = float(target_row_dict["몸무게"]) if pd.notna(target_row_dict["몸무게"]) else weight

            with st.form(key=f"full_form_{child_name}"):
                st.write(f"📅 **[{edit_date_str}] 수유량 및 체중 수정**")
                new_weight = st.number_input("해당 날짜 몸무게 (kg)", value=target_w_val, step=0.05, format="%.2f", key=f"edit_w_{child_name}")
                feed_inputs = {}
                f_cols = st.columns(4)
                for i, col_name in enumerate(current_time_cols):
                    val = int(target_row_dict[col_name]) if col_name in target_row_dict and pd.notna(target_row_dict[col_name]) else 0
                    with f_cols[i % 4]: feed_inputs[col_name] = st.number_input(f"{col_name}", value=val, step=5, key=f"{child_name}_{edit_date_str}_{col_name}")
                
                if st.form_submit_button(f"💾 [{edit_date_str}] 데이터 저장"):
                    if len(target_df) == 0:
                        new_r = {"날짜": edit_date_str, "아동": child_name, "몸무게": new_weight}
                        for col in df_feeding.columns:
                            if col not in ["날짜", "아동", "몸무게"]: new_r[col] = feed_inputs.get(col, 0)
                        df_feeding = pd.concat([df_feeding, pd.DataFrame([new_r])], ignore_index=True)
                    else:
                        df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == edit_date_str), "몸무게"] = new_weight
                        for col_name, val in feed_inputs.items():
                            df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == edit_date_str), col_name] = val
                    
                    save_feeding_data(df_feeding)
                    st.toast(f"[{edit_date_str}] 데이터 저장 완료!")
                    st.rerun()

        st.divider()

        # --- 5. 수유량 추이 그래프 ---
        time_cols_in_df = [c for c in child_df.columns if c not in ["날짜", "아동", "몸무게", "몸무게_원본", "몸무게_보간", "추정여부"]]
        
        trend_records = []
        for _, r in child_df.iterrows():
            day_total = 0
            feed_count = 0
            details = []
            for tc in time_cols_in_df:
                if pd.notna(r[tc]) and int(r[tc]) > 0:
                    v = int(r[tc])
                    day_total += v
                    feed_count += 1
                    details.append(f"{tc}:{v}ml")
            
            w_val = float(r["몸무게_보간"])
            target_v = min(int(w_val * 180), 1000)
            detail_str = " / ".join(details) if details else "기록없음"
            avg_single_feed = round(day_total / feed_count) if feed_count > 0 else 0
            
            trend_records.append({
                "날짜": r["날짜"],
                "총수유량": day_total,
                "목표수유량": target_v,
                "평균1회수유량": avg_single_feed,
                "시간대별내역": detail_str
            })
            
        trend_df = pd.DataFrame(trend_records)

        fig_feed_trend = go.Figure()
        
        fig_feed_trend.add_trace(go.Bar(
            x=trend_df["날짜"], y=trend_df["총수유량"], name="총 수유량(ml)",
            marker_color="#2e7d32", 
            text=trend_df["총수유량"], 
            textposition="auto",
            textfont=dict(color="white", size=13, family="Arial Black"),
            customdata=list(zip(trend_df["시간대별내역"], trend_df["평균1회수유량"])),
            hovertemplate="<b>날짜</b>: %{x}<br><b>총 수유량</b>: %{y} ml<br><b>평균 1회 수유량</b>: %{customdata[1]} ml<br><b>시간대별</b>: %{customdata[0]}"
        ))
        
        fig_feed_trend.add_trace(go.Scatter(
            x=trend_df["날짜"], y=trend_df["목표수유량"], name="목표 기준(ml)",
            line=dict(color="#f57c00", width=2, dash="dash"),
            hovertemplate="<b>목표 기준</b>: %{y} ml"
        ))

        min_date = trend_df["날짜"].max()
        try: default_start = (datetime.strptime(min_date, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
        except: default_start = trend_df["날짜"].min()

        fig_feed_trend.update_layout(
            title=dict(text=f"<b>{child_name} 일자별 총 수유량 추이</b>", font=dict(size=16)),
            height=340, margin=dict(l=10, r=10, t=60, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
            xaxis=dict(
                range=[default_start, min_date],
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1개월", step="month", stepmode="backward"),
                        dict(count=3, label="3개월", step="month", stepmode="backward"),
                        dict(step="all", label="전체")
                    ]),
                    bgcolor="#262730", activecolor="#4caf50", y=1.12
                )
            ),
            yaxis=dict(title="총 수유량 (ml)")
        )
        st.plotly_chart(fig_feed_trend, use_container_width=True)

        # --- 체중 추이 그래프 ---
        fig_line = px.line(
            child_df, x="날짜", y="몸무게_보간", markers=True, 
            title=f"<b>{child_name} 일자별 체중 추이 (kg)</b>", height=300,
            hover_data={"추정여부": True, "몸무게_보간": ":.2f"}
        )
        fig_line.update_traces(
            hovertemplate="<b>날짜</b>: %{x}<br><b>몸무게</b>: %{y:.2f} kg %{customdata[0]}",
            line=dict(width=3, color="#3b82f6"), marker=dict(size=7)
        )
        w_min = child_df["몸무게_보간"].min() - 0.15
        w_max = child_df["몸무게_보간"].max() + 0.15
        fig_line.update_layout(
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis=dict(
                range=[default_start, min_date],
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1개월", step="month", stepmode="backward"),
                        dict(count=3, label="3개월", step="month", stepmode="backward"),
                        dict(step="all", label="전체")
                    ]),
                    bgcolor="#262730", activecolor="#3b82f6", y=1.12
                )
            ),
            yaxis=dict(title="체중 (kg)", range=[w_min, w_max])
        )
        st.plotly_chart(fig_line, use_container_width=True)

render_child_section("원빈", col_left)
render_child_section("현빈", col_right)

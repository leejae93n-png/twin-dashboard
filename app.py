import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os
from PIL import Image

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
        today_str = datetime.now().strftime("%Y-%m-%d")
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

def load_feeding_data():
    return pd.read_csv(FEEDING_FILE)

def load_poop_data():
    return pd.read_csv(POOP_FILE)

def load_sleep_data():
    return pd.read_csv(SLEEP_FILE)

def save_feeding_data(df):
    df.to_csv(FEEDING_FILE, index=False, encoding="utf-8-sig")

def save_poop_data(df):
    df.to_csv(POOP_FILE, index=False, encoding="utf-8-sig")

def save_sleep_data(df):
    df.to_csv(SLEEP_FILE, index=False, encoding="utf-8-sig")

st.title("👶 쌍둥이 이른둥이 맞춤 수유 & 성장 대시보드")

today_dt = date.today()
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
equal_ratio = 1.0 / len(current_time_cols)

st.sidebar.divider()
st.sidebar.header("💾 데이터 백업")
col_b1, col_b2, col_b3 = st.sidebar.columns(3)
with col_b1:
    st.download_button("📥 수유", df_feeding.to_csv(index=False, encoding="utf-8-sig"), f"feeding_{date.today()}.csv", "text/csv")
with col_b2:
    st.download_button("📥 배변", df_poop.to_csv(index=False, encoding="utf-8-sig"), f"poop_{date.today()}.csv", "text/csv")
with col_b3:
    st.download_button("📥 수면", df_sleep.to_csv(index=False, encoding="utf-8-sig"), f"sleep_{date.today()}.csv", "text/csv")

col_left, col_right = st.columns(2)

def render_child_section(child_name, container):
    global df_feeding, df_poop, df_sleep
    
    with container:
        # --- 프로필 영역 ---
        img_filename_png = f"profile_{child_name}.png"
        img_filename_jpg = f"profile_{child_name}.jpg"
        
        head_col1, head_col2 = st.columns([1, 3])
        with head_col1:
            if os.path.exists(img_filename_png):
                st.image(Image.open(img_filename_png), width=80)
            elif os.path.exists(img_filename_jpg):
                st.image(Image.open(img_filename_jpg), width=80)
            else:
                st.markdown("## 👶")
                
        with head_col2:
            st.header(f"이{child_name}")
            with st.expander("🖼️ 프로필 사진 변경", expanded=False):
                uploaded_file = st.file_uploader(f"{child_name} 사진 선택", type=["jpg", "png", "jpeg"], key=f"img_{child_name}")
                if uploaded_file is not None:
                    img = Image.open(uploaded_file)
                    img.save(img_filename_png)
                    st.toast("프로필 사진 저장 완료!", icon="🖼️")
                    st.rerun()

        today_str = datetime.now().strftime("%Y-%m-%d")
        child_df = df_feeding[df_feeding["아동"] == child_name].copy().sort_values(by="날짜").reset_index(drop=True)
        
        # 오늘 날짜 행 생성
        if today_str not in child_df["날짜"].values:
            last_weight = child_df["몸무게"].dropna().iloc[-1] if len(child_df["몸무게"].dropna()) > 0 else (3.5 if child_name == "원빈" else 4.1)
            new_row = {"날짜": today_str, "아동": child_name, "몸무게": last_weight}
            for col in df_feeding.columns:
                if col not in ["날짜", "아동", "몸무게"]:
                    new_row[col] = 0
            df_feeding = pd.concat([df_feeding, pd.DataFrame([new_row])], ignore_index=True)
            save_feeding_data(df_feeding)
            child_df = df_feeding[df_feeding["아동"] == child_name].copy().sort_values(by="날짜").reset_index(drop=True)

        # 체중 추정치(선형 보간) 로직
        child_df["몸무게_원본"] = child_df["몸무게"]
        child_df["몸무게_보간"] = child_df["몸무게"].interpolate(method="linear").bfill().ffill()
        child_df["추정여부"] = child_df["몸무게_원본"].isna().map({True: "(추정치)", False: ""})

        today_row = child_df[child_df["날짜"] == today_str].iloc[0]
        weight = float(today_row["몸무게_보간"])
        target_weight_for_next_step = 4.8
        
        # 체중 성장 예측 로직
        if len(child_df) >= 2:
            days_diff = len(child_df) - 1
            weight_diff = weight - float(child_df.iloc[0]["몸무게_보간"])
            daily_gain = (weight_diff / days_diff) if days_diff > 0 else 0.03
            if daily_gain <= 0: daily_gain = 0.02
        else:
            daily_gain = 0.03

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
        with k1:
            st.metric("체중 / 기준", f"{weight:.2f} kg", "1kg당 180ml")
        with k2:
            st.metric("현재 수유 달성", f"{actual_total} / {target_total} ml", f"{actual_total - target_total} ml")
        with k3:
            st.metric("오늘 배변/수면", f"💩{poop_cnt} 🟡{pee_cnt}", f"😴 {total_sleep_min//60}시간 {total_sleep_min%60}분")

        last_recorded_idx = 0
        for i, c in enumerate(current_time_cols):
            if c in today_row and pd.notna(today_row[c]) and int(today_row[c]) > 0:
                last_recorded_idx = i

        # --- 1. 빠른 수유량 입력 및 저장 ---
        st.markdown("---")
        st.subheader("🍼 수유량 입력 및 저장")
        
        q_c1, q_c2, q_c3 = st.columns([2, 2, 2])
        with q_c1:
            selected_slot = st.selectbox("수유 시간", current_time_cols, index=last_recorded_idx, key=f"q_slot_{child_name}")
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

        # --- 수유 타임라인 시각화 ---
        st.write("🕒 **오늘 수유 타임라인**")
        feed_badges = []
        for c in current_time_cols:
            v = int(today_row[c]) if c in today_row and pd.notna(today_row[c]) else 0
            if v > 0:
                feed_badges.append(
                    f'<span style="display:inline-block; background-color:#1e3a5f; border:1px solid #3b82f6; '
                    f'padding:3px 8px; margin:2px; border-radius:12px; font-size:13px; font-weight:bold;">'
                    f'🍼 {c}: {v}ml</span>'
                )
        if feed_badges:
            st.markdown("".join(feed_badges), unsafe_allow_html=True)
        else:
            st.caption("오늘 기록된 수유 내역이 없습니다.")

        # --- 2. 빠른 배변 및 수면 기록 ---
        st.subheader("💩 배변 & 😴 수면 기록")
        p_btn1, p_btn2 = st.columns(2)
        with p_btn1:
            if st.button(f"💩 대변 기록", key=f"quick_poop_{child_name}", use_container_width=True):
                now_str = datetime.now().strftime("%H:%M")
                new_poop = {"날짜": today_str, "아동": child_name, "시간": now_str, "종류": "대변"}
                df_poop = pd.concat([df_poop, pd.DataFrame([new_poop])], ignore_index=True)
                save_poop_data(df_poop)
                st.toast(f"💩 {child_name} 대변 ({now_str}) 기록 완료!", icon="💩")
                st.rerun()
        with p_btn2:
            if st.button(f"🟡 소변 기록", key=f"quick_pee_{child_name}", use_container_width=True):
                now_str = datetime.now().strftime("%H:%M")
                new_poop = {"날짜": today_str, "아동": child_name, "시간": now_str, "종류": "소변"}
                df_poop = pd.concat([df_poop, pd.DataFrame([new_poop])], ignore_index=True)
                save_poop_data(df_poop)
                st.toast(f"🟡 {child_name} 소변 ({now_str}) 기록 완료!", icon="🟡")
                st.rerun()

        # 수면 기록 폼
        with st.expander("😴 수면 시간 세부 기록", expanded=False):
            with st.form(key=f"sleep_form_{child_name}"):
                s_col1, s_col2 = st.columns(2)
                with s_col1:
                    sleep_start = st.time_input("수면 시작 시간", datetime.now().time())
                with s_col2:
                    sleep_end = st.time_input("수면 종료 시간", datetime.now().time())
                
                if st.form_submit_button("💾 수면 기록 저장"):
                    t_start = datetime.combine(date.today(), sleep_start)
                    t_end = datetime.combine(date.today(), sleep_end)
                    if t_end < t_start: # 자정을 넘긴 수면
                        t_end = t_end.replace(day=t_end.day + 1)
                    duration_min = int((t_end - t_start).total_seconds() / 60)
                    
                    new_sleep = {
                        "날짜": today_str, "아동": child_name, 
                        "시작시간": sleep_start.strftime("%H:%M"), 
                        "종류": sleep_end.strftime("%H:%M"), 
                        "수면분": duration_min
                    }
                    df_sleep = pd.concat([df_sleep, pd.DataFrame([new_sleep])], ignore_index=True)
                    save_sleep_data(df_sleep)
                    st.toast(f"😴 {child_name} 수면 {duration_min}분 기록 완료!", icon="😴")
                    st.rerun()

        # --- 배변 및 수면 내역 삭제/수정 관리 메뉴 (신규 추가) ---
        with st.expander("🛠️ 배변 & 수면 기록 관리 (삭제/수정)", expanded=False):
            st.caption("잘못 입력된 배변 또는 수면 내역을 삭제할 수 있습니다.")
            
            # 배변 삭제
            if len(today_poop_df) > 0:
                st.write("📌 **오늘 배변 내역**")
                for p_idx, p_row in today_poop_df.iterrows():
                    del_col1, del_col2 = st.columns([3, 1])
                    with del_col1:
                        st.write(f"- {p_row['종류']} ({p_row['시간']})")
                    with del_col2:
                        if st.button("🗑️ 삭제", key=f"del_poop_{p_idx}"):
                            df_poop = df_poop.drop(p_idx).reset_index(drop=True)
                            save_poop_data(df_poop)
                            st.toast("배변 내역이 삭제되었습니다.")
                            st.rerun()
            
            # 수면 삭제
            if len(today_sleep_df) > 0:
                st.write("📌 **오늘 수면 내역**")
                for s_idx, s_row in today_sleep_df.iterrows():
                    del_col1, del_col2 = st.columns([3, 1])
                    with del_col1:
                        st.write(f"- 수면: {s_row['시작시간']} ~ {s_row['종류']} ({s_row['수면분']}분)")
                    with del_col2:
                        if st.button("🗑️ 삭제", key=f"del_sleep_{s_idx}"):
                            df_sleep = df_sleep.drop(s_idx).reset_index(drop=True)
                            save_sleep_data(df_sleep)
                            st.toast("수면 내역이 삭제되었습니다.")
                            st.rerun()

        # 배변 & 수면 타임라인
        st.write("🕒 **오늘 배변/수면 타임라인**")
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
                combined_badges.append(
                    f'<span style="display:inline-block; background-color:#1c2d37; border:1px solid #0284c7; '
                    f'padding:3px 8px; margin:2px; border-radius:12px; font-size:13px; font-weight:bold;">'
                    f'😴 {r["시작시간"]}~{r["종류"]} ({r["수면분"]}분)</span>'
                )

        if combined_badges:
            st.markdown("".join(combined_badges), unsafe_allow_html=True)
        else:
            st.caption("오늘 기록된 배변 및 수면 내역이 없습니다.")

        # --- 상세 일괄 수정 ---
        with st.expander("⚙️ 오늘 체중 및 전체 수유표 일괄 수정", expanded=False):
            with st.form(key=f"full_form_{child_name}"):
                new_weight = st.number_input("오늘 몸무게 (kg)", value=weight, step=0.05, format="%.2f")
                feed_inputs = {}
                f_cols = st.columns(4)
                for i, col_name in enumerate(current_time_cols):
                    val = int(today_row[col_name]) if col_name in today_row and pd.notna(today_row[col_name]) else 0
                    with f_cols[i % 4]:
                        feed_inputs[col_name] = st.number_input(
                            f"{col_name}", value=val, step=5, key=f"{child_name}_{col_name}"
                        )
                if st.form_submit_button("💾 전체 체중/수유 데이터 일괄 저장"):
                    df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == today_str), "몸무게"] = new_weight
                    for col_name, val in feed_inputs.items():
                        df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == today_str), col_name] = val
                    save_feeding_data(df_feeding)
                    st.toast("체중 및 수유 데이터가 전체 저장되었습니다!")
                    st.rerun()

        st.divider()

        # --- 그래프 (체중 추정치 선형 보간 반영) ---
        comp_list = []
        for c in current_time_cols:
            val = int(today_row[c]) if c in today_row and pd.notna(today_row[c]) else 0
            comp_list.append({"시간대": c, "목표": round(target_total * equal_ratio), "실제": val})
        
        comp_df = pd.DataFrame(comp_list)
        fig_bar = px.bar(comp_df, x="시간대", y=["목표", "실제"], barmode="group",
                         title=f"{child_name} 시간대별 수유량 (ml)", 
                         color_discrete_sequence=["#90caf9", "#4caf50"], height=280,
                         text_auto=True)
        fig_bar.update_yaxes(range=[30, max(comp_df["실제"].max(), comp_df["목표"].max()) + 25])
        st.plotly_chart(fig_bar, use_container_width=True)

        # 보간 체중 추이 그래프
        fig_line = px.line(
            child_df, x="날짜", y="몸무게_보간", markers=True, 
            title=f"{child_name} 일자별 체중 추이 (kg) - *누락일 추정치 자동 연결*", height=280,
            hover_data={"추정여부": True, "몸무게_보간": ":.2f"}
        )
        fig_line.update_traces(
            hovertemplate="<b>날짜</b>: %{x}<br><b>몸무게</b>: %{y:.2f} kg %{customdata[0]}",
            line=dict(width=3),
            marker=dict(size=7)
        )
        w_min = child_df["몸무게_보간"].min() - 0.15
        w_max = child_df["몸무게_보간"].max() + 0.15
        fig_line.update_yaxes(range=[w_min, w_max])
        st.plotly_chart(fig_line, use_container_width=True)

render_child_section("원빈", col_left)
render_child_section("현빈", col_right)

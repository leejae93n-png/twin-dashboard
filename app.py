import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os
from PIL import Image

st.set_page_config(page_title="쌍둥이 통합 수유 & 성장 대시보드", layout="wide")

FEEDING_FILE = "twin_feeding_data.csv"
POOP_FILE = "twin_poop_data.csv"

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

init_data()

def load_feeding_data():
    return pd.read_csv(FEEDING_FILE)

def load_poop_data():
    return pd.read_csv(POOP_FILE)

def save_feeding_data(df):
    df.to_csv(FEEDING_FILE, index=False, encoding="utf-8-sig")

def save_poop_data(df):
    df.to_csv(POOP_FILE, index=False, encoding="utf-8-sig")

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

st.sidebar.header("⚙️ 수유 스케줄 설정")
selected_schedule_key = st.sidebar.selectbox("현재 적용할 수유 패턴", list(SCHEDULE_OPTIONS.keys()), index=0)
current_time_cols = SCHEDULE_OPTIONS[selected_schedule_key]
equal_ratio = 1.0 / len(current_time_cols)

col_left, col_right = st.columns(2)

def render_child_section(child_name, container):
    global df_feeding, df_poop
    
    with container:
        # --- 프로필 사진 영역 ---
        img_filename = f"profile_{child_name}.png"
        head_col1, head_col2 = st.columns([1, 4])
        
        with head_col1:
            if os.path.exists(img_filename):
                image = Image.open(img_filename)
                st.image(image, width=90)
            else:
                st.markdown("👶")
                
        with head_col2:
            st.header(f"이{child_name}")
            with st.expander("🖼️ 프로필 사진 등록/변경", expanded=False):
                uploaded_file = st.file_uploader(f"{child_name} 사진 선택", type=["jpg", "png", "jpeg"], key=f"img_{child_name}")
                if uploaded_file is not None:
                    img = Image.open(uploaded_file)
                    img.save(img_filename)
                    st.success("사진 저장 완료!")
                    st.rerun()

        today_str = datetime.now().strftime("%Y-%m-%d")
        child_df = df_feeding[df_feeding["아동"] == child_name].copy().sort_values(by="날짜").reset_index(drop=True)
        
        if today_str not in child_df["날짜"].values:
            last_weight = child_df["몸무게"].iloc[-1] if len(child_df) > 0 else (3.5 if child_name == "원빈" else 4.1)
            new_row = {"날짜": today_str, "아동": child_name, "몸무게": last_weight}
            for col in df_feeding.columns:
                if col not in ["날짜", "아동", "몸무게"]:
                    new_row[col] = 0
            df_feeding = pd.concat([df_feeding, pd.DataFrame([new_row])], ignore_index=True)
            save_feeding_data(df_feeding)
            child_df = df_feeding[df_feeding["아동"] == child_name].copy().sort_values(by="날짜").reset_index(drop=True)

        today_idx = child_df[child_df["날짜"] == today_str].index[0]
        today_row = child_df.loc[today_idx]

        weight = float(today_row["몸무게"])
        target_weight_for_next_step = 4.8
        
        if len(child_df) >= 2:
            days_diff = len(child_df) - 1
            weight_diff = weight - float(child_df.iloc[0]["몸무게"])
            daily_gain = (weight_diff / days_diff) if days_diff > 0 else 0.03
        else:
            daily_gain = 0.03

        if weight < target_weight_for_next_step and daily_gain > 0:
            days_left = int((target_weight_for_next_step - weight) / daily_gain)
            predict_msg = f"💡 현재 성장 속도(일 {daily_gain*1000:.0f}g) 기준, **약 {days_left}일 후({target_weight_for_next_step}kg 도달 시)** 수유 텀 연장(일 7회) 권장"
        else:
            predict_msg = "💡 체중 4.8kg 이상 도달! 수유 텀 연장(일 6~7회) 가능"

        st.caption(predict_msg)

        today_poop_df = df_poop[(df_poop["아동"] == child_name) & (df_poop["날짜"] == today_str)]
        poop_cnt = len(today_poop_df[today_poop_df["종류"] == "대변"])
        pee_cnt = len(today_poop_df[today_poop_df["종류"] == "소변"])

        target_total = min(int(weight * 180), 1000)
        actual_total = sum([int(today_row[c]) for c in current_time_cols if c in today_row])

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("체중 / 목표기준", f"{weight:.2f} kg", "1kg당 180ml")
        with k2:
            st.metric("현재 수유 달성", f"{actual_total} ml / {target_total} ml", f"{actual_total - target_total} ml")
        with k3:
            st.metric("오늘 배변 현황", f"💩 {poop_cnt}회 / 🟡 {pee_cnt}회")

        # 마지막 입력된 수유 시간 자동 감지
        last_recorded_idx = 0
        for i, c in enumerate(current_time_cols):
            if c in today_row and int(today_row[c]) > 0:
                last_recorded_idx = i

        t1, t2 = st.columns([1, 1])
        with t1:
            last_fed = st.selectbox(
                "마지막 수유", 
                current_time_cols, 
                index=last_recorded_idx,
                key=f"{child_name}_last_fed"
            )
        with t2:
            idx = current_time_cols.index(last_fed)
            next_fed = current_time_cols[(idx + 1) % len(current_time_cols)]
            st.info(f"💡 다음: **[{next_fed}]**")

        with st.expander("📝 수유량 & 체중 입력", expanded=False):
            with st.form(key=f"feed_form_{child_name}"):
                new_weight = st.number_input("오늘 몸무게 (kg)", value=weight, step=0.05, format="%.2f")
                feed_inputs = {}
                f_cols = st.columns(4)
                for i, col_name in enumerate(current_time_cols):
                    val = int(today_row[col_name]) if col_name in today_row else 0
                    with f_cols[i % 4]:
                        feed_inputs[col_name] = st.number_input(
                            f"{col_name}", value=val, step=5, key=f"{child_name}_{col_name}"
                        )
                if st.form_submit_button("💾 수유 데이터 저장"):
                    df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == today_str), "몸무게"] = new_weight
                    for col_name, val in feed_inputs.items():
                        df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == today_str), col_name] = val
                    save_feeding_data(df_feeding)
                    st.success("저장 완료!")
                    st.rerun()

        with st.expander("💩 배변 시간 기록하기", expanded=False):
            with st.form(key=f"poop_form_{child_name}"):
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    poop_type = st.radio("종류", ["소변", "대변"], horizontal=True)
                with p_col2:
                    poop_time = st.time_input("발생 시간", datetime.now().time())
                
                if st.form_submit_button("➕ 배변 기록 추가"):
                    time_str = poop_time.strftime("%H:%M")
                    new_poop_row = {"날짜": today_str, "아동": child_name, "시간": time_str, "종류": poop_type}
                    df_poop = pd.concat([df_poop, pd.DataFrame([new_poop_row])], ignore_index=True)
                    save_poop_data(df_poop)
                    st.success(f"{poop_type} ({time_str}) 기록 완료!")
                    st.rerun()

        st.write("🕒 **오늘 배변 타임라인**")
        if len(today_poop_df) > 0:
            sorted_poop = today_poop_df.sort_values(by="시간")
            badges_html = []
            for _, r in sorted_poop.iterrows():
                icon = "💩" if r["종류"] == "대변" else "🟡"
                bg_color = "#3d2b1f" if r["종류"] == "대변" else "#3a351e"
                border_color = "#8d5b28" if r["종류"] == "대변" else "#8c7b27"
                badges_html.append(
                    f'<span style="display:inline-block; background-color:{bg_color}; border:1px solid {border_color}; '
                    f'padding:4px 10px; margin:3px; border-radius:15px; font-size:15px; font-weight:bold;">'
                    f'{icon} {r["시간"]}</span>'
                )
            st.markdown("".join(badges_html), unsafe_allow_html=True)
        else:
            st.caption("기록된 배변 내역이 없습니다.")

        st.divider()

        comp_list = []
        for c in current_time_cols:
            val = int(today_row[c]) if c in today_row else 0
            comp_list.append({"시간대": c, "목표": round(target_total * equal_ratio), "실제": val})
        
        comp_df = pd.DataFrame(comp_list)
        fig_bar = px.bar(comp_df, x="시간대", y=["목표", "실제"], barmode="group",
                         title=f"{child_name} 시간대별 수유량 (ml)", 
                         color_discrete_sequence=["#90caf9", "#4caf50"], height=300,
                         text_auto=True)
        fig_bar.update_yaxes(range=[30, max(comp_df["실제"].max(), comp_df["목표"].max()) + 25])
        st.plotly_chart(fig_bar, use_container_width=True)

        fig_line = px.line(
            child_df, x="날짜", y="몸무게", markers=True, 
            title=f"{child_name} 일자별 체중 추이 (kg)", height=280
        )
        fig_line.update_traces(
            hovertemplate="<b>날짜</b>: %{x}<br><b>몸무게</b>: %{y:.2f} kg",
            line=dict(width=3),
            marker=dict(size=7)
        )
        w_min = child_df["몸무게"].min() - 0.15
        w_max = child_df["몸무게"].max() + 0.15
        fig_line.update_yaxes(range=[w_min, w_max])
        st.plotly_chart(fig_line, use_container_width=True)

render_child_section("원빈", col_left)
render_child_section("현빈", col_right)
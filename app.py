import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta, timezone
import os
from PIL import Image

KST = timezone(timedelta(hours=9))
def get_now_kst(): return datetime.now(KST)

st.set_page_config(page_title="쌍둥이 이른둥이 맞춤 수유 & 성장 대시보드", layout="wide")

BIRTH_DATE = date(2026, 5, 14)
DUE_DATE = date(2026, 8, 12)

SCHEDULE_OPTIONS = {
    "일 8회 (3시간 텀)": ["01:00", "04:00", "07:00", "10:00", "13:00", "16:00", "19:00", "22:00"],
    "일 7회 (3.5시간 텀)": ["01:00", "04:30", "08:00", "11:30", "15:00", "18:30", "22:00"],
    "일 6회 (4시간 텀)": ["02:00", "06:00", "10:00", "14:00", "18:00", "22:00"],
    "일 5회 (4.5시간 텀)": ["06:00", "10:30", "15:00", "19:30", "23:00"]
}

GAS_URL = st.secrets.get("GAS_URL", "").strip()

def parse_clean_date(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    v = str(val).strip().split("T")[0].split(" ")[0]
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except:
        return v

def load_data_from_gas(sheet_name):
    if not GAS_URL: return pd.DataFrame()
    try:
        timestamp = int(time.time() * 1000)
        res = requests.get(f"{GAS_URL}?sheet={sheet_name}&_t={timestamp}", timeout=35, allow_redirects=True)
        if res.status_code != 200: return pd.DataFrame()
        data = res.json()
        if not data or len(data) <= 1: return pd.DataFrame()
        
        raw_columns = [str(c).strip() for c in data[0]]
        seen = {}
        unique_columns = []
        for col in raw_columns:
            if col in seen:
                seen[col] += 1
                unique_columns.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 0
                unique_columns.append(col)
                
        df = pd.DataFrame(data[1:], columns=unique_columns)
        if "날짜" in df.columns:
            df["날짜"] = df["날짜"].apply(parse_clean_date)
            df = df[df["날짜"] != ""]
        if "아동" in df.columns:
            df["아동"] = df["아동"].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"❌ 구글 시트 연동 오류 [{sheet_name}]: {e}")
        return pd.DataFrame()

def save_data_to_gas(sheet_name, df):
    if not GAS_URL: return
    try:
        df_clean = df.fillna("")
        rows = [df_clean.columns.tolist()] + df_clean.values.tolist()
        payload = {"sheet": sheet_name, "rows": rows}
        headers = {'Content-Type': 'application/json'}
        res = requests.post(GAS_URL, data=json.dumps(payload), headers=headers, timeout=35, allow_redirects=True)
        if res.status_code == 200:
            st.toast(f"✅ [{sheet_name}] 구글 시트에 실시간 반영되었습니다!", icon="💾")
    except Exception as e:
        st.error(f"❌ 구글 시트 저장 연동 오류: {e}")

def load_feeding_data():
    df = load_data_from_gas("Feeding")
    cols = ["날짜", "아동", "시간", "수유량", "몸무게"]
    if df.empty: return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns: df[c] = ""
    return df

def load_poop_data():
    df = load_data_from_gas("Poop")
    cols = ["날짜", "아동", "시간", "종류"]
    return df if not df.empty else pd.DataFrame(columns=cols)

def load_sleep_data():
    df = load_data_from_gas("Sleep")
    cols = ["날짜", "아동", "시작시간", "종류", "수면분"]
    return df if not df.empty else pd.DataFrame(columns=cols)

def save_feeding_data(df): save_data_to_gas("Feeding", df)
def save_poop_data(df): save_data_to_gas("Poop", df)
def save_sleep_data(df): save_data_to_gas("Sleep", df)

st.title("👶 쌍둥이 이른둥이 맞춤 수유 & 성장 대시보드")

today_dt = get_now_kst().date()
chronological_days = (today_dt - BIRTH_DATE).days
corrected_days = (today_dt - DUE_DATE).days

header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.info(
        f"🍼 **성장 기준일 안내** (오늘: {today_dt.strftime('%Y-%m-%d')}) | "
        f"**출생일령**: 생후 **{chronological_days}일차** | "
        f"**교정일령**: 교정 **{corrected_days}일차**"
    )
with header_col2:
    if st.button("🔄 최신 데이터 동기화", use_container_width=True):
        st.rerun()

df_feeding = load_feeding_data()
df_poop = load_poop_data()
df_sleep = load_sleep_data()

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

def get_closest_slot(time_slots, now_time):
    now_min = now_time.hour * 60 + now_time.minute
    min_diff = 9999
    best_slot_idx = 0
    for idx, slot in enumerate(time_slots):
        sh, sm = map(int, slot.split(":"))
        slot_min = sh * 60 + sm
        diff = abs(now_min - slot_min)
        if diff < min_diff:
            min_diff = diff
            best_slot_idx = idx
    return best_slot_idx

def render_child_section(child_name, container):
    global df_feeding, df_poop, df_sleep
    
    with container:
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

        today_str = get_now_kst().strftime("%Y-%m-%d")
        
        child_feed_all = df_feeding[df_feeding["아동"] == child_name].copy() if not df_feeding.empty and "아동" in df_feeding.columns else pd.DataFrame()
        child_feed_all["수유량_num"] = pd.to_numeric(child_feed_all["수유량"], errors="coerce").fillna(0)
        child_feed_all["몸무게_num"] = pd.to_numeric(child_feed_all["몸무게"], errors="coerce")

        default_base_weight = 3.9 if child_name == "원빈" else 4.1
        
        # 오늘 체중 확인
        today_f = child_feed_all[child_feed_all["날짜"] == today_str]
        today_w_valid = today_f["몸무게_num"].dropna()
        if not today_w_valid.empty and today_w_valid.iloc[-1] > 0:
            weight = float(today_w_valid.iloc[-1])
        else:
            all_w_valid = child_feed_all["몸무게_num"].dropna()
            weight = float(all_w_valid.iloc[-1]) if not all_w_valid.empty and all_w_valid.iloc[-1] > 0 else default_base_weight

        today_poop_df = df_poop[(df_poop["아동"] == child_name) & (df_poop["날짜"] == today_str)] if not df_poop.empty and "아동" in df_poop.columns else pd.DataFrame()
        poop_cnt = len(today_poop_df[today_poop_df["종류"] == "대변"]) if not today_poop_df.empty else 0
        pee_cnt = len(today_poop_df[today_poop_df["종류"] == "소변"]) if not today_poop_df.empty else 0

        today_sleep_df = df_sleep[(df_sleep["아동"] == child_name) & (df_sleep["날짜"] == today_str)] if not df_sleep.empty and "아동" in df_sleep.columns else pd.DataFrame()
        total_sleep_min = pd.to_numeric(today_sleep_df["수면분"], errors="coerce").fillna(0).sum() if not today_sleep_df.empty else 0

        target_total = min(int(weight * 180), 1000)
        actual_total = int(today_f["수유량_num"].sum()) if not today_f.empty else 0

        k1, k2, k3 = st.columns([1.1, 1.3, 1.2])
        with k1: st.metric("체중 / 기준", f"{weight:.2f} kg", "1kg당 180ml")
        with k2: st.metric("현재 수유 달성", f"{actual_total} / {target_total} ml", f"{actual_total - target_total} ml")
        with k3: st.metric("오늘 배변/수면", f"💩{poop_cnt} 🟡{pee_cnt}", f"😴 {int(total_sleep_min)//60}시간 {int(total_sleep_min)%60}분")

        closest_slot_idx = get_closest_slot(current_time_cols, get_now_kst().time())

        # --- 실시간 1초 원클릭 기록 ---
        st.subheader("⚡ 실시간 1초 원클릭 기록 (현재시간)")
        auto_slot = current_time_cols[closest_slot_idx]
        
        feed_col1, feed_col2, btn_c2, btn_c3, btn_c4 = st.columns([1.2, 1.8, 1, 1, 1])
        with feed_col1:
            now_feed_val = st.number_input("수유량 (ml)", value=100, step=5, key=f"now_val_{child_name}", label_visibility="collapsed")
        with feed_col2:
            if st.button(f"🍼 수유 [{auto_slot}] 기록", key=f"now_feed_{child_name}", type="primary", use_container_width=True):
                new_feed = {"날짜": today_str, "아동": child_name, "시간": auto_slot, "수유량": now_feed_val, "몸무게": weight}
                df_feeding = pd.concat([df_feeding, pd.DataFrame([new_feed])], ignore_index=True)
                save_feeding_data(df_feeding)
                st.rerun()

        with btn_c2:
            if st.button(f"💩 대변 (지금)", key=f"now_poop_{child_name}", use_container_width=True):
                now_str = get_now_kst().strftime("%H:%M")
                new_poop = {"날짜": today_str, "아동": child_name, "시간": now_str, "종류": "대변"}
                df_poop = pd.concat([df_poop, pd.DataFrame([new_poop])], ignore_index=True)
                save_poop_data(df_poop)
                st.rerun()

        with btn_c3:
            if st.button(f"🟡 소변 (지금)", key=f"now_pee_{child_name}", use_container_width=True):
                now_str = get_now_kst().strftime("%H:%M")
                new_poop = {"날짜": today_str, "아동": child_name, "시간": now_str, "종류": "소변"}
                df_poop = pd.concat([df_poop, pd.DataFrame([new_poop])], ignore_index=True)
                save_poop_data(df_poop)
                st.rerun()

        with btn_c4:
            sleeping_row = df_sleep[(df_sleep["아동"] == child_name) & (df_sleep["날짜"] == today_str) & (df_sleep["수면분"].astype(str) == "0")] if not df_sleep.empty and "아동" in df_sleep.columns else pd.DataFrame()
            if len(sleeping_row) == 0:
                if st.button(f"😴 잠들었음", key=f"sleep_start_{child_name}", use_container_width=True):
                    now_str = get_now_kst().strftime("%H:%M")
                    new_sleep = {"날짜": today_str, "아동": child_name, "시작시간": now_str, "종류": "수면중", "수면분": 0}
                    df_sleep = pd.concat([df_sleep, pd.DataFrame([new_sleep])], ignore_index=True)
                    save_sleep_data(df_sleep)
                    st.rerun()
            else:
                if st.button(f"⏰ 깨어났음", key=f"sleep_end_{child_name}", type="primary", use_container_width=True):
                    now_dt = get_now_kst()
                    start_str = sleeping_row.iloc[-1]["시작시간"]
                    start_dt = datetime.strptime(f"{today_str} {start_str}", "%Y-%m-%d %H:%M").replace(tzinfo=KST)
                    duration_min = int((now_dt - start_dt).total_seconds() / 60)
                    target_idx = sleeping_row.index[-1]
                    df_sleep.loc[target_idx, "종류"] = now_dt.strftime("%H:%M")
                    df_sleep.loc[target_idx, "수면분"] = max(duration_min, 1)
                    save_sleep_data(df_sleep)
                    st.rerun()

        # --- 날짜별 통합 기록 조회 및 수정 센터 ---
        st.markdown("---")
        with st.expander("📅 날짜별 통합 기록 조회 및 수정 센터 (클릭하여 열기)", expanded=False):
            sel_date = st.date_input("조회 및 수정할 날짜 선택", get_now_kst().date(), key=f"m_date_{child_name}")
            sel_date_str = sel_date.strftime("%Y-%m-%d")
            
            st.markdown(f"#### 🔍 **[{sel_date_str}] {child_name} 기록 상태**")
            
            sel_feed_df = df_feeding[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == sel_date_str)] if not df_feeding.empty and "아동" in df_feeding.columns else pd.DataFrame()
            p_df_sel = df_poop[(df_poop["아동"] == child_name) & (df_poop["날짜"] == sel_date_str)] if not df_poop.empty and "아동" in df_poop.columns else pd.DataFrame()
            s_df_sel = df_sleep[(df_sleep["아동"] == child_name) & (df_sleep["날짜"] == sel_date_str)] if not df_sleep.empty and "아동" in df_sleep.columns else pd.DataFrame()

            f_col_s, p_col_s, s_col_s = st.columns(3)
            with f_col_s:
                st.write("🍼 **수유 내역 (삭제 가능)**")
                if len(sel_feed_df) > 0:
                    for f_idx, f_r in sel_feed_df.iterrows():
                        c_a, c_b = st.columns([3, 1])
                        with c_a: st.write(f"- {f_r['시간']} : {f_r['수유량']}ml")
                        with c_b:
                            if st.button("🗑️", key=f"del_f_{child_name}_{f_idx}"):
                                df_feeding = df_feeding.drop(f_idx).reset_index(drop=True)
                                save_feeding_data(df_feeding)
                                st.rerun()
                else: st.caption("수유 기록 없음")

            with p_col_s:
                st.write("📌 **배변 내역 (삭제 가능)**")
                if len(p_df_sel) > 0:
                    for p_idx, p_r in p_df_sel.iterrows():
                        c_a, c_b = st.columns([3, 1])
                        with c_a: st.write(f"- {p_r['종류']} ({p_r['시간']})")
                        with c_b:
                            if st.button("🗑️", key=f"del_p_{child_name}_{p_idx}"):
                                df_poop = df_poop.drop(p_idx).reset_index(drop=True)
                                save_poop_data(df_poop)
                                st.rerun()
                else: st.caption("배변 기록 없음")

            with s_col_s:
                st.write("📌 **수면 내역 (삭제 가능)**")
                if len(s_df_sel) > 0:
                    for s_idx, s_r in s_df_sel.iterrows():
                        c_a, c_b = st.columns([3, 1])
                        with c_a:
                            if str(s_r["수면분"]) == "0": st.write(f"- 😴 {s_r['시작시간']}~진행중")
                            else: st.write(f"- 😴 {s_r['시작시간']}~{s_r['종류']} ({s_r['수면분']}분)")
                        with c_b:
                            if st.button("🗑️", key=f"del_s_{child_name}_{s_idx}"):
                                df_sleep = df_sleep.drop(s_idx).reset_index(drop=True)
                                save_sleep_data(df_sleep)
                                st.rerun()
                else: st.caption("수면 기록 없음")

            st.divider()
            
            with st.form(key=f"m_add_feed_{child_name}_{sel_date_str}"):
                st.write("➕ **수유 기록 추가**")
                fa1, fa2, fa3 = st.columns(3)
                with fa1: ft_in = st.time_input("수유 시각", get_now_kst().time(), key=f"mft_{child_name}_{sel_date_str}")
                with fa2: fv_in = st.number_input("수유량 (ml)", value=100, step=5, key=f"mfv_{child_name}_{sel_date_str}")
                with fa3: fw_in = st.number_input("체중 (kg)", value=weight, step=0.05, format="%.2f", key=f"mfw_{child_name}_{sel_date_str}")
                if st.form_submit_button("➕ 수유 추가하기"):
                    new_f = {"날짜": sel_date_str, "아동": child_name, "시간": ft_in.strftime("%H:%M"), "수유량": fv_in, "몸무게": fw_in}
                    df_feeding = pd.concat([df_feeding, pd.DataFrame([new_f])], ignore_index=True)
                    save_feeding_data(df_feeding)
                    st.rerun()

        st.divider()

        # --- 그래프 조회 기간 선택 ---
        daily_summary = []
        if not child_feed_all.empty:
            for d_str, group in child_feed_all.groupby("날짜"):
                tot_amt = int(group["수유량_num"].sum())
                w_vals = group["몸무게_num"].dropna()
                w_val = float(w_vals.iloc[-1]) if not w_vals.empty and w_vals.iloc[-1] > 0 else weight
                target_v = min(int(w_val * 180), 1000)
                feed_cnt = len(group[group["수유량_num"] > 0])
                avg_amt = round(tot_amt / feed_cnt) if feed_cnt > 0 else 0
                
                details = []
                for _, r in group.sort_values(by="시간").iterrows():
                    details.append(f"{r['시간']}:{r['수유량']}ml")
                detail_str = " / ".join(details) if details else "기록없음"
                
                daily_summary.append({
                    "날짜": d_str,
                    "총수유량": tot_amt,
                    "목표수유량": target_v,
                    "평균1회수유량": avg_amt,
                    "체중": w_val,
                    "시간대별내역": detail_str
                })
                
        trend_df = pd.DataFrame(daily_summary).sort_values(by="날짜") if daily_summary else pd.DataFrame(columns=["날짜", "총수유량", "목표수유량", "평균1회수유량", "체중", "시간대별내역"])
        all_dates = list(trend_df["날짜"].unique()) if not trend_df.empty else [today_str]

        period_option = st.radio(
            f"📊 **{child_name} 그래프 조회 기간**",
            ["전체", "최근 1개월 (30일)", "최근 2주 (14일)", "최근 1주 (7일)"],
            horizontal=True,
            key=f"period_range_{child_name}"
        )

        total_len = len(all_dates)
        if period_option == "최근 1주 (7일)": start_idx = max(0, total_len - 7)
        elif period_option == "최근 2주 (14일)": start_idx = max(0, total_len - 14)
        elif period_option == "최근 1개월 (30일)": start_idx = max(0, total_len - 30)
        else: start_idx = 0

        # 수유량 추이 그래프
        fig_feed_trend = go.Figure()
        if not trend_df.empty:
            fig_feed_trend.add_trace(go.Bar(
                x=trend_df["날짜"], y=trend_df["총수유량"], name="총 수유량(ml)",
                marker_color="#2e7d32", text=trend_df["총수유량"], textposition="auto",
                textfont=dict(color="white", size=13, family="Arial Black"),
                customdata=list(zip(trend_df["시간대별내역"], trend_df["평균1회수유량"])),
                hovertemplate="<b>날짜</b>: %{x}<br><b>총 수유량</b>: %{y} ml<br><b>평균 1회</b>: %{customdata[1]} ml<br><b>내역</b>: %{customdata[0]}"
            ))
            fig_feed_trend.add_trace(go.Scatter(
                x=trend_df["날짜"], y=trend_df["목표수유량"], name="목표 기준(ml)",
                line=dict(color="#f57c00", width=2, dash="dash"),
                hovertemplate="<b>목표 기준</b>: %{y} ml"
            ))

        fig_feed_trend.update_layout(
            title=dict(text=f"<b>{child_name} 일자별 총 수유량 추이</b>", font=dict(size=16), y=0.98, x=0.01, xanchor="left"),
            height=360, margin=dict(l=10, r=10, t=80, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(type="category", categoryorder="category ascending", range=[start_idx - 0.5, total_len - 0.5], autorange=False),
            yaxis=dict(title="총 수유량 (ml)")
        )
        st.plotly_chart(fig_feed_trend, use_container_width=True)

        # 체중 추이 그래프
        fig_line = go.Figure()
        if not trend_df.empty:
            fig_line.add_trace(go.Scatter(
                x=trend_df["날짜"], y=trend_df["체중"], mode="lines+markers",
                line=dict(width=3, color="#3b82f6"), marker=dict(size=7),
                hovertemplate="<b>날짜</b>: %{x}<br><b>몸무게</b>: %{y:.2f} kg"
            ))
        w_min = trend_df["체중"].min() - 0.15 if not trend_df.empty else 3.0
        w_max = trend_df["체중"].max() + 0.15 if not trend_df.empty else 5.0
        fig_line.update_layout(
            title=dict(text=f"<b>{child_name} 일자별 체중 추이 (kg)</b>", font=dict(size=16), y=0.98, x=0.01, xanchor="left"),
            height=320, margin=dict(l=10, r=10, t=80, b=10),
            xaxis=dict(type="category", categoryorder="category ascending", range=[start_idx - 0.5, total_len - 0.5], autorange=False),
            yaxis=dict(title="체중 (kg)", range=[w_min, w_max])
        )
        st.plotly_chart(fig_line, use_container_width=True)

render_child_section("원빈", col_left)
render_child_section("현빈", col_right)

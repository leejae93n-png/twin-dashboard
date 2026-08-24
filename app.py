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

st.set_page_config(page_title="쌍둥이 통합 수유 & 성장 대시보드", layout="wide")

BIRTH_DATE = date(2026, 5, 14)
DUE_DATE = date(2026, 8, 12)

SCHEDULE_OPTIONS = {
    "일 8회 (3시간 텀)": ["01:00", "04:00", "07:00", "10:00", "13:00", "16:00", "19:00", "22:00"],
    "일 7회 (3.5시간 텀)": ["01:00", "04:30", "08:00", "11:30", "15:00", "18:30", "22:00"],
    "일 6회 (4시간 텀)": ["02:00", "06:00", "10:00", "14:00", "18:00", "22:00"],
    "일 5회 (4.5시간 텀)": ["06:00", "10:30", "15:00", "19:30", "23:00"]
}

GAS_URL = st.secrets.get("GAS_URL", "").strip()

def format_time_col(col_name):
    col_str = str(col_name).strip()
    if ":" in col_str:
        parts = col_str.split(":")
        if len(parts) == 2:
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    return col_str

def parse_clean_date(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    v = str(val).strip().split("T")[0].split(" ")[0]
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except:
        return v

# --- 구글 연동 타임아웃 극복을 위한 메모리 캐싱 및 네트워크 타임아웃 확장(30초) ---
def load_data_from_gas(sheet_name, force_reload=False):
    session_key = f"gas_data_{sheet_name}"
    if not force_reload and session_key in st.session_state:
        return st.session_state[session_key]

    if not GAS_URL:
        st.error("⚠️ Secrets 설정에서 GAS_URL을 등록해 주세요.")
        return pd.DataFrame()

    try:
        timestamp = int(time.time())
        res = requests.get(f"{GAS_URL}?sheet={sheet_name}&_t={timestamp}", timeout=30, allow_redirects=True)
        if res.status_code != 200:
            return st.session_state.get(session_key, pd.DataFrame())
            
        data = res.json()
        if not data or len(data) <= 1: 
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(data[1:], columns=data[0])
            df.columns = [format_time_col(c) for c in df.columns]
            if "날짜" in df.columns:
                df["날짜"] = df["날짜"].apply(parse_clean_date)
                df = df[df["날짜"] != ""]
            if "아동" in df.columns:
                df["아동"] = df["아동"].astype(str).str.strip()
        
        st.session_state[session_key] = df
        return df
    except Exception as e:
        if session_key in st.session_state:
            return st.session_state[session_key]
        st.error(f"❌ 구글 시트 연결 시간 초과 [{sheet_name}]: {e}")
        return pd.DataFrame()

def save_data_to_gas(sheet_name, df):
    if not GAS_URL:
        st.error("⚠️ GAS_URL 미설정으로 저장이 취소되었습니다.")
        return
    try:
        df_clean = df.fillna(0)
        rows = [df_clean.columns.tolist()] + df_clean.values.tolist()
        payload = {"sheet": sheet_name, "rows": rows}
        headers = {'Content-Type': 'application/json'}
        
        res = requests.post(GAS_URL, data=json.dumps(payload), headers=headers, timeout=30, allow_redirects=True)
        if res.status_code == 200:
            st.session_state[f"gas_data_{sheet_name}"] = df
            st.toast(f"✅ [{sheet_name}] 구글 시트에 안전하게 저장되었습니다!", icon="💾")
        else:
            st.warning(f"⚠️ 저장 통신 응답 코드: {res.status_code}")
    except Exception as e:
        st.error(f"❌ 구글 시트 저장 연동 오류: {e}")

def load_feeding_data(force_reload=False):
    df = load_data_from_gas("Feeding", force_reload)
    if df.empty:
        all_possible_times = list(set([t for sch in SCHEDULE_OPTIONS.values() for t in sch]))
        cols = ["날짜", "아동", "몸무게"] + sorted(all_possible_times)
        return pd.DataFrame(columns=cols)
    return df

def load_poop_data(force_reload=False):
    df = load_data_from_gas("Poop", force_reload)
    return df if not df.empty else pd.DataFrame(columns=["날짜", "아동", "시간", "종류"])

def load_sleep_data(force_reload=False):
    df = load_data_from_gas("Sleep", force_reload)
    return df if not df.empty else pd.DataFrame(columns=["날짜", "아동", "시작시간", "종류", "수면분"])

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
    if st.button("🔄 구글 시트 최신 데이터 불러오기", use_container_width=True):
        load_feeding_data(force_reload=True)
        load_poop_data(force_reload=True)
        load_sleep_data(force_reload=True)
        st.toast("구글 시트 최신 데이터 동기화 완료!", icon="🔄")
        st.rerun()

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

        today_str = get_now_kst().strftime("%Y-%m-%d")
        
        if not df_feeding.empty and "아동" in df_feeding.columns and "날짜" in df_feeding.columns:
            child_df = df_feeding[df_feeding["아동"] == child_name].copy()
            child_df = child_df.sort_values(by="날짜").reset_index(drop=True)
        else:
            child_df = pd.DataFrame()
        
        # 오늘 날짜 행이 없더라도 전체 데이터를 덮어쓰지 않고 안전하게 메모리에서만 구성
        if today_str not in child_df["날짜"].values if not child_df.empty else True:
            default_w = 3.5 if child_name == "원빈" else 4.1
            new_row = {"날짜": today_str, "아동": child_name, "몸무게": default_w}
            for col in df_feeding.columns:
                if col not in ["날짜", "아동", "몸무게"]: new_row[col] = 0
            
            # 구글 시트에 원본이 있는 경우에만 결합
            df_feeding = pd.concat([df_feeding, pd.DataFrame([new_row])], ignore_index=True)
            child_df = df_feeding[df_feeding["아동"] == child_name].copy().sort_values(by="날짜").reset_index(drop=True)

        default_base_weight = 3.5 if child_name == "원빈" else 4.1
        child_df["몸무게"] = pd.to_numeric(child_df["몸무게"], errors="coerce").fillna(default_base_weight)
        child_df["몸무게_보간"] = child_df["몸무게"].interpolate(method="linear").bfill().ffill().fillna(default_base_weight)

        today_row_matches = df_feeding[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == today_str)]
        today_row = today_row_matches.iloc[0] if len(today_row_matches) > 0 else child_df.iloc[-1]
        
        weight_raw = pd.to_numeric(today_row.get("몸무게"), errors='coerce')
        weight = float(weight_raw) if pd.notna(weight_raw) and weight_raw > 0 else default_base_weight

        today_poop_df = df_poop[(df_poop["아동"] == child_name) & (df_poop["날짜"] == today_str)] if not df_poop.empty and "아동" in df_poop.columns else pd.DataFrame()
        poop_cnt = len(today_poop_df[today_poop_df["종류"] == "대변"]) if not today_poop_df.empty else 0
        pee_cnt = len(today_poop_df[today_poop_df["종류"] == "소변"]) if not today_poop_df.empty else 0

        today_sleep_df = df_sleep[(df_sleep["아동"] == child_name) & (df_sleep["날짜"] == today_str)] if not df_sleep.empty and "아동" in df_sleep.columns else pd.DataFrame()
        total_sleep_min = pd.to_numeric(today_sleep_df["수면분"], errors="coerce").fillna(0).sum() if not today_sleep_df.empty else 0

        target_total = min(int(weight * 180), 1000)
        actual_total = sum([int(pd.to_numeric(today_row[c], errors='coerce')) for c in current_time_cols if c in today_row and pd.notna(pd.to_numeric(today_row[c], errors='coerce'))])

        slot_sums = {c: 0 for c in current_time_cols}
        slot_counts = {c: 0 for c in current_time_cols}
        for _, r in child_df.iterrows():
            for c in current_time_cols:
                if c in r and pd.notna(r[c]):
                    v = pd.to_numeric(r[c], errors='coerce')
                    if pd.notna(v) and v > 0:
                        slot_sums[c] += int(v)
                        slot_counts[c] += 1
        
        slot_avgs = {c: (slot_sums[c] / slot_counts[c] if slot_counts[c] > 0 else (target_total / len(current_time_cols))) for c in current_time_cols}
        total_avg_sum = sum(slot_avgs.values()) if sum(slot_avgs.values()) > 0 else 1
        slot_recommended = {c: round((slot_avgs[c] / total_avg_sum) * target_total / 5) * 5 for c in current_time_cols}

        k1, k2, k3 = st.columns([1.1, 1.3, 1.2])
        with k1: st.metric("체중 / 기준", f"{weight:.2f} kg", "1kg당 180ml")
        with k2: st.metric("현재 수유 달성", f"{actual_total} / {target_total} ml", f"{actual_total - target_total} ml")
        with k3: st.metric("오늘 배변/수면", f"💩{poop_cnt} 🟡{pee_cnt}", f"😴 {int(total_sleep_min)//60}시간 {int(total_sleep_min)%60}분")

        closest_slot_idx = get_closest_slot(current_time_cols, get_now_kst().time())

        # --- 2. 실시간 1초 원클릭 기록 ---
        st.subheader("⚡ 실시간 1초 원클릭 기록 (현재시간)")
        
        feed_col1, feed_col2, btn_c2, btn_c3, btn_c4 = st.columns([1.2, 1.8, 1, 1, 1])
        
        with feed_col1:
            auto_slot = current_time_cols[closest_slot_idx]
            cur_val_raw = pd.to_numeric(today_row[auto_slot], errors='coerce') if auto_slot in today_row else 0
            cur_val = int(cur_val_raw) if pd.notna(cur_val_raw) else 0
            default_feed = cur_val if cur_val > 0 else slot_recommended.get(auto_slot, 100)
            now_feed_val = st.number_input("수유량 (ml)", value=default_feed, step=5, key=f"now_val_{child_name}", label_visibility="collapsed")
            
        with feed_col2:
            if st.button(f"🍼 수유 [{auto_slot}] 기록", key=f"now_feed_{child_name}", type="primary", use_container_width=True):
                df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == today_str), auto_slot] = now_feed_val
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

        # --- 3. 📅 날짜별 통합 기록 조회 및 수정 센터 ---
        st.markdown("---")
        with st.expander("📅 날짜별 통합 기록 조회 및 수정 센터 (클릭하여 열기)", expanded=False):
            sel_date = st.date_input("조회 및 수정할 날짜 선택", get_now_kst().date(), key=f"m_date_{child_name}")
            sel_date_str = sel_date.strftime("%Y-%m-%d")
            
            st.markdown(f"#### 🔍 **[{sel_date_str}] {child_name} 기록 상태**")
            
            f_row = df_feeding[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == sel_date_str)] if not df_feeding.empty and "아동" in df_feeding.columns else pd.DataFrame()
            p_df_sel = df_poop[(df_poop["아동"] == child_name) & (df_poop["날짜"] == sel_date_str)] if not df_poop.empty and "아동" in df_poop.columns else pd.DataFrame()
            s_df_sel = df_sleep[(df_sleep["아동"] == child_name) & (df_sleep["날짜"] == sel_date_str)] if not df_sleep.empty and "아동" in df_sleep.columns else pd.DataFrame()

            missing_times = []
            row_dict = f_row.iloc[0] if len(f_row) > 0 else {}
            for t_col in current_time_cols:
                val_raw = pd.to_numeric(row_dict.get(t_col), errors='coerce') if t_col in row_dict else 0
                val = int(val_raw) if pd.notna(val_raw) else 0
                if val == 0: missing_times.append(t_col)

            if missing_times:
                m_str = ", ".join(missing_times)
                st.warning(f"⚠️ **수유 미입력 시간대**: {m_str}")
            else:
                st.success("✅ 해당 날짜의 모든 시간대 수유 기록이 완료되었습니다!")

            p_col, s_col = st.columns(2)
            with p_col:
                st.write("📌 **배변 내역 (삭제 가능)**")
                if len(p_df_sel) > 0:
                    for p_idx, p_r in p_df_sel.iterrows():
                        c_a, c_b = st.columns([3, 1])
                        with c_a: st.write(f"- {p_r['종류']} ({p_r['시간']})")
                        with c_b:
                            if st.button("🗑️ 삭제", key=f"del_p_{child_name}_{p_idx}"):
                                df_poop = df_poop.drop(p_idx).reset_index(drop=True)
                                save_poop_data(df_poop)
                                st.rerun()
                else: st.caption("배변 기록 없음")

            with s_col:
                st.write("📌 **수면 내역 (삭제 가능)**")
                if len(s_df_sel) > 0:
                    for s_idx, s_r in s_df_sel.iterrows():
                        c_a, c_b = st.columns([3, 1])
                        with c_a:
                            if str(s_r["수면분"]) == "0": st.write(f"- 😴 {s_r['시작시간']}~진행중")
                            else: st.write(f"- 😴 {s_r['시작시간']}~{s_r['종류']} ({s_r['수면분']}분)")
                        with c_b:
                            if st.button("🗑️ 삭제", key=f"del_s_{child_name}_{s_idx}"):
                                df_sleep = df_sleep.drop(s_idx).reset_index(drop=True)
                                save_sleep_data(df_sleep)
                                st.rerun()
                else: st.caption("수면 기록 없음")

            st.divider()

            st.write(f"✍️ **[{sel_date_str}] 데이터 수정 & 추가**")
            w_raw = pd.to_numeric(row_dict.get("몸무게"), errors='coerce') if "몸무게" in row_dict else weight
            cur_w = float(w_raw) if pd.notna(w_raw) else weight
            
            with st.form(key=f"m_feed_form_{child_name}_{sel_date_str}"):
                st.write("🍼 **수유량 및 체중 일괄 수정**")
                w_in = st.number_input("해당 날짜 체중 (kg)", value=cur_w, step=0.05, format="%.2f", key=f"mw_{child_name}_{sel_date_str}")
                f_in = {}
                f_cols = st.columns(4)
                for i, c_name in enumerate(current_time_cols):
                    v_raw = pd.to_numeric(row_dict.get(c_name), errors='coerce') if c_name in row_dict else 0
                    v = int(v_raw) if pd.notna(v_raw) else 0
                    with f_cols[i % 4]:
                        f_in[c_name] = st.number_input(f"{c_name}", value=v, step=5, key=f"mf_{child_name}_{sel_date_str}_{c_name}")
                
                if st.form_submit_button("💾 체중/수유 수정 저장"):
                    if len(f_row) == 0:
                        new_r = {"날짜": sel_date_str, "아동": child_name, "몸무게": w_in}
                        for col in df_feeding.columns:
                            if col not in ["날짜", "아동", "몸무게"]: new_r[col] = f_in.get(col, 0)
                        df_feeding = pd.concat([df_feeding, pd.DataFrame([new_r])], ignore_index=True)
                    else:
                        df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == sel_date_str), "몸무게"] = w_in
                        for c_name, v in f_in.items():
                            df_feeding.loc[(df_feeding["아동"] == child_name) & (df_feeding["날짜"] == sel_date_str), c_name] = v
                    save_feeding_data(df_feeding)
                    st.rerun()

            with st.form(key=f"m_poop_form_{child_name}_{sel_date_str}"):
                st.write("💩 **지나간 배변 기록 추가**")
                p1, p2 = st.columns(2)
                with p1: pk = st.selectbox("종류", ["대변", "소변"], key=f"mpk_{child_name}_{sel_date_str}")
                with p2: pt = st.time_input("발생 시각", get_now_kst().time(), key=f"mpt_{child_name}_{sel_date_str}")
                if st.form_submit_button("➕ 배변 추가"):
                    t_s = pt.strftime("%H:%M")
                    new_p = {"날짜": sel_date_str, "아동": child_name, "시간": t_s, "종류": pk}
                    df_poop = pd.concat([df_poop, pd.DataFrame([new_p])], ignore_index=True)
                    save_poop_data(df_poop)
                    st.rerun()

            with st.form(key=f"m_sleep_form_{child_name}_{sel_date_str}"):
                st.write("😴 **지나간 수면 기록 추가**")
                s1, s2 = st.columns(2)
                with s1: ss = st.time_input("수면 시작 시각", get_now_kst().time(), key=f"mss_{child_name}_{sel_date_str}")
                with s2: se = st.time_input("수면 종료 시각", get_now_kst().time(), key=f"mse_{child_name}_{sel_date_str}")
                if st.form_submit_button("➕ 수면 추가"):
                    ts = datetime.combine(sel_date, ss)
                    te = datetime.combine(sel_date, se)
                    if te < ts: te = te.replace(day=te.day + 1)
                    dur = int((te - ts).total_seconds() / 60)
                    new_s = {"날짜": sel_date_str, "아동": child_name, "시작시간": ss.strftime("%H:%M"), "종류": se.strftime("%H:%M"), "수면분": dur}
                    df_sleep = pd.concat([df_sleep, pd.DataFrame([new_s])], ignore_index=True)
                    save_sleep_data(df_sleep)
                    st.rerun()

        st.divider()

        # --- 4. 그래프 조회 기간 선택 컨트롤러 ---
        time_cols_in_df = [c for c in child_df.columns if c not in ["날짜", "아동", "몸무게", "몸무게_원본", "몸무게_보간", "추정여부"]]
        
        trend_records = []
        for _, r in child_df.iterrows():
            day_total = 0
            feed_count = 0
            details = []
            for tc in time_cols_in_df:
                if tc in r and pd.notna(r[tc]):
                    v_raw = pd.to_numeric(r[tc], errors='coerce')
                    if pd.notna(v_raw) and v_raw > 0:
                        v = int(v_raw)
                        day_total += v
                        feed_count += 1
                        details.append(f"{tc}:{v}ml")
            
            w_val = float(r["몸무게_보간"])
            target_v = min(int(w_val * 180), 1000)
            detail_str = " / ".join(details) if details else "기록없음"
            avg_single_feed = round(day_total / feed_count) if feed_count > 0 else 0
            
            trend_records.append({
                "날짜": str(r["날짜"]),
                "총수유량": day_total,
                "목표수유량": target_v,
                "평균1회수유량": avg_single_feed,
                "시간대별내역": detail_str
            })
            
        trend_df = pd.DataFrame(trend_records)
        all_dates = list(trend_df["날짜"].unique()) if not trend_df.empty else [today_str]

        period_option = st.radio(
            f"📊 **{child_name} 그래프 조회 기간**",
            ["전체", "최근 1개월 (30일)", "최근 2주 (14일)", "최근 1주 (7일)"],
            horizontal=True,
            key=f"period_range_{child_name}"
        )

        total_len = len(all_dates)
        if period_option == "최근 1주 (7일)":
            start_idx = max(0, total_len - 7)
        elif period_option == "최근 2주 (14일)":
            start_idx = max(0, total_len - 14)
        elif period_option == "최근 1개월 (30일)":
            start_idx = max(0, total_len - 30)
        else:
            start_idx = 0

        # --- 수유량 추이 그래프 ---
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

        fig_feed_trend.update_layout(
            title=dict(text=f"<b>{child_name} 일자별 총 수유량 추이</b>", font=dict(size=16), y=0.98, x=0.01, xanchor="left"),
            height=360, margin=dict(l=10, r=10, t=80, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                type="category",
                categoryorder="category ascending",
                range=[start_idx - 0.5, total_len - 0.5],
                autorange=False
            ),
            yaxis=dict(title="총 수유량 (ml)")
        )
        st.plotly_chart(fig_feed_trend, use_container_width=True)

        # --- 체중 추이 그래프 ---
        fig_line = px.line(
            child_df, x="날짜", y="몸무게_보간", markers=True, 
            title=f"<b>{child_name} 일자별 체중 추이 (kg)</b>", height=320,
            hover_data={"몸무게_보간": ":.2f"}
        )
        fig_line.update_traces(
            hovertemplate="<b>날짜</b>: %{x}<br><b>몸무게</b>: %{y:.2f} kg",
            line=dict(width=3, color="#3b82f6"), marker=dict(size=7)
        )
        w_min = child_df["몸무게_보간"].min() - 0.15 if not child_df.empty else 3.0
        w_max = child_df["몸무게_보간"].max() + 0.15 if not child_df.empty else 5.0
        fig_line.update_layout(
            title=dict(y=0.98, x=0.01, xanchor="left"),
            margin=dict(l=10, r=10, t=80, b=10),
            xaxis=dict(
                type="category",
                categoryorder="category ascending",
                range=[start_idx - 0.5, total_len - 0.5],
                autorange=False
            ),
            yaxis=dict(title="체중 (kg)", range=[w_min, w_max])
        )
        st.plotly_chart(fig_line, use_container_width=True)

render_child_section("원빈", col_left)
render_child_section("현빈", col_right)

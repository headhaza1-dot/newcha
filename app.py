import os
import sqlite3
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="사내 연차관리", page_icon="🗓️", layout="wide")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leave.db")

STATUS_WAIT = "대기"
STATUS_APPROVED = "승인"
STATUS_REJECTED = "반려"


# ---------------------------------------------------------------------------
# DB 유틸
# ---------------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            total_days REAL NOT NULL DEFAULT 15,
            join_date TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            days REAL NOT NULL,
            reason TEXT,
            status TEXT NOT NULL DEFAULT '대기',
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


def count_weekdays(start: date, end: date) -> int:
    """start~end(포함) 사이 평일(월~금) 수를 센다."""
    if end < start:
        start, end = end, start
    days = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return days


@st.cache_data(ttl=5)
def load_employees() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM employees ORDER BY name", conn)
    conn.close()
    return df


@st.cache_data(ttl=5)
def load_requests() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT r.id, r.employee_id, e.name AS employee_name, r.start_date, r.end_date,
               r.days, r.reason, r.status, r.requested_at
        FROM leave_requests r
        JOIN employees e ON e.id = r.employee_id
        ORDER BY r.requested_at DESC
        """,
        conn,
    )
    conn.close()
    return df


def add_employee(name: str, total_days: float, join_date: date):
    conn = get_conn()
    conn.execute(
        "INSERT INTO employees (name, total_days, join_date) VALUES (?, ?, ?)",
        (name, total_days, join_date.isoformat()),
    )
    conn.commit()
    conn.close()
    st.cache_data.clear()


def delete_employee(emp_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    st.cache_data.clear()


def add_request(emp_id: int, start: date, end: date, days: float, reason: str):
    conn = get_conn()
    conn.execute(
        """INSERT INTO leave_requests (employee_id, start_date, end_date, days, reason, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (emp_id, start.isoformat(), end.isoformat(), days, reason, STATUS_WAIT),
    )
    conn.commit()
    conn.close()
    st.cache_data.clear()


def update_status(req_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (status, req_id))
    conn.commit()
    conn.close()
    st.cache_data.clear()


def delete_request(req_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM leave_requests WHERE id = ?", (req_id,))
    conn.commit()
    conn.close()
    st.cache_data.clear()


init_db()

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("🗓️ 사내 연차관리")
st.caption("로그인 없이 링크로 바로 접속해 연차를 신청·조회·승인할 수 있는 공용 페이지입니다.")

tab_apply, tab_employees, tab_approve, tab_status, tab_calendar = st.tabs(
    ["📅 연차 신청", "👥 직원 관리", "✅ 승인 관리", "📊 연차 현황", "🗓 캘린더 뷰"]
)

employees_df = load_employees()
requests_df = load_requests()

# --- 연차 신청 ---------------------------------------------------------
with tab_apply:
    st.subheader("연차 신청")
    if employees_df.empty:
        st.info("먼저 '👥 직원 관리' 탭에서 직원을 등록해주세요.")
    else:
        with st.form("apply_form", clear_on_submit=True):
            name_to_id = dict(zip(employees_df["name"], employees_df["id"]))
            emp_name = st.selectbox("신청자", list(name_to_id.keys()))
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("시작일", value=date.today())
            with col2:
                end = st.date_input("종료일", value=date.today())

            leave_type = None
            if start == end:
                leave_type = st.radio(
                    "연차 종류", ["연차(1일)", "오전 반차(0.5일)", "오후 반차(0.5일)"], horizontal=True
                )

            reason = st.text_input("사유 (선택)")
            submitted = st.form_submit_button("신청하기", use_container_width=True)

            if submitted:
                if end < start:
                    st.error("종료일이 시작일보다 빠를 수 없습니다.")
                else:
                    if start == end and leave_type != "연차(1일)":
                        days = 0.5
                    else:
                        days = count_weekdays(start, end)
                        if days == 0:
                            st.warning("선택한 기간에 평일이 없습니다. 주말/공휴일을 확인해주세요.")
                    if days > 0 or (start == end and leave_type != "연차(1일)"):
                        add_request(name_to_id[emp_name], start, end, days, reason)
                        st.success(f"{emp_name}님의 연차 신청이 접수되었습니다. ({days}일, 상태: 대기)")
                        st.rerun()

    st.divider()
    st.markdown("**내 신청 내역**")
    if not requests_df.empty:
        view = requests_df[["employee_name", "start_date", "end_date", "days", "reason", "status"]].rename(
            columns={
                "employee_name": "이름",
                "start_date": "시작일",
                "end_date": "종료일",
                "days": "일수",
                "reason": "사유",
                "status": "상태",
            }
        )
        st.dataframe(view, use_container_width=True, hide_index=True)
    else:
        st.caption("아직 신청 내역이 없습니다.")

# --- 직원 관리 ---------------------------------------------------------
with tab_employees:
    st.subheader("직원 관리")
    with st.form("emp_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_name = st.text_input("이름")
        with c2:
            new_total = st.number_input("연간 총 연차일수", min_value=0.0, value=15.0, step=0.5)
        with c3:
            new_join = st.date_input("입사일", value=date.today())
        add_btn = st.form_submit_button("직원 등록", use_container_width=True)
        if add_btn:
            if not new_name.strip():
                st.error("이름을 입력해주세요.")
            else:
                add_employee(new_name.strip(), new_total, new_join)
                st.success(f"'{new_name}' 님이 등록되었습니다.")
                st.rerun()

    st.divider()
    if employees_df.empty:
        st.caption("등록된 직원이 없습니다.")
    else:
        for _, row in employees_df.iterrows():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.write(row["name"])
            c2.write(f"총 {row['total_days']}일")
            c3.write(f"입사일 {row['join_date']}")
            if c4.button("삭제", key=f"del_emp_{row['id']}"):
                delete_employee(int(row["id"]))
                st.rerun()

# --- 승인 관리 ---------------------------------------------------------
with tab_approve:
    st.subheader("승인 관리 (로그인 없이 누구나 처리할 수 있는 공용 화면입니다)")
    pending = requests_df[requests_df["status"] == STATUS_WAIT] if not requests_df.empty else requests_df
    if pending.empty:
        st.caption("대기 중인 신청이 없습니다.")
    else:
        for _, row in pending.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.write(
                        f"**{row['employee_name']}** · {row['start_date']} ~ {row['end_date']} · "
                        f"{row['days']}일 · 사유: {row['reason'] or '-'}"
                    )
                with c2:
                    b1, b2 = st.columns(2)
                    if b1.button("승인", key=f"ok_{row['id']}", use_container_width=True):
                        update_status(int(row["id"]), STATUS_APPROVED)
                        st.rerun()
                    if b2.button("반려", key=f"no_{row['id']}", use_container_width=True):
                        update_status(int(row["id"]), STATUS_REJECTED)
                        st.rerun()

    st.divider()
    st.markdown("**처리 완료 내역**")
    done = requests_df[requests_df["status"] != STATUS_WAIT] if not requests_df.empty else requests_df
    if not done.empty:
        view = done[["employee_name", "start_date", "end_date", "days", "status"]].rename(
            columns={
                "employee_name": "이름",
                "start_date": "시작일",
                "end_date": "종료일",
                "days": "일수",
                "status": "상태",
            }
        )
        st.dataframe(view, use_container_width=True, hide_index=True)
    else:
        st.caption("처리된 내역이 없습니다.")

# --- 연차 현황 ---------------------------------------------------------
with tab_status:
    st.subheader("직원별 연차 현황")
    if employees_df.empty:
        st.caption("등록된 직원이 없습니다.")
    else:
        approved = requests_df[requests_df["status"] == STATUS_APPROVED] if not requests_df.empty else pd.DataFrame(columns=["employee_id", "days"])
        used_by_emp = approved.groupby("employee_id")["days"].sum() if not approved.empty else pd.Series(dtype=float)

        pending_df = requests_df[requests_df["status"] == STATUS_WAIT] if not requests_df.empty else pd.DataFrame(columns=["employee_id", "days"])
        pending_by_emp = pending_df.groupby("employee_id")["days"].sum() if not pending_df.empty else pd.Series(dtype=float)

        rows = []
        for _, e in employees_df.iterrows():
            used = float(used_by_emp.get(e["id"], 0))
            pend = float(pending_by_emp.get(e["id"], 0))
            rows.append(
                {
                    "이름": e["name"],
                    "총 연차": e["total_days"],
                    "사용(승인)": used,
                    "신청중(대기)": pend,
                    "잔여": e["total_days"] - used,
                }
            )
        status_df = pd.DataFrame(rows)
        st.dataframe(status_df, use_container_width=True, hide_index=True)

        fig = px.bar(
            status_df,
            x="이름",
            y=["사용(승인)", "잔여"],
            title="직원별 연차 사용/잔여 현황",
            barmode="stack",
        )
        st.plotly_chart(fig, use_container_width=True)

# --- 캘린더 뷰 ---------------------------------------------------------
with tab_calendar:
    st.subheader("승인된 연차 캘린더 뷰")
    approved = requests_df[requests_df["status"] == STATUS_APPROVED] if not requests_df.empty else pd.DataFrame()
    if approved.empty:
        st.caption("표시할 승인된 연차가 없습니다.")
    else:
        gantt_df = approved.copy()
        # 종료일에 +1일 해야 timeline 바가 종료일 하루를 포함해 보임
        gantt_df["end_display"] = pd.to_datetime(gantt_df["end_date"]) + pd.Timedelta(days=1)
        fig = px.timeline(
            gantt_df,
            x_start="start_date",
            x_end="end_display",
            y="employee_name",
            color="employee_name",
            hover_data=["days", "reason"],
            title="승인된 연차 일정",
        )
        fig.update_yaxes(autorange="reversed", title="")
        st.plotly_chart(fig, use_container_width=True)

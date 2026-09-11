import calendar
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "leave_manager.db"
COLORS = ["#7986cb", "#33b679", "#8e24aa", "#e67c73", "#f6bf26", "#f4511e", "#039be5", "#616161", "#3f51b5", "#bef264"]
HOLIDAYS = {
    "2026-01-01": "신정", "2026-02-16": "설날 연휴", "2026-02-17": "설날", "2026-02-18": "설날 연휴",
    "2026-03-01": "삼일절", "2026-03-02": "삼일절 대체공휴일", "2026-05-01": "근로자의 날",
    "2026-05-05": "어린이날", "2026-05-24": "부처님오신날", "2026-05-25": "부처님오신날 대체공휴일",
    "2026-06-06": "현충일", "2026-07-17": "제헌절", "2026-08-15": "광복절", "2026-08-17": "광복절 대체공휴일",
    "2026-09-24": "추석 연휴", "2026-09-25": "추석", "2026-09-26": "추석 연휴",
    "2026-10-03": "개천절", "2026-10-05": "개천절 대체공휴일", "2026-10-09": "한글날", "2026-12-25": "성탄절",
}

st.set_page_config(page_title="쉼표 — 직원 연차관리", page_icon="쉼", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1400px; padding-top: 2rem;}
.member-dot {display:inline-block;width:14px;height:14px;border-radius:50%;margin-right:6px;vertical-align:-2px;}
.holiday {background:#fff1f2;color:#be123c;border-radius:6px;padding:3px 5px;font-size:11px;font-weight:700;margin:2px 0;}
.leave-chip {border-radius:6px;padding:3px 5px;font-size:11px;font-weight:700;margin:2px 0;color:#1f2937;}
</style>
""", unsafe_allow_html=True)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, team TEXT NOT NULL,
            role TEXT NOT NULL, color TEXT NOT NULL DEFAULT '#bef264', allowance REAL NOT NULL DEFAULT 15,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            kind TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL, days REAL NOT NULL,
            reason TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)


def employees():
    with db() as conn:
        return conn.execute("SELECT * FROM employees ORDER BY name").fetchall()


def leaves():
    with db() as conn:
        return conn.execute("""SELECT l.*, e.name employee_name, e.team, e.color
            FROM leaves l JOIN employees e ON e.id=l.employee_id ORDER BY l.start_date DESC, l.id DESC""").fetchall()


def weekdays(start, end):
    n, cur = 0, start
    while cur <= end:
        if cur.weekday() < 5:
            n += 1
        cur += timedelta(days=1)
    return max(n, 1)


def status_text(status):
    return {"pending": "승인 대기", "approved": "승인", "rejected": "반려", "cancelled": "취소"}[status]


def add_employee(name, team, role, color, allowance):
    with db() as conn:
        conn.execute("INSERT INTO employees(name,team,role,color,allowance) VALUES(?,?,?,?,?)", (name, team, role, color, allowance))


def add_leave(employee_id, kind, start, end, days, reason):
    with db() as conn:
        conn.execute("INSERT INTO leaves(employee_id,kind,start_date,end_date,days,reason) VALUES(?,?,?,?,?,?)", (employee_id, kind, start.isoformat(), end.isoformat(), days, reason))


def set_status(leave_id, status):
    with db() as conn:
        conn.execute("UPDATE leaves SET status=? WHERE id=?", (status, leave_id))


def delete_employee(employee_id):
    with db() as conn:
        conn.execute("DELETE FROM employees WHERE id=?", (employee_id,))


def calendar_card(year, month, rows):
    st.subheader(f"{year}년 {month}월")
    st.caption("빨간색은 대한민국 공휴일·대체공휴일, 구성원 색상은 승인 연차입니다.")
    cal = calendar.Calendar(firstweekday=6)
    cols = st.columns(7)
    for col, name in zip(cols, ["일", "월", "화", "수", "목", "금", "토"]):
        col.markdown(f"**{name}**")
    by_day = {}
    for row in rows:
        if row["status"] != "approved":
            continue
        start, end = date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"])
        cur = start
        while cur <= end:
            if cur.year == year and cur.month == month:
                by_day.setdefault(cur.day, []).append(row)
            cur += timedelta(days=1)
    for week in cal.monthdayscalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if not day:
                cols[i].write("")
                continue
            iso = f"{year:04d}-{month:02d}-{day:02d}"
            html = f"<div style='min-height:90px'><b>{day}</b>"
            if iso in HOLIDAYS:
                html += f"<div class='holiday'>{HOLIDAYS[iso]}</div>"
            for row in by_day.get(day, [])[:2]:
                html += f"<div class='leave-chip' style='background:{row['color']}'>{row['employee_name']}</div>"
            if len(by_day.get(day, [])) > 2:
                html += f"<small>+{len(by_day[day])-2}명</small>"
            cols[i].markdown(html + "</div>", unsafe_allow_html=True)


def app():
    init_db()
    emps, all_leaves = employees(), leaves()
    st.title("쉼표")
    st.caption("직원 연차관리")
    menu = st.sidebar.radio("메뉴", ["대시보드", "연차 캘린더", "구성원 관리", "승인 관리"])
    st.sidebar.divider()
    with st.sidebar.expander("직원 등록", expanded=False):
        with st.form("employee_form", clear_on_submit=True):
            name = st.text_input("이름"); team = st.text_input("팀"); role = st.text_input("직무")
            color = st.selectbox("표시 색상", COLORS, format_func=lambda c: "●  " + c, index=9)
            allowance = st.number_input("연간 부여 연차", min_value=0.0, value=15.0, step=0.5)
            if st.form_submit_button("직원 등록"):
                if not name.strip() or not team.strip() or not role.strip(): st.error("이름·팀·직무를 입력해 주세요.")
                else: add_employee(name.strip(), team.strip(), role.strip(), color, allowance); st.success("직원을 등록했어요."); st.rerun()
    if menu == "대시보드":
        approved = [x for x in all_leaves if x["status"] == "approved"]
        today = date.today().isoformat()
        used = {e["id"]: sum(x["days"] for x in approved if x["employee_id"] == e["id"]) for e in emps}
        a, b, c, d = st.columns(4)
        a.metric("전체 구성원", f"{len(emps)}명"); b.metric("오늘 휴가", f"{sum(x['start_date']<=today<=x['end_date'] for x in approved)}명")
        c.metric("승인 대기", f"{sum(x['status']=='pending' for x in all_leaves)}건")
        d.metric("평균 잔여 연차", f"{(sum(e['allowance']-used[e['id']] for e in emps)/len(emps)):.1f}일" if emps else "0.0일")
        st.divider(); now = date.today(); calendar_card(now.year, now.month, all_leaves)
    elif menu == "연차 캘린더":
        now = date.today(); calendar_card(now.year, now.month, all_leaves)
        st.info("월 이동이 필요한 경우 아래 날짜 선택에서 확인할 월을 골라 주세요.")
        chosen = st.date_input("확인할 월", now, key="calendar_month")
        if chosen: calendar_card(chosen.year, chosen.month, all_leaves)
    elif menu == "구성원 관리":
        st.subheader("구성원 관리")
        used = {e["id"]: sum(x["days"] for x in all_leaves if x["employee_id"] == e["id"] and x["status"] == "approved") for e in emps}
        for e in emps:
            left = e["allowance"] - used[e["id"]]
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.markdown(f"<span class='member-dot' style='background:{e['color']}'></span> **{e['name']}** · {e['team']} · {e['role']}", unsafe_allow_html=True)
            c2.write(f"부여 {e['allowance']}일 / 사용 {used[e['id']]}일")
            c3.write(f"잔여 {left}일")
            if c4.button("삭제", key=f"del-{e['id']}"):
                st.session_state[f"confirm-{e['id']}"] = True
            if st.session_state.get(f"confirm-{e['id']}"):
                st.warning(f"{e['name']}님과 연차 기록을 함께 삭제할까요?")
                y, n = st.columns(2)
                if y.button("삭제 확인", key=f"yes-{e['id']}"): delete_employee(e["id"]); st.session_state.pop(f"confirm-{e['id']}"); st.rerun()
                if n.button("취소", key=f"no-{e['id']}"): st.session_state.pop(f"confirm-{e['id']}"); st.rerun()
            st.divider()
    else:
        st.subheader("연차 신청")
        if emps:
            with st.form("leave_form", clear_on_submit=True):
                emp = st.selectbox("직원", emps, format_func=lambda e: f"{e['name']} · {e['team']}")
                kind = st.selectbox("휴가 종류", ["연차", "오전 반차", "오후 반차", "리프레시 휴가", "경조 휴가"])
                start = st.date_input("시작일", date.today()); end = st.date_input("종료일", date.today())
                days = st.number_input("사용 일수", min_value=0.5, value=float(weekdays(start, end)), step=0.5)
                reason = st.text_input("메모 (선택)")
                if st.form_submit_button("연차 신청"):
                    if end < start: st.error("종료일은 시작일보다 빠를 수 없어요.")
                    else: add_leave(emp["id"], kind, start, end, days, reason); st.success("연차를 신청했어요."); st.rerun()
        st.divider(); st.subheader("신청·승인 내역")
        for row in all_leaves:
            c1, c2, c3 = st.columns([5, 2, 2])
            c1.markdown(f"<span class='member-dot' style='background:{row['color']}'></span> **{row['employee_name']}** · {row['start_date']} ~ {row['end_date']} · {row['days']}일", unsafe_allow_html=True)
            c2.write(status_text(row["status"]))
            if row["status"] == "pending":
                if c3.button("승인", key=f"approve-{row['id']}"): set_status(row["id"], "approved"); st.rerun()
                if c3.button("신청 취소", key=f"cancel-p-{row['id']}"): set_status(row["id"], "cancelled"); st.rerun()
            elif row["status"] == "approved" and c3.button("승인 취소", key=f"cancel-a-{row['id']}"):
                set_status(row["id"], "cancelled"); st.rerun()
            st.divider()


if __name__ == "__main__":
    app()

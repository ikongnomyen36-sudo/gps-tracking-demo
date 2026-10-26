import sqlite3
from datetime import datetime
import streamlit as st
import folium
from streamlit_folium import st_folium

APP_TITLE = "TrackEasy | ระบบติดตามพัสดุจำลอง"
DB_PATH = "tracking_demo.db"
ADMIN_PASSWORD = "1234"  # เปลี่ยนรหัสนี้ก่อนเผยแพร่ หากต้องการใช้จริง

STATUSES = [
    "รับพัสดุแล้ว",
    "กำลังคัดแยกพัสดุ",
    "กำลังขนส่ง",
    "ถึงศูนย์กระจายสินค้า",
    "อยู่ระหว่างนำจ่าย",
    "จัดส่งสำเร็จ",
]

DEMO_PARCELS = [
    ("TH100001", "คุณสมชาย ใจดี", "กรุงเทพมหานคร", "กำลังขนส่ง", 13.7563, 100.5018, "เสื้อยืด 1 กล่อง"),
    ("TH100002", "คุณมาลี รักเรียน", "ชลบุรี", "อยู่ระหว่างนำจ่าย", 13.3611, 100.9847, "หนังสือ 1 กล่อง"),
    ("TH100003", "คุณนที ตัวอย่าง", "เชียงใหม่", "รับพัสดุแล้ว", 18.7883, 98.9853, "อุปกรณ์ 1 กล่อง"),
]

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS parcels (
                tracking_number TEXT PRIMARY KEY,
                recipient_name TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                details TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM parcels").fetchone()[0]
        if count == 0:
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.executemany("""
                INSERT INTO parcels
                (tracking_number, recipient_name, destination, status, lat, lon, details, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [(*row, now) for row in DEMO_PARCELS])

def get_parcel(tracking):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM parcels WHERE tracking_number = ?",
            (tracking.strip().upper(),)
        ).fetchone()

def get_all():
    with db() as conn:
        return conn.execute(
            "SELECT * FROM parcels ORDER BY updated_at DESC"
        ).fetchall()

def save_parcel(tracking, recipient, destination, status, lat, lon, details):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    with db() as conn:
        conn.execute("""
            INSERT INTO parcels
            (tracking_number, recipient_name, destination, status, lat, lon, details, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tracking_number) DO UPDATE SET
              recipient_name=excluded.recipient_name,
              destination=excluded.destination,
              status=excluded.status,
              lat=excluded.lat,
              lon=excluded.lon,
              details=excluded.details,
              updated_at=excluded.updated_at
        """, (tracking.strip().upper(), recipient, destination, status, float(lat), float(lon), details, now))

st.set_page_config(page_title=APP_TITLE, page_icon="📦", layout="wide")
init_db()

st.title("📦 TrackEasy")
st.caption("ระบบติดตามพัสดุและตำแหน่งรถขนส่ง (เวอร์ชันจำลองสำหรับโปรเจกต์)")
page = st.sidebar.radio("เลือกหน้า", ["ติดตามพัสดุ", "ผู้ดูแลระบบ", "ข้อมูลโครงงาน"])

if page == "ติดตามพัสดุ":
    st.subheader("🔎 ตรวจสอบสถานะพัสดุ")
    st.write("ลองใช้เลขพัสดุตัวอย่าง: `TH100001`, `TH100002` หรือ `TH100003`")
    with st.form("track_form"):
        tracking = st.text_input("เลขพัสดุ", placeholder="เช่น TH100001")
        submitted = st.form_submit_button("ค้นหาพัสดุ", type="primary")
    if submitted:
        if not tracking.strip():
            st.warning("กรุณากรอกเลขพัสดุก่อนค้นหา")
        else:
            parcel = get_parcel(tracking)
            if parcel is None:
                st.error("ไม่พบเลขพัสดุนี้ กรุณาตรวจสอบเลขพัสดุอีกครั้ง")
            else:
                st.success("พบข้อมูลพัสดุ")
                a, b, c = st.columns(3)
                a.metric("เลขพัสดุ", parcel["tracking_number"])
                b.metric("สถานะล่าสุด", parcel["status"])
                c.metric("ปลายทาง", parcel["destination"])
                st.write(f"**ผู้รับ:** {parcel['recipient_name']}")
                st.write(f"**รายละเอียด:** {parcel['details'] or '-'}")
                st.caption(f"อัปเดตล่าสุด: {parcel['updated_at']}")
                st.markdown("#### เส้นทางสถานะพัสดุ")
                current_index = STATUSES.index(parcel["status"]) if parcel["status"] in STATUSES else 0
                for i, status in enumerate(STATUSES):
                    marker = "🟢" if i <= current_index else "⚪"
                    st.write(f"{marker} {i+1}. {status}")
                st.markdown("#### 📍 ตำแหน่งรถขนส่งจำลอง")
                m = folium.Map(location=[parcel["lat"], parcel["lon"]], zoom_start=11)
                folium.Marker(
                    [parcel["lat"], parcel["lon"]],
                    tooltip=parcel["tracking_number"],
                    popup=f"รถขนส่งจำลอง<br>สถานะ: {parcel['status']}<br>ปลายทาง: {parcel['destination']}",
                    icon=folium.Icon(color="blue", icon="truck", prefix="fa")
                ).add_to(m)
                st_folium(m, use_container_width=True, height=400, returned_objects=[])
                st.caption("หมายเหตุ: หมุดแผนที่เป็นตำแหน่งตัวอย่างที่ผู้ดูแลระบบกำหนด ไม่ใช่ GPS สดจากรถจริง")

elif page == "ผู้ดูแลระบบ":
    st.subheader("🛠️ จัดการพัสดุ")
    if not st.session_state.get("admin_logged_in", False):
        with st.form("admin_login"):
            password = st.text_input("รหัสผ่านผู้ดูแลระบบ", type="password")
            login = st.form_submit_button("เข้าสู่ระบบ")
        if login:
            if password == ADMIN_PASSWORD:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")
        st.info("รหัสผ่านสำหรับสาธิต: 1234 (ควรเปลี่ยนก่อนนำไปเผยแพร่)")
    else:
        if st.button("ออกจากระบบ"):
            st.session_state["admin_logged_in"] = False
            st.rerun()
        parcels = get_all()
        st.markdown("#### พัสดุทั้งหมด")
        if parcels:
            st.dataframe([{
                "เลขพัสดุ": p["tracking_number"],
                "ผู้รับ": p["recipient_name"],
                "ปลายทาง": p["destination"],
                "สถานะ": p["status"],
                "ละติจูด": p["lat"],
                "ลองจิจูด": p["lon"],
                "อัปเดตล่าสุด": p["updated_at"]
            } for p in parcels], use_container_width=True, hide_index=True)

        st.markdown("#### เพิ่มหรือแก้ไขข้อมูลพัสดุ")
        existing_codes = [p["tracking_number"] for p in parcels]
        mode = st.radio("วิธีกรอก", ["เพิ่มพัสดุใหม่", "แก้ไขพัสดุเดิม"], horizontal=True)
        selected = None
        if mode == "แก้ไขพัสดุเดิม" and existing_codes:
            selected = st.selectbox("เลือกเลขพัสดุ", existing_codes)
        old = get_parcel(selected) if selected else None
        with st.form("parcel_form"):
            tracking_num = st.text_input("เลขพัสดุ *", value=old["tracking_number"] if old else "")
            recipient = st.text_input("ชื่อผู้รับ *", value=old["recipient_name"] if old else "")
            destination = st.text_input("จังหวัดปลายทาง *", value=old["destination"] if old else "")
            status = st.selectbox("สถานะ", STATUSES, index=STATUSES.index(old["status"]) if old and old["status"] in STATUSES else 0)
            details = st.text_input("รายละเอียดพัสดุ", value=old["details"] if old else "")
            col1, col2 = st.columns(2)
            lat = col1.number_input("ละติจูด (Latitude)", min_value=-90.0, max_value=90.0, value=float(old["lat"]) if old else 13.7563, format="%.6f")
            lon = col2.number_input("ลองจิจูด (Longitude)", min_value=-180.0, max_value=180.0, value=float(old["lon"]) if old else 100.5018, format="%.6f")
            save = st.form_submit_button("บันทึกข้อมูล", type="primary")
        if save:
            if not tracking_num.strip() or not recipient.strip() or not destination.strip():
                st.error("กรุณากรอกเลขพัสดุ ชื่อผู้รับ และจังหวัดปลายทางให้ครบ")
            else:
                save_parcel(tracking_num, recipient, destination, status, lat, lon, details)
                st.success("บันทึกข้อมูลแล้ว ลูกค้าสามารถค้นหาด้วยเลขพัสดุได้")
                st.rerun()

elif page == "ข้อมูลโครงงาน":
    st.subheader("📘 รายละเอียดระบบ")
    st.markdown("""
    **ชื่อโครงงาน:** ระบบจำลองติดตามสถานะพัสดุและตำแหน่งรถขนส่งด้วย GPS

    **วัตถุประสงค์**
    1. เพื่อให้ลูกค้าค้นหาสถานะพัสดุด้วยเลขติดตาม
    2. เพื่อให้ผู้ดูแลระบบเพิ่มและแก้ไขข้อมูลพัสดุ
    3. เพื่อแสดงตำแหน่งรถขนส่งบนแผนที่ในรูปแบบจำลอง

    **เทคโนโลยีที่ใช้**
    - Python
    - Streamlit สำหรับสร้างหน้าจอเว็บแอป
    - SQLite สำหรับเก็บข้อมูลตัวอย่าง
    - Folium สำหรับแสดงแผนที่

    **ข้อจำกัด:** พิกัดเป็นข้อมูลจำลอง ไม่ได้รับข้อมูล GPS แบบเรียลไทม์จากอุปกรณ์บนรถ
    """)
    st.info("ข้อมูลตัวอย่างมีเลขพัสดุ TH100001, TH100002 และ TH100003")

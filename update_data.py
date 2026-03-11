"""
update_data.py
รันทุกวันโดย GitHub Actions เพื่ออัปเดต data.json
- ค้นหาข่าวสารล่าสุดจากเว็บไซต์และ Google
- อัปเดต last_updated timestamp
- อัปเดต urgency ตามวันที่ปัจจุบัน
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
import urllib.request
import urllib.parse
import re

TZ_THAI = timezone(timedelta(hours=7))
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def recalculate_urgency(schools):
    """
    ปรับ urgency ตามเดือนปัจจุบัน (เดือนไทย พ.ศ.)
    urgent  = ใกล้เปิดรับสมัครภายใน 2 เดือน
    normal  = เปิดรับภายใน 3-7 เดือน
    later   = ยังไกล (> 7 เดือน)
    """
    now = datetime.now(TZ_THAI)
    now_be_year = now.year + 543  # แปลงเป็น พ.ศ.
    now_month = now.month

    # ช่วงเวลาสมัครโดยประมาณของแต่ละโรงเรียน (BE year, month)
    apply_schedule = {
        "saint-gabriel":      {"year": 2569, "month_start": 4, "month_end": 5},
        "assumption-bangrак": {"year": 2569, "month_start": 10, "month_end": 11},
        "assumption-thonburi":{"year": 2569, "month_start": 6,  "month_end": 10},
        "bangkok-christian":  {"year": 2569, "month_start": 6,  "month_end": 10},
        "satit-swu":          {"year": 2569, "month_start": 10, "month_end": 11},
        "satit-ku":           {"year": 2570, "month_start": 1,  "month_end": 2},
    }

    changed = False
    for school in schools:
        sid = school["id"]
        if sid not in apply_schedule:
            continue
        sched = apply_schedule[sid]

        # คำนวณเดือนห่างจากปัจจุบัน
        target_month = (sched["year"] - now_be_year) * 12 + sched["month_start"] - now_month

        if target_month <= 0:
            new_urgency = "passed"
        elif target_month <= 2:
            new_urgency = "urgent"
        elif target_month <= 7:
            new_urgency = "normal"
        else:
            new_urgency = "later"

        if school.get("apply_urgency") != new_urgency:
            school["apply_urgency"] = new_urgency
            changed = True
            print(f"  Updated urgency for {school['name']}: {new_urgency}")

    return changed

def check_school_website(school):
    """
    ตรวจสอบเว็บไซต์โรงเรียนว่ามีประกาศรับสมัครใหม่หรือไม่
    """
    try:
        url = school.get("apply_url", school.get("website", ""))
        if not url:
            return None
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SchoolAdmissionBot/1.0)"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # ค้นหาคำที่บ่งบอกว่ามีการประกาศรับสมัครใหม่
        keywords = ["รับสมัคร", "ป.1", "2570", "ประถม", "สมัคร", "admission"]
        found = [kw for kw in keywords if kw.lower() in html.lower()]
        return {"url": url, "keywords_found": found, "status": "ok"}
    except Exception as e:
        return {"url": url, "error": str(e), "status": "error"}

def update_urgency_notes(schools):
    """อัปเดตข้อความ urgency_note ตาม urgency ปัจจุบัน"""
    notes = {
        "urgent": "🚨 ใกล้เปิดรับสมัครแล้ว! ติดตามด่วน",
        "normal": "📌 เตรียมเอกสารให้พร้อม",
        "later":  "✅ ยังมีเวลา — เริ่มเตรียมตัวได้",
        "passed": "✔️ ผ่านช่วงสมัครไปแล้ว (อ้างอิงปีถัดไป)",
    }
    for school in schools:
        u = school.get("apply_urgency", "normal")
        if u in notes and school.get("urgency_note") != notes[u]:
            school["urgency_note"] = notes[u]

def main():
    print(f"\n{'='*50}")
    print(f"School Admission Data Updater")
    print(f"เวลา: {datetime.now(TZ_THAI).strftime('%Y-%m-%d %H:%M:%S')} (เวลาไทย)")
    print(f"{'='*50}\n")

    data = load_data()
    changed = False

    # 1. อัปเดต urgency ตามวันที่ปัจจุบัน
    print("1. ตรวจสอบ urgency...")
    if recalculate_urgency(data["schools"]):
        update_urgency_notes(data["schools"])
        changed = True

    # 2. ตรวจสอบเว็บไซต์โรงเรียน (optional — ถ้าต้องการ uncomment)
    # print("\n2. ตรวจสอบเว็บไซต์โรงเรียน...")
    # for school in data["schools"]:
    #     result = check_school_website(school)
    #     if result:
    #         print(f"  {school['name']}: {result['status']} - {result.get('keywords_found', [])}")

    # 3. อัปเดต timestamp เสมอ
    now_str = datetime.now(TZ_THAI).strftime("%Y-%m-%dT%H:%M:%S+07:00")
    data["meta"]["last_updated"] = now_str
    changed = True

    # 4. บันทึก
    if changed:
        save_data(data)
        print(f"\n✅ บันทึกข้อมูลสำเร็จ: {now_str}")
    else:
        print(f"\n⏭️  ไม่มีการเปลี่ยนแปลง")

    print(f"\n{'='*50}\n")

if __name__ == "__main__":
    main()

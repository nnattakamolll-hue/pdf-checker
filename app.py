import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os
import time

st.set_page_config(page_title="PDF Specific Fields Checker", page_icon="📄", layout="wide")

st.title("📄 ระบบตรวจสอบ Description, ราคา และจำนวน ด้วย AI")
st.caption("เปรียบเทียบไฟล์ตั้งต้น (File A) กับไฟล์ตรวจสอบ (File B) เจาะจงตรวจเฉพาะ Description, ราคา และจำนวน")

api_key = st.text_input("🔑 กรอก Gemini API Key ของคุณที่นี่", type="password", help="วาง API Key ที่ได้มาจาก Google AI Studio ตรงนี้")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("1. ไฟล์ตั้งต้น (Baseline - File A)")
    file_a = st.file_uploader("เลือกไฟล์ PDF ต้นฉบับ", type=["pdf"], key="fa")

with col2:
    st.subheader("2. ไฟล์ที่ต้องการตรวจ (To Check - File B)")
    file_b = st.file_uploader("เลือกไฟล์ PDF ที่ต้องการเทียบ", type=["pdf"], key="fb")

def upload_to_gemini(client, uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    g_file = client.files.upload(file=tmp_path)
    while g_file.state.name == "PROCESSING":
        time.sleep(2)
        g_file = client.files.get(name=g_file.name)
    os.unlink(tmp_path)
    return g_file

st.divider()
if st.button("🚀 เริ่มตรวจสอบเอกสาร", type="primary", use_container_width=True):
    if not api_key:
        st.error("❌ กรุณากรอก Gemini API Key ในช่องด้านบนก่อนครับ")
    elif not file_a or not file_b:
        st.error("❌ กรุณาอัปโหลดไฟล์ PDF ให้ครบทั้ง 2 ไฟล์ครับ")
    else:
        status_box = st.status("🔍 กำลังประมวลผล...", expanded=True)
        uploaded_files = []
        try:
            client = genai.Client(api_key=api_key)
            
            status_box.write("📤 กำลังส่งไฟล์เข้าสู่ระบบวิเคราะห์...")
            g_a = upload_to_gemini(client, file_a)
            uploaded_files.append(g_a.name)
            
            g_b = upload_to_gemini(client, file_b)
            uploaded_files.append(g_b.name)
            
            status_box.write("🤖 AI กำลังตรวจสอบ Description, ราคา และจำนวน...")
            
            # Prompt เน้นตรวจเฉพาะ Description, ราคา และจำนวน
            prompt = """
            จงเปรียบเทียบเอกสาร B (ไฟล์ตรวจสอบ) กับ เอกสาร A (ไฟล์ตั้งต้น) โดยเจาะจงตรวจสอบเฉพาะ 3 จุดสำคัญนี้เท่านั้น:
            1. Description (รายละเอียด/คำอธิบายสินค้า): ต้องตรงกันแบบคำต่อคำ ตัวอักษรต่อตัวอักษร (Exact Match) ห้ามมีข้อความตกหล่น หรือผิดเพี้ยน
            2. จำนวนสินค้า (Quantity / Qty): ตัวเลขจำนวนต้องตรงกันทุกรายการ
            3. ราคา (Price / Unit Price / Total Price): ตัวเลขราคาหน่วยและราคารวมต้องตรงกัน

            คำสั่งการวิเคราะห์เอกสาร B:
            1. สำรวจไฟล์ B ก่อนว่ามีกี่หน้า และประกอบด้วยเอกสารประเภทใดบ้าง (เช่น ใบสั่งซื้อ PO, ใบเสนอราคา Quotation ฯลฯ)
            2. แบ่งรายงานผลออกเป็นส่วนๆ ตามประเภทเอกสารหรือหน้าที่พบในไฟล์ B (เช่น "ส่วนที่ 1: เปรียบเทียบกับหน้า [ชื่อประเภทเอกสาร]")

            เงื่อนไขการแสดงผลตาราง:
            - ทุกส่วนต้องสรุปออกมาเป็นตาราง Markdown ที่มีคอลัมน์หลักดังนี้:
              1. รายการ / รหัสสินค้า (พร้อมระบุเลขหน้า/Item ในไฟล์ B)
              2. รายละเอียดใน เอกสาร A (ไฟล์ตั้งต้น)
              3. รายละเอียดใน เอกสาร B (ไฟล์ตรวจสอบ)
              4. ผลการตรวจสอบ / จุดที่แตกต่าง (ระบุสั้นๆ ว่า Description, จำนวน หรือราคา ตรงกันหรือไม่ตรงกันอย่างไร)
            - ในช่อง "ผลการตรวจสอบ / จุดที่แตกต่าง" ให้สรุปเป็น Bullet Point (•) สั้นกระชับ ตรงประเด็น
            - ห้ามใช้แท็ก HTML เช่น <br> ในตารางเด็ดขาด
            - หากทั้ง Description, จำนวน และราคา ตรงกันหมดทุกรายการ ให้สรุปผลว่า "Description, จำนวน และราคา ตรงกันทุกประการ 100%"
            """
            
            # ระบบลองส่งซ้ำอัตโนมัติ (Auto-Retry) เมื่อเจอ 503 High Demand
            max_retries = 5
            retry_delay = 5
            response = None
            success = False
            
            for attempt in range(max_retries):
                try:
                    status_box.write(f"🔄 กำลังประมวลผล (พยายามครั้งที่ {attempt+1}/{max_retries})...")
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=[g_a, g_b, prompt]
                    )
                    success = True
                    break
                except Exception as api_err:
                    if ("503" in str(api_err) or "UNAVAILABLE" in str(api_err)) and attempt < max_retries - 1:
                        status_box.warning(f"⚠️ เซิร์ฟเวอร์หนาแน่น กำลังลองใหม่ในอีก {retry_delay} วินาที...")
                        time.sleep(retry_delay)
                        retry_delay += 3
                    else:
                        raise api_err
            
            if not success or not response:
                raise Exception("เซิร์ฟเวอร์หนาแน่นเกินไป โปรดลองกดปุ่มเริ่มตรวจสอบใหม่อีกครั้ง")
            
            # ลบแท็ก <br> ทิ้งทั้งหมด
            clean_output = response.text.replace("<br>", " ").replace("<br/>", " ").replace("<BR>", " ")
            
            status_box.update(label="✅ ตรวจสอบเสร็จสิ้น!", state="complete", expanded=False)
            st.markdown(clean_output)
            
            st.divider()
            st.download_button(
                label="📥 ดาวน์โหลดรายงานผลเป็นไฟล์ข้อความ (.txt)",
                data=clean_output,
                file_name="check_report.txt",
                mime="text/plain"
            )

        except Exception as e:
            status_box.update(label="❌ เกิดข้อผิดพลาด", state="error", expanded=True)
            st.error(f"รายละเอียด: {str(e)}")
            
        finally:
            if uploaded_files and 'client' in locals():
                for name in uploaded_files:
                    try:
                        client.files.delete(name=name)
                    except:
                        pass

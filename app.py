import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os
import time

st.set_page_config(page_title="PDF Comparison Tool", page_icon="📄", layout="wide")

st.title("📄 ระบบตรวจสอบและเปรียบเทียบไฟล์ PDF ด้วย AI")
st.caption("อัปโหลดไฟล์ตั้งต้น (File A) และไฟล์ที่ต้องการตรวจ (File B) เพื่อให้ AI เทียบจุดต่างให้ทันที")

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
if st.button("🚀 เริ่มเปรียบเทียบเอกสาร", type="primary", use_container_width=True):
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
            
            status_box.write("🤖 AI กำลังอ่านและเทียบข้อความ ตาราง ตัวเลข...")
            
            prompt = """
            จงเปรียบเทียบ **เอกสาร B (ไฟล์ตรวจสอบ)** เทียบกับ **เอกสาร A (ไฟล์ตั้งต้น)** อย่างละเอียด
            ตรวจสอบว่าเนื้อหา ตัวเลข เงื่อนไข และรายละเอียดถูกต้องตรงกันหรือไม่
            
            กรุณารายงานผลเป็นภาษาไทย ดังนี้:
            1. **สรุปภาพรวม (Overview):** เอกสารตรงกันหรือไม่ มีจุดต่างสำคัญตรงไหนบ้าง
            2. **ตารางเปรียบเทียบจุดที่ต่างกัน (Discrepancies Table):** 
               - หัวข้อ/รายการ
               - ค่าในไฟล์ตั้งต้น (File A)
               - ค่าในไฟล์ตรวจสอบ (File B)
               - หมายเหตุ / ผลกระทบ
            3. **ข้อเสนอแนะเพิ่มเติม**
            """
            
            # อัปเดตโมเดลเป็น gemini-3.8-flash ตามคำแนะนำของระบบ
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[g_a, g_b, prompt]
            )
            
            status_box.update(label="✅ เสร็จเรียบร้อย!", state="complete", expanded=False)
            st.markdown(response.text)
            
            st.divider()
            st.download_button(
                label="📥 ดาวน์โหลดรายงานผลเป็นไฟล์ข้อความ (.txt)",
                data=response.text,
                file_name="comparison_report.txt",
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

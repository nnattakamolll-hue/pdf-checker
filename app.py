import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os
import time

st.set_page_config(page_title="PDF Description Strict Checker", page_icon="📄", layout="wide")

st.title("📄 ระบบตรวจสอบความถูกต้อง Description สินค้าด้วย AI")
st.caption("เปรียบเทียบไฟล์ตั้งต้น (File A) กับไฟล์ตรวจสอบ (File B) เน้นเช็ค Description แบบคำต่อคำ พร้อมระบบกันหลุด (Auto-Retry)")

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
if st.button("🚀 เริ่มตรวจสอบ Description", type="primary", use_container_width=True):
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
            
            status_box.write("🤖 AI กำลังตรวจสอบ Description แบบเข้มงวด...")
            
            # เพิ่มเงื่อนไขสั่งห้ามใช้ <br> ในตาราง
            prompt = """
            จงเปรียบเทียบเอกสาร B (ไฟล์ตรวจสอบ) กับ เอกสาร A (ไฟล์ตั้งต้น) โดยเน้นเจาะจงตรวจสอบที่ "Description (รายละเอียด/คำอธิบายสินค้า)" เป็นหลักอย่างเข้มงวดที่สุด
            
            เงื่อนไขการตรวจสอบ:
            1. รายละเอียดสินค้า (Description) ในไฟล์ตรวจสอบ (B) ต้องตรงกับไฟล์ตั้งต้น (A) แบบคำต่อคำ ตัวอักษรต่อตัวอักษร (Exact Match) ห้ามมีข้อความตกหล่น เพิ่มเติม หรือผิดเพี้ยนเด็ดขาด
            2. หากมีจุดไหนที่ไม่ตรงกันแม้แต่ตัวอักษรเดียว หรือมีความคลาดเคลื่อน ให้ทำรายงานระบุออกมาทันทีในรูปแบบตาราง Markdown
            3. **ข้อห้ามสำคัญ:** ห้ามใช้แท็ก HTML เช่น `<br>` ในตารางเด็ดขาด หากต้องการแบ่งบรรทัดในช่องตาราง ให้ใช้การขึ้นบรรทัดใหม่ตามปกติ หรือใช้สัญลักษณ์ bullet (-) แยกข้อความแทน เพื่อให้อ่านง่ายและสะอาดตาที่สุด
            4. หากตรงกันทั้งหมดทุกรายการ ให้สรุปผลว่า "Description ตรงกันทุกประการ 100%"
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
            
            status_box.update(label="✅ ตรวจสอบเสร็จสิ้น!", state="complete", expanded=False)
            st.markdown(response.text)
            
            st.divider()
            st.download_button(
                label="📥 ดาวน์โหลดรายงานผลเป็นไฟล์ข้อความ (.txt)",
                data=response.text,
                file_name="description_report.txt",
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

import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os
import time

st.set_page_config(
    page_title="PDF PO & Quotation Auditor", 
    page_icon="📄", 
    layout="wide"
)

st.title("📄 ระบบตรวจสอบและเปรียบเทียบไฟล์ PDF (PO & Quotation) อัตโนมัติ")
st.caption("เปรียบเทียบไฟล์ Quotation ตั้งต้น (รองรับหลายไฟล์) กับ PO ตรวจสอบชื่อ ขนาด สเปก และรายละเอียดทุกหน้าอย่างแม่นยำ")

api_key = st.text_input("กรอก Gemini API Key ของคุณที่นี่", type="password", help="วาง API Key ที่ได้มาจาก Google AI Studio ตรงนี้")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("1. ไฟล์ตั้งต้น (Baseline - Quotation หลายไฟล์ได้)")
    files_a = st.file_uploader("เลือกไฟล์ PDF Quotation (เลือกได้หลายไฟล์พร้อมกัน)", type=["pdf"], key="file_quotation", accept_multiple_files=True)

with col2:
    st.subheader("2. ไฟล์ที่ต้องการตรวจ (To Check - PO)")
    file_b = st.file_uploader("เลือกไฟล์ PDF PO", type=["pdf"], key="file_po")

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

if st.button("🚀 เริ่มตรวจสอบชื่อ ขนาด สเปก และเปรียบเทียบไฟล์ PDF ทั้งหมด", type="primary", use_container_width=True):
    if not api_key:
        st.error("กรุณากรอก Gemini API Key ในช่องด้านบนก่อนครับ")
    elif not files_a or not file_b:
        st.error("กรุณาอัปโหลดไฟล์ PDF ตั้งต้น (Quotation) อย่างน้อย 1 ไฟล์ และไฟล์ PO ให้ครบถ้วนครับ")
    else:
        status_box = st.status("กำลังประมวลผลตรวจสอบรายละเอียดทุกหน้า...", expanded=True)
        uploaded_files = []
        
        try:
            client = genai.Client(api_key=api_key)
            
            status_box.write("กำลังส่งไฟล์ตั้งต้น (Quotation) ทั้งหมดเข้าสู่ระบบ AI...")
            g_a_list = []
            for idx, f_a in enumerate(files_a):
                status_box.write(f"กำลังอัปโหลดไฟล์ตั้งต้นที่ {idx+1}: {f_a.name}...")
                g_a = upload_to_gemini(client, f_a)
                g_a_list.append(g_a)
                uploaded_files.append(g_a.name)
            
            status_box.write("กำลังส่งไฟล์ PO เข้าสู่ระบบ...")
            g_b = upload_to_gemini(client, file_b)
            uploaded_files.append(g_b.name)
            
            status_box.write("AI กำลังสแกนตรวจเทียบชื่อ ขนาด สเปก และรายละเอียดสินค้าใน PO ทุกหน้า...")
            
            prompt = '''จงเปรียบเทียบเอกสาร B (ไฟล์ PO ที่ต้องการตรวจสอบ) กับกลุ่มเอกสาร A (ไฟล์ตั้งต้น Quotation ทั้งหมดที่ให้ไป) อย่างละเอียดถี่ถ้วน "ทุกหน้า ทุกแผ่นแบบครบถ้วน 100%"

หลักการตรวจสอบความถูกต้อง:
1. ตรวจสอบทีละหน้าอย่างเป็นระบบ ห้ามข้ามหน้าใดๆ ทั้งสิ้น
2. ยึดข้อมูลรวมในกลุ่มเอกสาร A (Quotation ทั้งหมด) เป็นความถูกต้องหลัก 100%
3. **ตรวจสอบรายละเอียดที่ปรากฏใน PO (File B) ทั้งหมด** เช่น ชื่อสินค้า, ขนาด (Dimensions), สเปกเชิงเทคนิค (Specifications), รหัสรุ่น (Model/Part Numbers), ราคา, และจำนวน ว่าเมื่อเทียบกับใบตั้งต้นแล้ว มีการใส่รายละเอียดมาผิดพลาด ย่อข้อความจนตกหล่น หรือไม่ตรงกับต้นฉบับหรือไม่
4. หากพบว่ารายละเอียด ขนาด หรือชื่อใน PO ไม่ตรงกับต้นฉบับ หรือถูกตัดทอนจนข้อมูลสำคัญหายไป ให้ถือว่าผิดพลาดและต้องแก้ไข
5. ระบุเลขหน้าให้ตรงกับหน้าจริงในเอกสาร PO ที่พบความผิดพลาด

รูปแบบรายงานสรุป:
### ตารางเปรียบเทียบและผลการตรวจสอบ (ชื่อ ขนาด และสเปก)
แสดงผลเป็นตาราง Markdown 5 คอลัมน์หลัก:
1. หน้าที่พบใน PO (Page)
2. รายการ / รหัสสินค้า
3. รายละเอียดในกลุ่ม Quotation A (ถูกต้องตามต้นฉบับ)
4. รายละเอียดที่ระบุมาใน PO B (ที่พบว่าผิด ขนาดเพี้ยน หรือตกหล่น)
5. ผลการตรวจสอบ / สิ่งที่ต้องแก้ไข

### สรุปภาพรวมทุกหน้า
สรุปภาพรวมการตรวจสอบรายละเอียดทั้งหมด'''
            
            max_retries = 5
            retry_delay = 5
            response = None
            success = False
            
            config = types.GenerateContentConfig(
                max_output_tokens=8192,
                temperature=0.1
            )
            
            contents_list = g_a_list + [g_b, prompt]
            
            for attempt in range(max_retries):
                try:
                    status_box.write(f"กำลังวิเคราะห์รายละเอียด (พยายามครั้งที่ {attempt+1}/{max_retries})...")
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=contents_list,
                        config=config
                    )
                    success = True
                    break
                except Exception as api_err:
                    if ("503" in str(api_err) or "UNAVAILABLE" in str(api_err)) and attempt < max_retries - 1:
                        status_box.warning(f"เซิร์ฟเวอร์หนาแน่น กำลังลองใหม่ในอีก {retry_delay} วินาที...")
                        time.sleep(retry_delay)
                        retry_delay += 3
                    else:
                        raise api_err
            
            if not success or not response:
                raise Exception("เซิร์ฟเวอร์หนาแน่นเกินไป โปรดลองกดปุ่มเริ่มตรวจสอบใหม่อีกครั้ง")
            
            raw_text = response.text if hasattr(response, 'text') else str(response)
            clean_output = raw_text.replace("<br>", " ").replace("<br/>", " ").replace("<BR>", " ")
            
            status_box.update(label="ตรวจสอบรายละเอียดและเปรียบเทียบเอกสารเรียบร้อยสมบูรณ์!", state="complete", expanded=False)
            
            st.markdown(clean_output)
            
            st.divider()
            st.download_button(
                label="ดาวน์โหลดรายงานผลการตรวจสอบ (.txt)",
                data=clean_output,
                file_name="po_audit_report.txt",
                mime="text/plain"
            )

        except Exception as e:
            status_box.update(label="เกิดข้อผิดพลาดในการประมวลผล", state="error", expanded=True)
            st.error(f"รายละเอียด: {str(e)}")
            
        finally:
            if uploaded_files and 'client' in locals():
                for name in uploaded_files:
                    try:
                        client.files.delete(name=name)
                    except:
                        pass

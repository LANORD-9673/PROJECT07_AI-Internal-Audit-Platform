STREAMLIT VERSION: Read README.md first. On Windows run START_STREAMLIT.bat. For Streamlit Cloud use streamlit_app.py as entrypoint.

LEGACY REACT / FASTAPI INSTRUCTIONS BELOW:

PROJECT 07 v1.4 — LLM + PYTHON + HUMAN REVIEW
=================================================
BAN SOURCE DA CHINH SUA; DU LIEU GIA LAP, KHONG PHAI SAN PHAM PRODUCTION.

1. Giai nen ZIP vao thu muc rieng. Mo thu muc project-07 bang VS Code.
2. Cai Python 3.12/3.13, Node.js + npm va Ollama tren may Windows.
3. Doc demo/POL-LOAN-01_v1.0.txt va demo/employee_authority.csv.
   Sau khi nhom doi chieu policy, authority va pham vi demo, chay o ROOT project-07:
     Copy-Item .env.example .env
   .env chi cau hinh baseline gia lap dinh kem. Neu file nguon thay doi, hash
   khong con khop: can nguoi review nguon moi; KHONG tu thay hash de bo chan.
4. Chuan bi model local:
     ollama pull qwen3:4b
     ollama list
   Ollama can dang chay. Neu chua co service, mo terminal rieng: ollama serve
5. Double-click START_NEXUS.bat (nam ngay trong project-07).
   Hoac mo 2 terminal PowerShell o ROOT project-07:
     powershell -ExecutionPolicy Bypass -File .\start_backend.ps1
     powershell -ExecutionPolicy Bypass -File .\start_frontend.ps1
   Cho backend 'Application startup complete' va frontend hien URL.
6. Mo http://localhost:5173. Trang dau la 'Vai tro LLM & con nguoi'.

IMPORT DEMO TAI 'HO SO KIEM TOAN':
- Policy: demo/POL-LOAN-01_v1.0.txt
  policy_id=POL-LOAN-01; policy_set_id=BASELINE;
  effective_from=2026-10-08T00:00:00+07:00
- Loans: demo/loans_60.csv; dataset_id=DEMO-60
- Authority: demo/employee_authority.csv; authority_id=DEMO-AUTH
- Chon dung 3 snapshots -> tao Audit Run.

WORKFLOW BAT BUOC:
LLM1 sinh RCM -> nguoi doc policy goc va duyet RCM
-> LLM2 sinh plan -> nguoi duyet plan
-> Python chay T01-T03 -> nguoi review TAT CA EXCEPTION
-> LLM3 sinh findings -> nguoi CONFIRMED tung finding
-> LLM4 sinh report -> nguoi review report demo.
Moi quyet dinh review can ten va ly do do nguoi tu nhap.
Findings co policy quote, source snapshot, result ID, row/line va observed values.
Bao cao co evidence appendix va deterministic counts.
Report duoc review van co publication_status DRAFT. FINAL that bi chan.

MOT SO LOI VA CACH XU LY:
REVIEW_REQUIRED: doc buoc chua duyet; kiem tra .env/hash; khong bo gate.
MODEL_UNAVAILABLE: kiem tra Ollama service va ollama list.
MODEL_SCHEMA_ERROR/MISSING_EVIDENCE: model sai schema/quote/mapping; doc
nguon va tao lai ban nhap. Output bi tu choi, khong tu gia lam thanh cong.
INCOMPLETE_PLAN: RCM/plan phai bao phu T01,T02,T03; tao lai RCM/plan.
INCOMPLETE_FINDINGS: model chua lien ket het exception da xac nhan; tao lai.
CONTEXT_LIMIT: demo vuot gioi han context; can nhom thu hep scope co review.
Neu RCM/PLAN da duyet, tao Run moi khi can doi noi dung.
Sua review result se vo hieu findings/report cu; sua review finding se vo hieu
report cu. Sau khi report duoc duyet demo, Run bi khoa voi cac thay doi nay.

KIEM THU (ROOT project-07):
     python -m pip install -r backend/requirements.txt
     python -m pytest backend/tests -q
     cd frontend
     npm ci
     npm run build
API tai http://localhost:8000/docs

DOC THEM:
- docs/HUONG_DAN_GIANG_VIEN.md: yeu cau, phan vai, kich ban thuyet trinh.
- docs/NHAT_KY_LLM_LAP_TRINH.md: nhat ky ho tro AI va muc nhom can bo sung.
- docs/LLM_EVALUATION_REVIEW.csv: phieu cham ngu nghia LLM live (con trong).
- TEST_REPORT.txt: ket qua da chay va cac gioi han chua kiem chung.

KHONG DONG GOI .venv, node_modules, SQLite cu hoac API key.
Windows/LLM live can duoc nhom chay lai tren may trinh bay.

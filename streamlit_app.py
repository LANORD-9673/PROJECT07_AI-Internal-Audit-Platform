import hashlib
import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='NEXUS | Project 07', page_icon='🏦', layout='wide')

# Deployment settings are controlled by the app owner, never by visitors.
KEYS = ('GEMINI_API_KEY', 'PROJECT07_GEMINI_MODEL', 'PROJECT07_GEMINI_TIMEOUT',
        'PROJECT07_APPROVED_BASELINE_SHA256', 'PROJECT07_APPROVED_AUTHORITY_SHA256',
        'PROJECT07_AUTHORITY_APPROVAL_REFERENCE', 'PROJECT07_DB_PATH',
        'PROJECT07_VAULT_MASTER_KEY', 'PROJECT07_VAULT_DIR', 'PROJECT07_GEMINI_MAX_RETRIES')
try:
    for key in KEYS:
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])
except FileNotFoundError:
    pass
os.environ['PROJECT07_REQUIRE_GATES'] = '1'

from streamlit_runtime import initialize, request, ApiError


@st.cache_resource
def setup_backend():
    initialize()
    return True


setup_backend()


def api(path):
    return request('GET', path)


def mutate(path, payload=None, **kwargs):
    return request('POST', path, json=payload, **kwargs) if payload is not None else request('POST', path, **kwargs)


def action(label, path, payload=None, disabled=False, key=None):
    if st.button(label, disabled=disabled, key=key or path, type='primary'):
        try:
            with st.spinner('Đang xử lý…'):
                mutate(path, payload)
            st.session_state['notice'] = 'Thao tác hoàn tất. Kết quả đã được lưu vào audit trail.'
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))


def download(data, name, key):
    st.download_button('Tải JSON và bằng chứng', json.dumps(data, ensure_ascii=False, indent=2),
                       file_name=name, mime='application/json', key=key)


def review_form(title, path, key, extra=None, decision_key=None, disabled=False):
    with st.form(key):
        st.markdown(f'**{title}**')
        reviewer = st.text_input('Người review', key=key + '_reviewer')
        reason = st.text_area('Căn cứ / ghi chú review', key=key + '_reason')
        payload = dict(extra or {})
        if decision_key:
            payload[decision_key] = st.selectbox('Kết luận', ['CONFIRMED', 'NEEDS_FOLLOWUP', 'REJECTED'])
        checked = st.checkbox('Tôi đã đối chiếu nguồn và bằng chứng liên quan')
        submitted = st.form_submit_button('Lưu review', disabled=disabled)
    if submitted:
        if not checked or not reviewer.strip() or not reason.strip():
            st.error('Cần đối chiếu bằng chứng, nhập người review và căn cứ trước khi lưu.')
        else:
            try:
                mutate(path, dict(payload, reviewer=reviewer, reason=reason))
                st.session_state['notice'] = 'Đã lưu review của con người.'
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))


st.title('NEXUS — AI Internal Audit')
st.caption('PROJECT 07 · LLM soạn bản nháp · Python kiểm tra dữ liệu · Con người review và quyết định')
if 'notice' in st.session_state:
    st.success(st.session_state.pop('notice'))

pages = ['Vai trò & cấu hình', 'Bảo vệ dữ liệu', 'Dữ liệu & Audit Run', 'RCM', 'Test Plan', 'Tests & Exceptions', 'Findings', 'Report', 'Evaluation']
page = st.sidebar.radio('Quy trình kiểm toán', pages)
run_list = api('/audit-runs')
run_ids = [x['run_id'] for x in run_list]
labels = {x['run_id']: x['audit_name'] + ' · ' + x['run_id'][:8] for x in run_list}
selected = st.session_state.get('active_run')
rid = st.sidebar.selectbox('Audit Run', run_ids, index=run_ids.index(selected) if selected in run_ids else 0,
                           format_func=lambda x: labels[x]) if run_ids else None
if rid:
    st.session_state['active_run'] = rid
st.sidebar.caption('Demo dùng chung dữ liệu, chưa xác thực người duyệt. Chỉ dùng dữ liệu giả lập.')
st.sidebar.button('Làm mới dữ liệu', on_click=lambda: None)

if page == 'Vai trò & cấu hình':
    st.subheader('AI hỗ trợ ở đâu, con người cần làm gì?')
    st.dataframe(pd.DataFrame([
        ['Viết code', 'Hỗ trợ thiết kế, tạo code và gợi ý sửa lỗi', 'Đọc diff, kiểm chứng nghiệp vụ, test và duyệt PR'],
        ['Policy → RCM', 'LLM1 trích xuất risk/control và quote', 'Đối chiếu policy gốc, duyệt RCM'],
        ['RCM → Test Plan', 'LLM2 soạn thủ tục và evidence', 'Duyệt kế hoạch và phạm vi'],
        ['Data → Exceptions', 'Python chạy T01, T02, T03', 'Xác minh từng exception'],
        ['Exceptions → Findings', 'LLM3 viết finding gắn bằng chứng', 'Review từng finding'],
        ['Findings → Report', 'LLM4 tổng hợp báo cáo DRAFT', 'Review báo cáo; không tự coi là phát hành FINAL'],
    ], columns=['Bước', 'LLM / Python', 'Con người']), hide_index=True, width='stretch')
    st.info('Streamlit chạy giao diện Python và backend trong cùng ứng dụng. Không cần deploy FastAPI riêng hoặc build React.')
    st.markdown('**Trạng thái cấu hình**')
    st.write('Provider: **Gemini API — Google AI Studio**')
    st.write('API key: ' + ('đã cấu hình' if os.environ.get('GEMINI_API_KEY', '').strip() else 'chưa cấu hình GEMINI_API_KEY'))
    st.write('Model: ' + os.environ.get('PROJECT07_GEMINI_MODEL', 'gemini-3.8-flash'))
    st.caption('Chỉ kiểm tra cấu hình; chưa chứng minh kết nối hoặc chất lượng model. API key không hiển thị trên giao diện.')
    if st.button('Kiểm tra key và danh sách model', key='gemini_check'):
        try:
            with st.spinner('Đang đọc metadata model từ Google…'):
                checked = mutate('/llm/check')
            st.success('Google chấp nhận truy cập danh sách model. Chưa kiểm chứng việc tạo nội dung.')
            if not checked['configured_model_listed']:
                st.warning('Model đang cấu hình chưa có trong danh sách trả về. Chọn model hỗ trợ generateContent từ danh sách dưới và cập nhật Secrets.')
            st.json(checked)
        except ApiError as exc:
            st.error(str(exc))
    pins = all(os.environ.get(x, '').strip() for x in ('PROJECT07_APPROVED_BASELINE_SHA256', 'PROJECT07_APPROVED_AUTHORITY_SHA256', 'PROJECT07_AUTHORITY_APPROVAL_REFERENCE'))
    st.write('Hồ sơ phê duyệt baseline: ' + ('đã cấu hình — backend vẫn đối chiếu hash khi chạy' if pins else 'chưa đủ; Tests sẽ bị chặn'))
    with st.expander('SHA256 của bộ demo để chủ ứng dụng đối chiếu'):
        for name in ('POL-LOAN-01_v1.0.txt', 'employee_authority.csv'):
            st.text(name)
            st.code(hashlib.sha256((ROOT / 'demo' / name).read_bytes()).hexdigest())
        st.caption('Hash không thay cho phê duyệt. Chỉ cấu hình Secrets sau khi con người đã rà soát đúng bộ tài liệu.')
    st.info('Nhập GEMINI_API_KEY trong Streamlit Secrets hoặc biến môi trường ở PyCharm. Không cần Ollama chạy trên laptop. Model lỗi sẽ dừng bước tương ứng; không thay thế bằng kết quả giả.')

elif page == 'Bảo vệ dữ liệu':
    from services.privacy import protect_file, read_table, suggest_columns, pseudonymize, PrivacyError
    st.subheader('Bảo vệ dữ liệu trước khi phân tích')
    st.info('File gốc được mã hóa AES-256-GCM ngay sau khi upload, nếu chủ app đã cấu hình khóa chủ. Bản mã giả giữ cấu trúc nguồn và cần auditor review trước khi tải hoặc import.')
    st.caption('Mã giả không phải dữ liệu ẩn danh tuyệt đối. Cột KEEP còn là dữ liệu có thể đọc được. Chỉ gửi bản đã review vào quy trình kiểm toán.')
    sample_path = ROOT / 'demo' / 'privacy_sample_loans_100.csv'
    if sample_path.is_file():
        st.download_button('Tải CSV giả lập 100 khoản vay để thử mã hóa', sample_path.read_bytes(),
                           'Nexus_Simulated_Loans_100.csv', 'text/csv', key='privacy_sample_download')
        st.caption('File hoàn toàn hư cấu: họ tên và địa chỉ giả lập, điện thoại/CCCD/tài khoản có tiền tố SIM, email example.test.')
    file = st.file_uploader('Chọn file bất kỳ để mã hóa — tối đa 10 MB', key='private_upload')
    if not os.environ.get('PROJECT07_VAULT_MASTER_KEY', '').strip():
        st.warning('Chủ app cần cấu hình PROJECT07_VAULT_MASTER_KEY trong Secrets trước khi dùng vault. Xem HUONG_DAN_BAO_VE_DU_LIEU.md.')
    if file and os.environ.get('PROJECT07_VAULT_MASTER_KEY', '').strip():
        raw = file.getvalue()
        fingerprint = hashlib.sha256(raw).hexdigest() + file.name
        job = st.session_state.get('private_job')
        if not job or job['fingerprint'] != fingerprint:
            try:
                protected = protect_file(raw, file.name)
                job = {'fingerprint': fingerprint, 'protected': protected}
                st.session_state['private_job'] = job
                st.session_state.pop('private_reviewed', None)
            except PrivacyError as exc:
                st.error(str(exc)); st.stop()
            except OSError:
                st.error('Không tạo được vault riêng tư; kiểm tra quyền ghi và cấu hình lưu trữ.'); st.stop()
        protected = job['protected']
        st.success('Đã mã hóa toàn bộ file và lưu khóa từng file dưới dạng đã được mã hóa trong vault máy chủ.')
        st.write('File ID: `' + protected['file_id'] + '`')
        st.download_button('Tải file gốc đã mã hóa', protected['encrypted_bytes'], protected['download_name'], 'application/octet-stream', key='encrypted_download')
        if Path(file.name).suffix.lower() in ('.csv', '.xlsx'):
            try:
                frame = read_table(raw, file.name)
            except PrivacyError as exc:
                st.warning(str(exc)); st.stop()
            st.write(f'Bảng đọc được: {len(frame)} dòng, {len(frame.columns)} cột. Xuất giữ đủ cột và thứ tự. XLSX chỉ hỗ trợ một sheet dữ liệu không có công thức/ảnh/chart.')
            with st.form('privacy_review_' + protected['file_id']):
                default_scope = st.session_state.setdefault('privacy_default_scope', 'AUDIT-' + os.urandom(8).hex())
                scope = st.text_input('Mã phạm vi kiểm toán — dùng cùng mã cho loans và authority để giữ liên kết ID', default_scope)
                plan = st.data_editor(pd.DataFrame(suggest_columns(frame)), hide_index=True, width='stretch',
                    disabled=['column', 'reason'], num_rows='fixed',
                    column_config={'action': st.column_config.SelectboxColumn('Xử lý cột', options=['TOKENIZE', 'MASK', 'KEEP'], required=True)})
                reviewer = st.text_input('Người review phương án bảo vệ')
                checked = st.checkbox('Tôi đã đối chiếu file gốc; hiểu các cột KEEP còn đọc được và đã xác nhận mục đích sử dụng')
                submitted = st.form_submit_button('Duyệt và xuất bản mã giả')
            if submitted:
                if not checked:
                    st.error('Cần con người review phương án xử lý cột.')
                else:
                    try:
                        edited = plan.to_dict('records')
                        reviewed = pseudonymize(frame, edited, scope, reviewer, protected['file_id'], source_bytes=raw, source_name=file.name)
                        reviewed['source_fingerprint'] = fingerprint
                        st.session_state['privacy_default_scope'] = scope.strip()
                        st.session_state['private_reviewed'] = reviewed
                        st.success('Đã tạo file đúng định dạng nguồn và bảng đối chiếu riêng để auditor tải xuống. Không ghi bảng đối chiếu mới xuống vault/DB/log.')
                    except PrivacyError as exc:
                        st.error(str(exc))
                    except OSError:
                        st.error('Không xử lý được file; chưa xuất bản mã giả.')
            reviewed = st.session_state.get('private_reviewed')
            if reviewed and reviewed['source_fingerprint'] == fingerprint:
                st.caption('Nếu đổi phương án hoặc scope, bấm Duyệt và xuất lại. Bản bên dưới là kết quả của lần duyệt đã lưu.')
                st.dataframe(reviewed['frame'].head(20), hide_index=True, width='stretch')
                st.download_button('1. Tải dữ liệu đã bảo vệ — đúng định dạng nguồn', reviewed['export_bytes'],
                                   reviewed['export_filename'], reviewed['export_mime'], key='protected_csv_download')
                st.warning('Bảng đối chiếu CSV và hồ sơ JSON đều chứa dữ liệu gốc. Auditor lưu ở nơi riêng có quyền truy cập phù hợp; không import bảng này vào workflow hoặc gửi cho LLM.')
                st.download_button('2. Tải bảng đối chiếu chi tiết cho auditor', reviewed['audit_mapping_csv_bytes'],
                                   'AUDITOR_ONLY_mapping_' + protected['file_id'] + '.csv', 'text/csv', key='auditor_mapping_download')
                st.download_button('3. Tải hồ sơ đối chiếu JSON có dữ liệu gốc', reviewed['audit_report_json_bytes'],
                                   'AUDITOR_ONLY_review_' + protected['file_id'] + '.json', 'application/json', key='auditor_review_download')
                st.caption('Bảng đối chiếu chỉ được giữ tạm trong RAM của phiên để phục vụ tải; tải và lưu riêng trước khi đóng/reboot app.')
                st.write('Mã tham chiếu bảng ánh xạ: `' + reviewed['mapping_reference'] + '`')
                with st.form('import_private_' + protected['file_id']):
                    source = st.selectbox('Import bản đã review vào workflow', ['loans', 'authorities'])
                    logical_id = st.text_input('Dataset/Authority ID', 'PROTECTED-DEMO')
                    imported = st.form_submit_button('Import CSV đã bảo vệ')
                if imported:
                    fields = {('dataset_id' if source == 'loans' else 'authority_id'): logical_id}
                    try:
                        result = mutate('/import/' + source, files={'file': ('protected.csv', reviewed['csv_bytes'])}, data=fields)
                        st.success('Đã import bản mã giả, snapshot ' + result['snapshot_id'])
                        st.caption('Bộ test vẫn chỉ hỗ trợ schema/baseline Project 07. Authority đã thay mã tạo hash mới, cần owner đối chiếu và cấu hình phê duyệt đúng snapshot.')
                    except ApiError as exc:
                        st.error(str(exc))
        else:
            st.caption('File này đã được mã hóa nguyên vẹn. Tự chọn phương án xử lý cột chỉ áp dụng với CSV/XLSX có cấu trúc.')
    st.warning('Vault local trên Streamlit Community Cloud không được xem là lưu trữ bền vững. Mất khóa chủ hoặc mất file khóa trong vault thì không thể giải mã; cần sao lưu có kiểm soát. Demo chưa có phân quyền tài khoản để dùng dữ liệu khách hàng thật.')

elif page == 'Dữ liệu & Audit Run':
    st.subheader('1. Import dữ liệu và tạo Audit Run')
    st.caption('Dữ liệu giả lập có sẵn; snapshot giữ hash và phiên bản để truy vết.')
    if st.button('Import bộ demo 60 khoản vay', type='primary'):
        try:
            definitions = [
                ('policies', 'POL-LOAN-01_v1.0.txt', {'policy_id': 'POL-LOAN-01', 'policy_set_id': 'BASELINE', 'effective_from': '2026-10-08T00:00:00+07:00'}),
                ('loans', 'loans_60.csv', {'dataset_id': 'DEMO-60'}),
                ('authorities', 'employee_authority.csv', {'authority_id': 'DEMO-AUTH'}),
            ]
            for endpoint, name, fields in definitions:
                mutate('/import/' + endpoint, files={'file': (name, (ROOT / 'demo' / name).read_bytes())}, data=fields)
            st.session_state['notice'] = 'Đã import bộ demo. Chọn snapshot bên dưới để tạo Audit Run.'
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
    with st.expander('Import file khác'):
        with st.form('upload'):
            kind = st.selectbox('Loại nguồn', ['policies', 'loans', 'authorities'])
            file = st.file_uploader('TXT / DOCX / PDF / CSV / XLSX', type=['txt', 'docx', 'pdf', 'csv', 'xlsx'])
            logical = st.text_input('Mã nguồn', 'POL-LOAN-01')
            policy_set = st.text_input('Policy set', 'BASELINE')
            effective = st.text_input('Ngày hiệu lực ISO 8601', '2026-10-08T00:00:00+07:00')
            submit = st.form_submit_button('Import file')
        if submit and file and kind in ('loans', 'authorities'):
            st.error('Dữ liệu bảng tùy chỉnh phải qua màn hình Bảo vệ dữ liệu; import bản mã giả sau khi review.')
        if submit and file and kind == 'policies':
            fields = {'policy_id': logical, 'policy_set_id': policy_set, 'effective_from': effective} if kind == 'policies' else {('dataset_id' if kind == 'loans' else 'authority_id'): logical}
            try:
                mutate('/import/' + kind, files={'file': (file.name, file.getvalue())}, data=fields)
                st.session_state['notice'] = 'Đã import snapshot mới.'
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))
    snaps = api('/snapshots')
    groups = {kind: [x for x in snaps if x['source_type'] == kind] for kind in ('policy', 'loans', 'authority')}
    if all(groups.values()):
        with st.form('create_run'):
            name = st.text_input('Tên cuộc kiểm toán', 'Project 07 — Demo tín dụng')
            chosen = {}
            for kind, field in [('policy', 'policy_snapshot_id'), ('loans', 'dataset_snapshot_id'), ('authority', 'authority_snapshot_id')]:
                options = groups[kind]
                item = st.selectbox(kind.title() + ' snapshot', range(len(options)), format_func=lambda i, options=options: f"{options[i]['filename']} · v{options[i]['version']} · {options[i]['snapshot_id'][:8]}")
                chosen[field] = options[item]['snapshot_id']
            submitted = st.form_submit_button('Tạo Audit Run')
        if submitted:
            try:
                result = mutate('/audit-runs', dict(chosen, audit_name=name))
                st.session_state['active_run'] = result['run_id']
                st.session_state['notice'] = 'Đã tạo Audit Run. Chuyển sang RCM để bắt đầu.'
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))
    else:
        st.info('Cần đủ policy, loans và authority trước khi tạo Audit Run.')
    st.dataframe(pd.DataFrame(snaps), hide_index=True, width='stretch')

else:
    if not rid:
        st.info('Import dữ liệu và tạo Audit Run trước khi tiếp tục.')
        st.stop()
    base = '/audit-runs/' + rid
    wf = api(base + '/workflow')
    docs = {d['kind']: d for d in wf['documents']}
    if page in ('RCM', 'Test Plan'):
        kind, route, rows = ('RCM', 'rcm', 'controls') if page == 'RCM' else ('PLAN', 'test-plan', 'tests')
        document = docs.get(kind)
        approved = bool(document and document['state'] == 'APPROVED')
        st.subheader('2. LLM1 — RCM' if kind == 'RCM' else '3. LLM2 — Audit Test Plan')
        action('Tạo bản nháp bằng LLM', base + '/' + route + '/generate', disabled=approved)
        if kind == 'RCM':
            with st.expander('Policy nguồn để đối chiếu'):
                st.text(api('/policies/' + wf['run']['policy_snapshot_id'] + '/text')['extracted_text'])
        if document:
            st.write('Trạng thái: **' + document['state'] + '** · Model: ' + document['model'])
            st.dataframe(pd.DataFrame(document['payload'].get(rows, [])), hide_index=True, width='stretch')
            st.json(document['payload'])
            download(document, kind + '_' + rid + '.json', kind + '_download')
            review_form('Con người duyệt ' + kind, base + '/' + route + '/approve', kind + '_approve', disabled=approved)

    elif page == 'Tests & Exceptions':
        st.subheader('4. Python tests & Human review')
        st.caption('Backend chỉ chạy sau khi RCM và Test Plan được duyệt, đúng baseline và authority đã được đối chiếu hash.')
        action('Chạy T01–T03 bằng Python', base + '/tests/execute')
        results = api(base + '/results')['results']
        reviews = {x['result_id']: x['review_state'] for x in wf['result_reviews']}
        for result in results:
            result['human_review'] = reviews.get(result['result_id'], 'PENDING')
        if results:
            st.dataframe(pd.DataFrame([{k: x.get(k) for k in ('row_id', 'test_id', 'test_result', 'reason_code', 'human_review')} for x in results]), hide_index=True, width='stretch')
            download(results, 'results_' + rid + '.json', 'results_download')
            pending = [x for x in results if x['test_result'] == 'EXCEPTION' and x['human_review'] not in ('CONFIRMED', 'REJECTED')]
            st.write(f'Exceptions còn chờ xử lý: **{len(pending)}**')
            selected_result = st.selectbox('Chọn kết quả để đọc bằng chứng và review', range(len(results)), format_func=lambda i: f"{results[i]['row_id']} · {results[i]['test_id']} · {results[i]['test_result']} · {results[i]['human_review']}")
            item = results[selected_result]
            st.json(item)
            review_form('Review kết quả đang chọn', base + '/results/' + item['result_id'] + '/review', 'result_' + item['result_id'], decision_key='review_state')

    elif page == 'Findings':
        st.subheader('5. LLM3 — Draft findings')
        st.caption('Cần xử lý từng exception trước khi tạo findings. Bản nháp phải gắn policy quote và evidence_result_ids hợp lệ.')
        action('Tạo findings bằng LLM', base + '/findings/generate')
        document = docs.get('FINDINGS')
        if document:
            download(document, 'findings_' + rid + '.json', 'findings_download')
            states = {x['finding_key']: x['state'] for x in wf['finding_reviews']}
            for item in document['payload']['findings']:
                with st.expander(item['finding_key'] + ' — ' + item['title'] + ' · ' + states.get(item['finding_key'], 'PENDING'), expanded=True):
                    for key in ('criteria', 'condition', 'risk', 'recommendation'):
                        st.markdown('**' + key.title() + '**')
                        st.write(item[key])
                    st.json({'criteria_evidence': item['criteria_evidence'], 'evidence_details': item['evidence_details']})
                    review_form('Review finding', '/findings/' + item['finding_key'] + '/review', 'finding_' + rid + '_' + item['finding_key'], extra={'run_id': rid}, decision_key='state')

    elif page == 'Report':
        st.subheader('6. LLM4 — Báo cáo kiểm toán DRAFT')
        action('Tạo báo cáo từ findings đã xác nhận', base + '/report/generate', disabled=docs.get('REPORT', {}).get('state') == 'APPROVED')
        document = docs.get('REPORT')
        if document:
            st.write('Trạng thái review: **' + document['state'] + '** · Phát hành: **DRAFT**')
            for key in ('executive_summary', 'scope', 'methods', 'findings_summary', 'limitations', 'recommendations'):
                st.markdown('### ' + key.replace('_', ' ').title())
                st.write(document['payload'][key])
            with st.expander('Counts và phụ lục bằng chứng'):
                st.json(document['payload'])
            download(document, 'report_DRAFT_' + rid + '.json', 'report_download')
            review_form('Con người review báo cáo', base + '/report/approve', 'report_approve', disabled=document['state'] == 'APPROVED')
            st.caption('Demo chưa có xác thực/phân quyền người duyệt, nên báo cáo vẫn DRAFT và backend chặn phát hành FINAL.')

    elif page == 'Evaluation':
        st.subheader('7. Evaluation & audit trail')
        evaluation = api(base + '/evaluation')
        st.json(evaluation['structural_metrics'])
        st.caption('Chỉ số cấu trúc không chứng minh độ chính xác nghiệp vụ hoặc semantic groundedness của LLM.')
        with st.expander('Rule regression benchmark', expanded=True):
            st.json(evaluation['regression_benchmark'])
        st.markdown('**Lời gọi LLM thực tế**')
        st.dataframe(pd.DataFrame(evaluation['llm_calls']), hide_index=True, width='stretch')
        st.markdown('**Audit trail**')
        events = api(base + '/events')
        st.dataframe(pd.DataFrame(events), hide_index=True, width='stretch')
        download({'evaluation': evaluation, 'events': events}, 'evaluation_' + rid + '.json', 'eval_download')

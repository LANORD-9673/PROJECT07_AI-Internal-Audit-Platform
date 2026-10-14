"""UI integration check without a model or network; does not evaluate LLM quality."""
import os
import io
import base64
from unittest.mock import patch
import tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    os.environ['PROJECT07_DB_PATH'] = str(Path(tmp) / 'ui.sqlite')
    app = AppTest.from_file(str(root / 'streamlit_app.py'), default_timeout=30).run()
    assert not app.exception, app.exception
    assert any('NEXUS' in x.value for x in app.markdown)
    app.sidebar.toggle[0].set_value(False).run()
    assert not app.exception
    next(b for b in app.button if b.key == 'nav_Bảo vệ dữ liệu').click().run()
    assert app.session_state['nx_page'] == 'Bảo vệ dữ liệu'
    app.sidebar.toggle[0].set_value(True).run()
    app.sidebar.selectbox[0].set_value('Dữ liệu & Audit Run').run()
    next(b for b in app.button if b.label == 'Import bộ demo 60 khoản vay').click().run()
    assert not app.exception, app.exception
    next(b for b in app.button if b.label == 'Tạo Audit Run').click().run()
    assert not app.exception, app.exception
    assert len(app.sidebar.selectbox[1].options) == 1
    for page in ('Bảo vệ dữ liệu', 'RCM', 'Test Plan', 'Tests & Exceptions', 'Findings', 'Report', 'Evaluation'):
        app.sidebar.selectbox[0].set_value(page).run()
        assert not app.exception, (page, app.exception)
    app.sidebar.selectbox[0].set_value('Tests & Exceptions').run()
    next(b for b in app.button if b.label == 'Chạy T01–T03 bằng Python').click().run()
    assert not app.exception, app.exception
    assert app.error and 'REVIEW_REQUIRED' in app.error[0].value
    # Exercise automatic file encryption and mandatory review UI with a synthetic upload.
    os.environ['PROJECT07_VAULT_MASTER_KEY'] = base64.b64encode(os.urandom(32)).decode()
    os.environ['PROJECT07_VAULT_DIR'] = str(Path(tmp) / 'private-vault')
    uploaded = io.BytesIO(b'full_name,amount_vnd,note\nSecret Person,100000,private free text\n')
    uploaded.name = 'customer.csv'
    with patch('streamlit.file_uploader', return_value=uploaded):
        app.sidebar.selectbox[0].set_value('Bảo vệ dữ liệu').run()
        assert not app.exception, app.exception
        assert list((Path(tmp) / 'private-vault' / 'keys').glob('*.key.enc'))
        next(b for b in app.button if b.label == 'Duyệt và xuất bản mã giả').click().run()
        assert app.error and 'con người review' in app.error[0].value
        next(x for x in app.text_input if x.label == 'Người review phương án bảo vệ').set_value('UI test reviewer')
        next(x for x in app.checkbox if 'Tôi đã đối chiếu file gốc' in x.label).check()
        next(b for b in app.button if b.label == 'Duyệt và xuất bản mã giả').click().run()
        assert not app.exception, app.exception
        reviewed = app.session_state['private_reviewed']
        assert b'Secret Person' not in reviewed['csv_bytes']
        assert b'private free text' not in reviewed['csv_bytes']
        assert not list((Path(tmp) / 'private-vault' / 'maps').glob('*.map.enc'))
        assert b'Secret Person' in reviewed['audit_mapping_csv_bytes']
        assert b'full_name,amount_vnd,note' in reviewed['export_bytes']
print('PASS: workflow UI and gates; automatic archive encryption and reviewed pseudonymization UI. No live model called.')

"""UI integration check without a model or network; does not evaluate LLM quality."""
import os
import tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    os.environ['PROJECT07_DB_PATH'] = str(Path(tmp) / 'ui.sqlite')
    app = AppTest.from_file(str(root / 'streamlit_app.py'), default_timeout=30).run()
    assert not app.exception, app.exception
    assert 'NEXUS' in app.title[0].value
    app.sidebar.radio[0].set_value('Dữ liệu & Audit Run').run()
    next(b for b in app.button if b.label == 'Import bộ demo 60 khoản vay').click().run()
    assert not app.exception, app.exception
    next(b for b in app.button if b.label == 'Tạo Audit Run').click().run()
    assert not app.exception, app.exception
    assert len(app.sidebar.selectbox[0].options) == 1
    for page in ('RCM', 'Test Plan', 'Tests & Exceptions', 'Findings', 'Report', 'Evaluation'):
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, (page, app.exception)
    app.sidebar.radio[0].set_value('Tests & Exceptions').run()
    next(b for b in app.button if b.label == 'Chạy T01–T03 bằng Python').click().run()
    assert not app.exception, app.exception
    assert app.error and 'REVIEW_REQUIRED' in app.error[0].value
print('PASS: Streamlit startup, demo import, run creation, all workflow pages, backend gate enforcement. No live model called.')

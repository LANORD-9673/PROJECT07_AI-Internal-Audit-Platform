"""Local protection: authenticated file encryption and reviewed table pseudonymization.
No Gemini calls. A private vault is not a substitute for authentication or persistent storage.
"""
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import re
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

MAX_BYTES = 10 * 1024 * 1024
ACTIONS = {'TOKENIZE', 'MASK', 'KEEP', 'REMOVE'}  # REMOVE accepted as legacy alias of MASK.


class PrivacyError(ValueError):
    pass


def b64(raw): return base64.b64encode(raw).decode('ascii')
def unb64(text): return base64.b64decode(text, validate=True)


def master_key():
    value = os.environ.get('PROJECT07_VAULT_MASTER_KEY', '').strip()
    try:
        key = unb64(value)
        if len(key) != 32: raise ValueError()
    except (ValueError, TypeError):
        raise PrivacyError('Chủ app cần cấu hình PROJECT07_VAULT_MASTER_KEY: khóa ngẫu nhiên 32 byte, dạng Base64.')
    return key


def vault_dirs():
    root = Path(os.environ.get('PROJECT07_VAULT_DIR', str(Path(__file__).resolve().parents[1] / 'private_vault'))).expanduser()
    paths = [root, root / 'keys', root / 'encrypted', root / 'maps']
    for path in paths:
        if path.is_symlink(): raise PrivacyError('Vault không được là symbolic link.')
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path, 0o700)
    return paths[1:]


def private_write(path, raw):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


def seal(key, raw, aad):
    nonce = os.urandom(12)
    return {'nonce': b64(nonce), 'ciphertext': b64(AESGCM(key).encrypt(nonce, raw, aad))}


def open_sealed(key, obj, aad):
    return AESGCM(key).decrypt(unb64(obj['nonce']), unb64(obj['ciphertext']), aad)


def valid_id(value):
    if not re.fullmatch(r'[0-9a-f]{32}', value): raise PrivacyError('File ID không hợp lệ.')
    return value


def protect_file(raw, filename):
    if not raw or len(raw) > MAX_BYTES: raise PrivacyError('File phải có dữ liệu và không vượt 10 MB.')
    master = master_key()
    keys, encrypted, maps = vault_dirs()
    file_id = uuid.uuid4().hex
    key = AESGCM.generate_key(bit_length=256)
    payload = json.dumps({'filename': Path(filename.replace('\\', '/')).name,
                          'sha256': hashlib.sha256(raw).hexdigest(), 'data': b64(raw)}, ensure_ascii=False).encode()
    package = {'format': 'NEXUS-AES256GCM-v1', 'file_id': file_id,
               **seal(key, payload, ('file:' + file_id).encode())}
    wrapped = json.dumps(seal(master, key, ('key:' + file_id).encode())).encode()
    output = json.dumps(package).encode()
    created = []
    try:
        for path, content in [(keys / (file_id + '.key.enc'), wrapped), (encrypted / (file_id + '.nexus.enc'), output)]:
            private_write(path, content)
            created.append(path)
    except OSError:
        for path in created: path.unlink(missing_ok=True)
        raise PrivacyError('Không lưu được file/khóa trong vault. Kiểm tra quyền ghi và dung lượng máy chủ.')
    return {'file_id': file_id, 'encrypted_bytes': output, 'download_name': file_id + '.nexus.enc',
            'original_sha256': hashlib.sha256(raw).hexdigest()}


def restore_file(package_bytes):
    """Admin/local CLI only. Never mount this as a public endpoint."""
    package = json.loads(package_bytes)
    if package.get('format') != 'NEXUS-AES256GCM-v1': raise PrivacyError('Định dạng không hợp lệ.')
    file_id = valid_id(package['file_id'])
    keys, _, _ = vault_dirs()
    wrapped = json.loads((keys / (file_id + '.key.enc')).read_bytes())
    key = open_sealed(master_key(), wrapped, ('key:' + file_id).encode())
    payload = json.loads(open_sealed(key, package, ('file:' + file_id).encode()))
    raw = unb64(payload['data'])
    if hashlib.sha256(raw).hexdigest() != payload['sha256']: raise PrivacyError('Checksum mismatch.')
    return raw, payload['filename']


def normalize(text):
    text = unicodedata.normalize('NFKD', str(text).lower()).replace('đ', 'd')
    return re.sub(r'[^a-z0-9]+', '_', ''.join(c for c in text if not unicodedata.combining(c))).strip('_')


def read_table(raw, filename):
    if len(raw) > MAX_BYTES: raise PrivacyError('Maximum file size is 10 MB.')
    extension = Path(filename).suffix.lower()
    try:
        if extension == '.csv':
            profile = csv_profile(raw)
            records = list(csv.reader(io.StringIO(profile['text'], newline=''), delimiter=profile['delimiter'],
                                      quotechar=profile['quotechar']))
            if not records or any(len(row) != len(records[0]) for row in records[1:]):
                raise PrivacyError('CSV cần tiêu đề và số trường nhất quán ở mọi dòng.')
            frame = pd.DataFrame(records[1:], columns=records[0], dtype=str)
        elif extension == '.xlsx':
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if len(archive.infolist()) > 1000 or sum(x.file_size for x in archive.infolist()) > 50 * 1024 * 1024:
                    raise PrivacyError('XLSX vượt giới hạn dung lượng giải nén 50 MB.')
            frame = pd.read_excel(io.BytesIO(raw), sheet_name=0, dtype=str, keep_default_na=False, na_filter=False, engine='openpyxl')
        else:
            raise PrivacyError('Bản mã giả dạng bảng chỉ hỗ trợ CSV/XLSX; XLSX dùng sheet đầu tiên. Toàn bộ file gốc vẫn được mã hóa.')
    except PrivacyError: raise
    except Exception: raise PrivacyError('Không đọc được bảng. Dùng CSV UTF-8 hoặc XLSX có tiêu đề cột.')
    if frame.empty or len(frame.columns) > 200 or len(frame) > 100000 or frame.size > 200000:
        raise PrivacyError('Bảng phải có dữ liệu, tối đa 200 cột, 100.000 dòng và 200.000 ô để xuất đối chiếu chi tiết.')
    frame.columns = [str(x) for x in frame.columns]
    if frame.columns.duplicated().any(): raise PrivacyError('Tiêu đề cột bị trùng.')
    return frame


def suggest_columns(frame):
    keep_fields = {'amount_vnd','authority_limit_vnd','approval_time','disbursement_time','valid_from','valid_to',
                   'currency','approval_status','disbursement_status','role'}
    ids = {'row_id','loan_id','maker_id','approver_id','employee_id','branch_id','customer_id','account_id'}
    sensitive = ('name','ten','email','phone','dien_thoai','address','dia_chi','cccd','cmnd','passport',
                 'tai_khoan','account','customer','khach_hang','dob','ngay_sinh','date_of_birth','birth_date','tax','ma_so_thue')
    output = []
    for column in frame.columns:
        name = normalize(column)
        if name in keep_fields:
            action, reason = 'KEEP', 'Trường nghiệp vụ cần cho test; auditor phải xác nhận giữ lại.'
        elif name in ids or name.endswith('_id') or any(term in name for term in sensitive):
            action, reason = 'TOKENIZE', 'Có dấu hiệu nhận dạng/liên kết cá nhân; thay bằng mã giả.'
        else:
            action, reason = 'MASK', 'Chưa nhận diện được mục đích: che giá trị, giữ nguyên cột, cần con người review.'
        output.append({'column': column, 'action': action, 'reason': reason})
    return output


def token_value(master, scope, value):
    # Same exact ID across maker/approver/employee columns and paired files has the same token.
    scope_key = hmac.new(master, b'NEXUS-TOKEN-SCOPE:' + scope.encode(), hashlib.sha256).digest()
    digest = hmac.new(scope_key, str(value).strip().encode(), hashlib.sha256).hexdigest()[:32]
    return 'NX_' + digest


def csv_profile(raw):
    if raw.startswith(b'\xff\xfe'):
        text, encoding, bom = raw[2:].decode('utf-16-le'), 'utf-16-le', b'\xff\xfe'
    elif raw.startswith(b'\xfe\xff'):
        text, encoding, bom = raw[2:].decode('utf-16-be'), 'utf-16-be', b'\xfe\xff'
    else:
        encoding = 'utf-8'
        bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
        text = raw[len(bom):].decode('utf-8')
    try:
        dialect = csv.Sniffer().sniff(text[:32768], delimiters=',;\t|')
        delimiter, quotechar = dialect.delimiter, dialect.quotechar
    except csv.Error:
        delimiter, quotechar = ',', '"'
    newline = '\r\n' if '\r\n' in text else '\r' if '\r' in text and '\n' not in text else '\n'
    return {'text': text, 'encoding': encoding, 'bom': bom, 'delimiter': delimiter,
            'quotechar': quotechar, 'newline': newline, 'trailing_newline': text.endswith(('\r', '\n'))}


def spreadsheet_safe(value):
    text = str(value)
    # Valid signed numbers are ordinary values; executable-looking text is escaped.
    if text.lstrip().startswith(('=', '+', '-', '@')) and not re.fullmatch(r'[-+]?\d+(?:\.\d+)?', text.strip()):
        return "'" + text
    return text


def export_like_source(output, source_bytes, source_name, actions):
    extension = Path(source_name or 'protected.csv').suffix.lower()
    if extension == '.xlsx':
        from openpyxl import load_workbook
        with zipfile.ZipFile(io.BytesIO(source_bytes)) as archive:
            if any(x.startswith(('xl/media/', 'xl/charts/')) for x in archive.namelist()):
                raise PrivacyError('Workbook có ảnh/chart cần được rà soát riêng trước khi xuất mã giả.')
        workbook = load_workbook(io.BytesIO(source_bytes), data_only=False, keep_links=False)
        if len(workbook.worksheets) != 1:
            raise PrivacyError('XLSX nhiều sheet chưa được review đầy đủ. Bản này chỉ xuất mã giả workbook một sheet; file gốc vẫn mã hóa nguyên vẹn.')
        sheet = workbook.worksheets[0]
        if sheet.max_row != len(output) + 1 or sheet.max_column != len(output.columns):
            raise PrivacyError('XLSX cần bảng chữ nhật, header ở dòng 1, không có dòng/cột ngoài bảng.')
        if any(cell.data_type == 'f' for row in sheet for cell in row):
            raise PrivacyError('XLSX có công thức cần auditor chuẩn bị bản data-only trước khi thay mã, để tránh công thức lưu giá trị gốc hoặc thay đổi kết quả.')
        # openpyxl is the app runtime serializer, preserving the existing workbook's styles/layout.
        for row in sheet:
            for cell in row:
                cell.comment = None
                cell.hyperlink = None
        for column, name in enumerate(output.columns, 1):
            if actions[name] == 'KEEP': continue
            for index, value in enumerate(output[name], 2):
                sheet.cell(index, column).value = str(value)
                sheet.cell(index, column).data_type = 's'
        buffer = io.BytesIO(); workbook.save(buffer)
        return buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    profile = csv_profile(source_bytes) if source_bytes else {
        'encoding':'utf-8','bom':b'\xef\xbb\xbf','delimiter':',','quotechar':'"','newline':'\n','trailing_newline':True}
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer, delimiter=profile['delimiter'], quotechar=profile['quotechar'],
                        lineterminator=profile['newline'], quoting=csv.QUOTE_MINIMAL)
    writer.writerow(output.columns)
    writer.writerows(output.map(spreadsheet_safe).itertuples(index=False, name=None))
    text = buffer.getvalue()
    if not profile['trailing_newline']: text = text.removesuffix(profile['newline'])
    return profile['bom'] + text.encode(profile['encoding']), 'text/csv'


def pseudonymize(frame, plan, scope, reviewer, file_id, source_bytes=None, source_name='protected.csv'):
    master = master_key()
    valid_id(file_id)
    if not scope.strip() or len(scope) > 200 or not reviewer.strip():
        raise PrivacyError('Cần mã phạm vi kiểm toán và người review.')
    if len(plan) != len(frame.columns) or {x.get('column') for x in plan} != set(frame.columns):
        raise PrivacyError('Phương án xử lý phải có đúng mỗi cột một lần.')
    actions = {x['column']: ('MASK' if x['action'] == 'REMOVE' else x['action']) for x in plan}
    if any(x not in ACTIONS for x in actions.values()): raise PrivacyError('Hành động không hợp lệ.')
    output = frame.copy()
    details = []
    for column, action in actions.items():
        if action == 'MASK':
            output[column] = output[column].map(lambda value: '[REDACTED]' if str(value) else '')
        elif action == 'TOKENIZE':
            def replace(value):
                if not str(value).strip(): return ''
                token = token_value(master, scope.strip(), value)
                return token
            output[column] = output[column].map(replace)
    created_at = datetime.now(timezone.utc).isoformat()
    for index in range(len(frame)):
        for column in frame.columns:
            action = actions[column]
            details.append({'data_row': index + 1, 'column': column, 'action': action,
                'original_row_id': str(frame.iloc[index]['row_id']) if 'row_id' in frame.columns else '',
                'protected_row_id': str(output.iloc[index]['row_id']) if 'row_id' in output.columns else '',
                'method': 'HMAC-SHA256 scope token' if action == 'TOKENIZE' else 'literal redaction' if action == 'MASK' else 'unchanged',
                'original_value': str(frame.iloc[index][column]),
                'protected_value': str(output.iloc[index][column])})
    review_id = uuid.uuid4().hex
    export_bytes, mime = export_like_source(output, source_bytes, source_name, actions)
    metadata = {'file_id': file_id, 'review_id': review_id, 'scope': scope.strip(), 'reviewer': reviewer.strip(),
                'reviewed_at': created_at, 'source_filename': source_name, 'source_sha256': hashlib.sha256(source_bytes).hexdigest() if source_bytes else None,
                'protected_sha256': hashlib.sha256(export_bytes).hexdigest(), 'row_count': len(output),
                'column_count': len(output.columns), 'column_order': list(output.columns),
                'plan': [{**x, 'action': actions[x['column']]} for x in plan],
                'cell_details': details,
                'storage': 'auditor_download_only; no map file/DB/log write'}
    audit = pd.DataFrame(details).map(spreadsheet_safe)
    return {'csv_bytes': output.map(spreadsheet_safe).to_csv(index=False).encode('utf-8-sig'),
            'export_bytes': export_bytes, 'export_mime': mime,
            'export_filename': 'protected_' + Path(source_name.replace('\\','/')).name,
            'audit_mapping_csv_bytes': audit.to_csv(index=False).encode('utf-8-sig'),
            'audit_report_json_bytes': json.dumps(metadata, ensure_ascii=False, indent=2).encode(),
            'frame': output, 'mapping_reference': file_id + '.' + review_id, 'row_count': len(output)}


def restore_mapping(reference):
    """Private admin operation; mapping must never be exposed through public UI/API."""
    file_id, review_id = reference.split('.')
    valid_id(file_id); valid_id(review_id)
    keys, _, maps = vault_dirs()
    key = open_sealed(master_key(), json.loads((keys / (file_id + '.key.enc')).read_bytes()), ('key:' + file_id).encode())
    payload = json.loads((maps / (reference + '.map.enc')).read_bytes())
    return json.loads(open_sealed(key, payload, ('map:' + file_id + ':' + review_id).encode()))

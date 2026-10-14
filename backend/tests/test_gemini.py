"""Transport/validation tests with mocked HTTP; no live Gemini quality claims."""
import json
import io
import urllib.error
import pytest
from fastapi import HTTPException
from services import gemini


class Response:
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps(self.data).encode()


def candidate(text='{"controls": []}', reason='STOP'):
    return {'candidates': [{'finishReason': reason, 'content': {'parts': [{'text': text}]}}]}


def test_gemini_header_schema_and_payload(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-secret-never-live')
    monkeypatch.setenv('PROJECT07_GEMINI_MODEL', 'models/gemini-3.8-flash')
    def fake(req, timeout):
        assert req.full_url.endswith('/gemini-3.8-flash:generateContent')
        assert 'test-secret' not in req.full_url
        assert req.get_header('X-goog-api-key') == 'test-secret-never-live'
        body = json.loads(req.data)
        assert 'untrusted data' in body['systemInstruction']['parts'][0]['text']
        assert json.loads(body['contents'][0]['parts'][0]['text']) == {'policy_text': 'source'}
        assert body['generationConfig']['responseMimeType'] == 'application/json'
        assert body['generationConfig']['responseSchema']['required'] == ['controls']
        return Response(candidate())
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', fake)
    assert gemini.generate('LLM1_RCM', 'instruction', {'policy_text': 'source'}) == ({'controls': []}, 'gemini-3.8-flash')


def test_missing_key_fails_before_network(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('unexpected network'))
    with pytest.raises(gemini.GeminiError, match='GEMINI_API_KEY'):
        gemini.generate('LLM1_RCM', '', {})


@pytest.mark.parametrize('status,code', [(400,'MODEL_REQUEST_ERROR'), (401,'MODEL_AUTH_ERROR'),
    (403,'MODEL_AUTH_ERROR'), (404,'MODEL_NOT_FOUND'), (429,'MODEL_RATE_LIMIT'), (500,'MODEL_UNAVAILABLE')])
def test_http_errors_are_safe(monkeypatch, status, code):
    monkeypatch.setenv('GEMINI_API_KEY', 'do-not-leak-me')
    def fake(req, timeout):
        raise urllib.error.HTTPError(req.full_url, status, 'do-not-leak-me', {}, None)
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', fake)
    with pytest.raises(gemini.GeminiError) as exc:
        gemini.generate('LLM1_RCM', '', {})
    assert exc.value.code == code
    assert 'do-not-leak-me' not in str(exc.value)


@pytest.mark.parametrize('response,code', [
    ({'promptFeedback': {'blockReason': 'SAFETY'}}, 'MODEL_BLOCKED'),
    ({'candidates': []}, 'MODEL_SCHEMA_ERROR'),
    (candidate(reason='MAX_TOKENS'), 'MODEL_TRUNCATED'),
    (candidate(reason='SAFETY'), 'MODEL_BLOCKED'),
    (candidate('not JSON'), 'MODEL_SCHEMA_ERROR'),
    (candidate('[]'), 'MODEL_SCHEMA_ERROR'),
])
def test_invalid_or_blocked_output_fails_closed(monkeypatch, response, code):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake')
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', lambda *a, **k: Response(response))
    with pytest.raises(gemini.GeminiError) as exc:
        gemini.generate('LLM1_RCM', '', {})
    assert exc.value.code == code


@pytest.mark.parametrize('task', ['LLM1_RCM','LLM2_PLAN','LLM3_FINDINGS','LLM4_REPORT'])
def test_task_schema_valid(task):
    schema = gemini.schema_for(task)
    assert schema['type'] == 'OBJECT'
    assert all(x in schema['properties'] for x in schema['required'])


def test_workflow_missing_key_records_failed_call(client, monkeypatch):
    from services import workflow
    from models.db import connect
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with pytest.raises(HTTPException) as exc:
        workflow.llm_generate('test-run', 'LLM1_RCM', '', {})
    assert exc.value.status_code == 503
    with connect() as c:
        row = c.execute('SELECT task, status FROM llm_calls ORDER BY created_at DESC').fetchone()
        assert row['task'] == 'LLM1_RCM' and row['status'] == 'ERROR'


@pytest.mark.parametrize('reason', ['API_KEY_INVALID','API_KEY_SERVICE_BLOCKED',
    'API_KEY_HTTP_REFERRER_BLOCKED','API_KEY_IP_ADDRESS_BLOCKED','SERVICE_DISABLED','BILLING_DISABLED'])
def test_google_reason_safe_translation(reason):
    body = {'error': {'message': 'secret-should-not-be-shown', 'details': [{'reason': reason, 'metadata': {'key': 'secret-should-not-be-shown'}}]}}
    exc = urllib.error.HTTPError('https://example.test', 403, 'Forbidden', {}, io.BytesIO(json.dumps(body).encode()))
    result = gemini.http_error(exc)
    assert result.code == 'MODEL_AUTH_ERROR'
    assert 'secret-should-not-be-shown' not in str(result)
    assert 'chưa có reason' not in str(result)


def test_leaked_key_safe_translation():
    body = {'error': {'message': 'key secret-value was reported as leaked'}}
    result = gemini.http_error(urllib.error.HTTPError('https://example.test', 403, 'Forbidden', {}, io.BytesIO(json.dumps(body).encode())))
    assert 'bị lộ' in str(result)
    assert 'secret-value' not in str(result)


def test_model_metadata_check(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    monkeypatch.setenv('PROJECT07_GEMINI_MODEL', 'gemini-test')
    def fake(req, timeout):
        assert req.get_method() == 'GET' and req.data is None
        assert req.get_header('X-goog-api-key') == 'test-only'
        return Response({'models': [{'name': 'models/gemini-test', 'supportedGenerationMethods': ['generateContent']},
                                   {'name': 'models/embed-test', 'supportedGenerationMethods': ['embedContent']}]})
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', fake)
    result = gemini.check_access()
    assert result['metadata_access'] == 'OK'
    assert result['configured_model_listed'] is True
    assert result['generate_content_models'] == ['gemini-test']


def test_diagnostic_endpoint_missing_key(client, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    response = client.post('/api/llm/check')
    assert response.status_code == 503
    assert response.json()['errors'][0]['code'] == 'MODEL_CONFIGURATION_ERROR'


def test_unmapped_403_preserves_diagnostic_and_redacts_key(monkeypatch):
    secret = 'AIza' + 'x' * 35
    monkeypatch.setenv('GEMINI_API_KEY', secret)
    body = {'error': {'message': f'Model permission denied for key {secret}. Contact project administrator.'}}
    result = gemini.http_error(urllib.error.HTTPError('https://example.test', 403, 'Forbidden', {}, io.BytesIO(json.dumps(body).encode())))
    assert 'Model permission denied' in str(result)
    assert 'Contact project administrator' in str(result)
    assert secret not in str(result)
    assert '[REDACTED]' in str(result)


def test_sanitizes_query_tokens_and_whitespace(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'secret with spaces')
    text = gemini.sanitized_message('Denied\nsecret%20with%20spaces https://example.test?key=another-key Bearer token-123')
    assert 'secret%20with%20spaces' not in text and 'another-key' not in text and 'token-123' not in text
    assert '\n' not in text


def test_503_retries_are_bounded_and_can_recover(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-only')
    monkeypatch.setenv('PROJECT07_GEMINI_MAX_RETRIES', '2')
    calls = []; delays = []
    def fake(req, timeout):
        calls.append(req)
        if len(calls) < 3: raise urllib.error.HTTPError(req.full_url, 503, 'busy', {}, io.BytesIO(b'{}'))
        return Response(candidate())
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', fake)
    monkeypatch.setattr(gemini.time, 'sleep', delays.append)
    assert gemini.generate('LLM1_RCM', '', {})[0] == {'controls':[]}
    assert len(calls) == 3 and len(delays) == 2
    assert 1 <= delays[0] <= 1.3 and 2 <= delays[1] <= 2.3


def test_403_never_retries(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-only')
    calls = []
    def fake(req, timeout):
        calls.append(req)
        raise urllib.error.HTTPError(req.full_url, 403, 'denied', {}, io.BytesIO(b'{}'))
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', fake)
    monkeypatch.setattr(gemini.time, 'sleep', lambda _: pytest.fail('permission error must not retry'))
    with pytest.raises(gemini.GeminiError): gemini.generate('LLM1_RCM', '', {})
    assert len(calls) == 1


def test_503_stops_after_maximum_retries(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-only')
    monkeypatch.setenv('PROJECT07_GEMINI_MAX_RETRIES', '2')
    calls = []
    def fake(req, timeout):
        calls.append(req)
        raise urllib.error.HTTPError(req.full_url, 503, 'busy', {}, io.BytesIO(b'{}'))
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', fake)
    monkeypatch.setattr(gemini.time, 'sleep', lambda _: None)
    with pytest.raises(gemini.GeminiError): gemini.generate('LLM1_RCM', '', {})
    assert len(calls) == 3

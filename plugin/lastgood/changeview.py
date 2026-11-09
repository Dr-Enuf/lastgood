"""Bounded invariant-presence evidence; never capture source context."""
import json
import re
import threading
import uuid
from pathlib import PurePosixPath

SCHEMA = 1
MAX_LABEL_BYTES = 160
MAX_RECORDS = 200
MAX_INDEX_BYTES = 1024 * 1024
_REDACT = re.compile(
    r'-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*|'
    r'\b(?:sk-|ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{8,}|'
    r'(?i:\b(?:password|passwd|secret|token|api[_-]?key|authorization)\b[\"\']?\s*[:=]\s*[^\r\n]+)'
)


def bounded(text, limit=MAX_LABEL_BYTES):
    raw = str(text).encode('utf-8')
    if len(raw) <= limit:
        return str(text)
    return raw[:max(0, limit - len('…[truncated]'.encode()))].decode('utf-8', 'ignore') + '…[truncated]'


def redact(text):
    return _REDACT.sub('[redacted]', str(text))


def sanitize(value):
    if isinstance(value, str):
        return bounded(redact(value), 1024)
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value


def sensitive_path(raw):
    parts = PurePosixPath(str(raw).replace('\\', '/').lower()).parts
    return any(p.startswith('.env') or p in ('.ssh', 'credentials', 'credentials.json',
               'secrets.json', 'secrets.yaml', 'id_rsa', 'id_ed25519') or
               p.endswith(('.pem', '.key', '.p12', '.pfx')) for p in parts)


def observation(c, data, found):
    if sensitive_path(c['path']) or b'-----BEGIN ' in data or redact(c['text']) != c['text']:
        return None
    # Do not preserve even presence metadata from incomplete/binary/invalid reads.
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return None
    if any(ord(ch) < 32 and ch not in '\n\r\t' for ch in text):
        return None
    return {'schema': SCHEMA, 'path': bounded(redact(c['path'])),
            'text': bounded(redact(c['text'])), 'present': bool(found)}


def compare(previous, current):
    out = {'schema': SCHEMA, 'before_id': previous.get('id') if previous else None,
           'after_id': current['id'], 'changes': [], 'note': '',
           'caution': 'Adjacent checked observations only; edits between them are unobserved. Not proof of cause.'}
    if not previous:
        out['note'] = 'First retained observation; no earlier evidence.'
    elif any(r.get('result') not in ('PASS', 'FAIL') for r in (previous, current)):
        out['note'] = 'UNKNOWN/skipped observation gap; not compared.'
    elif current.get('baseline_requested'):
        out['note'] = 'Explicit baseline; no change comparison.'
    elif current.get('continuity_blocked'):
        out['note'] = 'Storage continuity lost; deltas disabled until an explicit baseline is saved.'
    elif previous.get('config_hash') != current.get('config_hash'):
        out['note'] = 'Check setup changed; no comparable evidence.'
    elif previous.get('session_id') != current.get('session_id'):
        out['note'] = 'Session boundary; no comparable evidence.'
    elif previous.get('continuity_epoch') != current.get('continuity_epoch'):
        out['note'] = 'Process/storage epoch changed; no comparison across uncertain continuity.'
    elif (previous.get('observation_finished') is None or current.get('observation_started') is None or
          previous['observation_finished'] > current['observation_started']):
        out['note'] = 'Legacy or overlapping observation intervals; order unverified.'
    else:
        old = previous.get('presence_observations', [])
        new = current.get('presence_observations', [])
        for a, b in zip(old[:5], new[:5]):
            if (a and b and a.get('schema') == b.get('schema') == SCHEMA and
                    a.get('path') == b.get('path') and a.get('text') == b.get('text') and
                    a['present'] != b['present']):
                out['changes'].append({'path': b['path'], 'text': b['text'],
                                       'change': 'added' if b['present'] else 'removed'})
        out['note'] = ('Configured-string presence changed.' if out['changes'] else
                       'No eligible configured-string presence change observed (unavailable checks are omitted).')
    return out


def describe(evidence):
    if not evidence:
        return 'No comparable change evidence was recorded.'
    text = f"Observed changes #{evidence.get('before_id')} → #{evidence.get('after_id')}: {evidence['note']}"
    for c in evidence.get('changes', [])[:5]:
        text += f"\n  {c['change']} configured text in {c['path']}: {c['text']}"
    return text + '\n' + evidence['caution']


def retain(items):
    del items[:-MAX_RECORDS]
    while len(items) > 1 and len(serialize_json(items).encode('utf-8')) > MAX_INDEX_BYTES:
        del items[0]

    if len(serialize_json(items).encode('utf-8')) > MAX_INDEX_BYTES:
        raise ValueError('Single retained record exceeds storage limit')


def serialize_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


# Epochs deliberately never imply continuity across process restarts.
_STATE_LOCK = threading.Lock()
_STATES = {}
_MAX_STATES = 256


def continuity(key):
    with _STATE_LOCK:
        if key not in _STATES:
            if len(_STATES) >= _MAX_STATES:
                return {'epoch': uuid.uuid4().hex, 'blocked': True}
            _STATES[key] = {'epoch': uuid.uuid4().hex, 'blocked': False}
        return dict(_STATES[key])


def lost_continuity(key):
    with _STATE_LOCK:
        if key in _STATES or len(_STATES) < _MAX_STATES:
            _STATES[key] = {'epoch': uuid.uuid4().hex, 'blocked': True}


def accept_baseline(key, epoch):
    with _STATE_LOCK:
        state = _STATES.get(key)
        if state and state['epoch'] == epoch:
            state['blocked'] = False

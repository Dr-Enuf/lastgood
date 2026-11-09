"""Process-local callback/check observations, never a durable liveness claim."""
import copy
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone

RUNTIME_ID = uuid.uuid4().hex
_LOCK = threading.Lock()
_SCOPES = {}
_MAX_SCOPES = 256
_UPDATES_DROPPED = False
_REGISTRATION = {'state': 'UNOBSERVED', 'time': None}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def key(project, ids=None):
    ids = ids or {}
    return (os.path.realpath(project), str(ids.get('session_id') or ids.get('conversation_id') or 'UNSPECIFIED')[:120])


def fresh():
    return {'pre': 0, 'post': 0, 'last_hook': None, 'last_tool': None,
            'post_status': {s: 0 for s in ('succeeded', 'failed', 'blocked', 'uncertain')},
            'callback_error': None, 'check': {'last_attempt': None, 'last_completed': None, 'last_error': None},
            'self_test': {'last_attempt': None, 'last_completed': None, 'last_error': None}}


def mutate(project, ids, action):
    global _UPDATES_DROPPED
    if not _LOCK.acquire(timeout=0.1):
        _UPDATES_DROPPED = True
        return False
    try:
        k = key(project, ids)
        if k not in _SCOPES:
            if len(_SCOPES) >= _MAX_SCOPES:
                _UPDATES_DROPPED = True
                return False
            _SCOPES[k] = fresh()
        action(_SCOPES[k])
        return True
    finally:
        _LOCK.release()


def registered():
    if _LOCK.acquire(timeout=0.1):
        try:
            _REGISTRATION.update(state='REGISTERED_IN_THIS_RUNTIME', time=now())
        finally:
            _LOCK.release()


def observe(project, ids, phase, tool_name, status=None):
    name = re.sub(r'[^a-zA-Z0-9_.-]', '_', str(tool_name or '?'))[:80]
    def update(s):
        s[phase] = min(2**31 - 1, s[phase] + 1)
        s['last_hook'], s['last_tool'] = now(), name
        if phase == 'post':
            s['post_status'][status if status in s['post_status'] else 'uncertain'] += 1
    return mutate(project, ids, update)


def callback_error(project, ids, kind):
    safe_type = re.sub(r'[^a-zA-Z0-9_.-]', '_', str(kind))[:80]
    mutate(project, ids, lambda s: s.update(callback_error={'time': now(), 'type': safe_type}))


def attempt(project, ids, diagnostic=False):
    lane = 'self_test' if diagnostic else 'check'
    mutate(project, ids, lambda s: s[lane].update(last_attempt={'time': now(), 'source': 'SELF-TEST' if diagnostic else 'CHECK'}))


def finish(project, ids, result, completed, error=None, diagnostic=False):
    lane = 'self_test' if diagnostic else 'check'
    def update(s):
        if completed:
            s[lane]['last_completed'] = {'time': now(), 'result': result}
        s[lane]['last_error'] = {'time': now(), 'type': error} if error else None
    mutate(project, ids, update)


def read(project, ids=None):
    if not _LOCK.acquire(timeout=0.1):
        return {'runtime_id': RUNTIME_ID, 'hook_activity': 'UNKNOWN', 'error': 'Health memory lock busy'}
    try:
        k = key(project, ids)
        s = copy.deepcopy(_SCOPES.get(k, fresh()))
        s.update(runtime_id=RUNTIME_ID, session_scope=k[1], registration=copy.deepcopy(_REGISTRATION),
                 hook_activity='CALLBACKS_OBSERVED' if s['pre'] or s['post'] else 'UNOBSERVED',
                 provenance='Callback invocation only; no guarantee of host origin or complete coverage.')
        if k not in _SCOPES and len(_SCOPES) >= _MAX_SCOPES:
            s.update(hook_activity='UNKNOWN', error='Health scope capacity reached')
        if _UPDATES_DROPPED:
            s.update(hook_activity='UNKNOWN', collection_error='Runtime memory updates were dropped; counts may be incomplete')
        return s
    finally:
        _LOCK.release()


def line(state):
    check = state.get('check', {})
    completed = check.get('last_completed') or {}
    attempted = check.get('last_attempt') or {}
    return (f"Runtime callbacks: {state.get('hook_activity', 'UNKNOWN')} "
            f"(pre={state.get('pre', '?')}, post={state.get('post', '?')}); "
            f"config={state.get('config', 'UNTESTED')}; "
            f"completed={completed.get('result', 'UNOBSERVED')} at {completed.get('time', 'never')}; "
            f"attempt={attempted.get('time', 'never')}; "
            f"check_error={(check.get('last_error') or {}).get('type', 'none')}; "
            f"callback_error={(state.get('callback_error') or {}).get('type', 'none')} "
            f"at {(state.get('callback_error') or {}).get('time', 'never')}; "
            f"last_hook={state.get('last_hook') or 'never'} tool={state.get('last_tool') or 'unobserved'}; "
            f"collection={state.get('collection_error') or state.get('error') or 'no dropped updates observed'}; "
            "registration is not delivery proof")

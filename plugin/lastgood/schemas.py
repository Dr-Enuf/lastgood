"""Tool schemas: what the model sees."""

_PATH = {"type": "string", "description": "Project folder (default: the session's working folder)"}

LASTGOOD_CHECK = {
    "name": "lastgood_check",
    "description": (
        "Run the project's LastGood checks on the files as they are now and record a "
        "tested step: PASS if every check passed, FAIL if one failed, UNKNOWN if a check "
        "could not decide (page unreachable, time budget, bad setup). Checks come from "
        "lastgood-config.json in the project folder. LastGood also checks automatically "
        "after write_file/patch when that file exists. A tested step is NOT a Hermes "
        "checkpoint; restoring is done with Hermes' /rollback. File checks use "
        "lastgood_setup. Its format is "
        '{"checks": [{"type": "file_opens", "path": "app.py"}]} with type one of '
        "file_opens, text_present, files_exist (no other fields). Do not add url_loads "
        "with this tool; only the user can, via /lastgood setup or by editing the file. "
        "A page check fetches the http(s) address they configure (link-local/metadata refused). "
        "LastGood refuses a home folder, the Hermes home folder, or a drive root as the project."
    ),
    "parameters": {"type": "object", "properties": {
        "label": {"type": "string", "description": "Short name for this step, e.g. 'added login form'"},
        "path": _PATH}, "required": []},
}

LASTGOOD_STATUS = {
    "name": "lastgood_status",
    "description": (
        "Show LastGood's tested steps for the project with PASS/FAIL/UNKNOWN and whether each "
        "is current (files and setup unchanged since it was tested) or stale."
    ),
    "parameters": {"type": "object", "properties": {"path": _PATH}, "required": []},
}

LASTGOOD_BLAME = {
    "name": "lastgood_blame",
    "description": (
        "Find the tested step where checks first failed after a passing one, from recorded "
        "results. This is where failure was first observed, not proof of what caused it."
    ),
    "parameters": {"type": "object", "properties": {"path": _PATH}, "required": []},
}

LASTGOOD_REPORT = {
    "name": "lastgood_report",
    "description": (
        "Write the LastGood Proof Report (one HTML file): tested-step timeline with "
        "freshness, the first-failure verdict, and recognised tool calls a file rollback "
        "won't undo. Returns the file path."
    ),
    "parameters": {"type": "object", "properties": {"path": _PATH}, "required": []},
}

LASTGOOD_SETUP = {
    "name": "lastgood_setup",
    "description": (
        "Save the project's LastGood file checks to lastgood-config.json (up to 5). Only call "
        "this when the user has said what 'still works' means. Types: file_opens {path}; "
        "text_present {path, text}; files_exist {paths}. Do not add url_loads: this tool "
        "refuses it. The user adds a page check with /lastgood setup or by editing "
        "lastgood-config.json. Paths must be inside the project folder. There is no "
        "command-running check. No other fields are accepted (no name/description/verify/target)."
    ),
    "parameters": {"type": "object", "properties": {
        "checks": {"type": "array", "maxItems": 5, "description": "The checks to save",
                   "items": {"type": "object", "required": ["type"], "additionalProperties": False,
                             "properties": {
                                 "type": {"type": "string", "enum": ["file_opens", "text_present",
                                                                     "files_exist"]},
                                 "path": {"type": "string", "description": "file_opens/text_present: file inside the project"},
                                 "text": {"type": "string", "description": "text_present: words that must be present"},
                                 "case_insensitive": {"type": "boolean"},
                                 "paths": {"type": "array", "items": {"type": "string"}, "description": "files_exist: files that must exist"},
                                 "url": {"type": "string", "description": "url_loads: http(s) address"},
                                 "timeout": {"type": "number"}}}},
        "path": _PATH}, "required": ["checks"]},
}

# v0.4.0 read-only restart/timeout diagnosis — Nov 7 2026, ~2:43 PM EST

## Ownership confirmed; terminal restart is not plugin-runtime restart
Installed `hermes_cli/gateway_plugin_commands.py:217-228` sends plugin slash
commands via `connection.call_until("slash.exec", session_id=cli.session_id,...)`.
`gateway/session_commands.py:182-227` resolves/executes the plugin handler in the
owning profile; `gateway/run_inbound_hooks.py:281-299` supplies session_id under
session env scope. `hermes_cli/plugins.py:1629-1645` caches manager per home inside
that owning process. This is not a fresh local plugin instance per terminal.
The isolated test home's gateway_state.json explicitly identifies PID5810;
read-only ps confirms PID5810 is a still-running gateway process, started while
the first health client was active. It was not restarted or touched.

First CLI/driver PIDs5761/5760 exited. New CLI/driver PIDs6444/6443 resumed SAME
session local-7622363d592e101cf5a51971b6d27574532e7b6ab56a9816552a1615bafc66f8.
Its real /lastgood status returned pre1/post1 and original patch/check timestamp
2:36:46 PM EST. That matches persistent owner semantics, not restoration from a
health file (none exists). Initial actual doctor runtime UUID was
11c2f221dc4f47a580353e5e648c34d3. No second UUID was obtained: do not claim a direct
UUID equality comparison. Existing evidence plus installed routing confirms the
terminal restart did not establish that the plugin-owning process restarted.
No concrete LastGood memory-reset defect was demonstrated. Actual plugin-owner
restart/reset remains host-UNTESTED; independent standalone process-reset tests
passed. User-visible health can correctly survive terminal reconnect to the same
live owner/session. Counts are scoped to plugin runtime, not terminal lifetime.

## No observed plugin doctor timeout
Restart driver sent.jsonl contains ONLY /lastgood status, sent2:37:26 PM EST.
It did return valid status. The helper expected `Runtime callbacks: UNOBSERVED`,
so a valid CALLBACKS_OBSERVED response failed its matcher and generated a 15s
harness timeout at2:37:41 PM EST. This was a wrong test expectation, not a slow
status handler.
Follow-up /lastgood doctor and /quit exist only in queue.jsonl (mtime2:38:23 PM
EST), NOT sent.jsonl. The doctor timeout capture is zero bytes; no doctor was
proved delivered. Thus do not attribute its missing response to plugin budget,
cleanup or a Hermes handler timeout. The driver was no longer forwarding input.
Its configured cap245s had NOT elapsed: started2:37:23 PM EST, queue updated
~60s later. No normal driver-ended marker was produced. Its termination cause
was not recorded (parent-script exception/tool subprocess lifetime is possible,
not proven). The exact dedicated client/driver PIDs were absent at prior end.

## Preserved scope
All inspection read-only; no new CLI/model, backend restart/kill, config changes,
code changes or source-hash changes. Earlier raw logs and timeout files preserved.
Real initial UNOBSERVED + doctor no-hooks/no-history + actual model callback
counts + doctor preserving genuine FAIL/report remain proven independently of
this invalid terminal-restart expectation. Packaging should explain this
runtime ownership nuance, not promise reset on every CLI reconnect.

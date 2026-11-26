# Native notification history, redaction and transience (Plans 181 and 184)

## Status: native history gate passes after a narrow height-feedback guard

`tools/check_native_history.py` exercises the sealed original Omarchy closure at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` with its reviewed Ubuntu service
derivation, the exclusive Quickshell runtime and the existing private Labwc/
Pixman/SHM + Qt OpenGL/llvmpipe lab. Plan 181 originally failed on layout binding
loops despite seven passing functional cases. Plan 184 reduces that failure to
code-card dismissal and adds one early height-report guard in the derivation:
`if (!liveKeys[key] || leaving[key]) return`.

The complete, unmodified history runner now passes all seven cases across three
native process generations with only the expected absent-Hyprland warning. The
original cards, layout algorithm, native surfaces, shaders, input handlers and
close ordering remain unchanged. Rendering, pointer and cross-process runners
also pass again against the new sealed derivation. No diagnostic is suppressed.
This closes that native-history gate, not live admission or deployment.

The finding does not establish a cause for the independent live crashes; no
real-crash backtrace connects them to this event-order feedback path.

## Functional assertions observed

The fixture retains real NotificationServer ingestion and native surfaces. Fixed
synthetic Notify calls, original IPC and private fixture restarts establish:

1. An ordinary message enters live storage and moves to history when dismissed.
   A transient message appears natively but enters neither live storage nor
   closed history.
2. A real replaces_id update from persistent to transient removes the saved row;
   its dismissal does not add history. The reverse update becomes persistable
   and its later dismissal is retained, with the original native ID preserved.
3. A synthetic verification message is detected as code-bearing. Active live and
   history files contain only the original redacted placeholder, with sender/
   source/string metadata cleared. The synthetic code/metadata canaries are
   absent from active file bytes. No copy/code/URL/app action is invoked.
4. A restart of **only the owned test shell** restores the redacted persistent
   card, not its transient companion. Restored row observations have no code,
   image or native sender actions/references. The placeholder remains redacted.
5. Original showHistory replays six recent native cards, including a redacted
   placeholder. They are restored rows without live sender actions. Dismissing
   replayed cards does not duplicate history.
6. After the owned service stops and private state is checkpointed, schema-valid
   synthetic legacy code records are seeded. Native startup sanitises/re-writes
   them and prunes a record older than 24 hours. No host wall clock is changed.
7. Native history reaches its 100-row cap; further ordinary closes preserve the
   newest-first order and drop the oldest retained rows. Final bounded-phase
   active state has empty live storage, 100 history rows and quiet still off.

Only owned regular, bounded 0600 files and exact schemas are read. Validation
never prepares, repairs or resets missing/invalid files. Derived fields such as
stored images/codes are not permitted by that schema. Do not infer that every
stored action/identifier is erased: the assertions follow the actual original
Store contract and explicitly inspect restored native sender references/actions.

## Historical binding-loop evidence and diagnostic controls

Before the Plan 184 guard, repeated complete runs recorded warning counts by
functional phase and private process generation:

- The ordinary/transient/replacement phases have only the expected absent-
  Hyprland warning.
- At the code live/history phase, the first process gains two layout binding-loop
  warnings. A second process restores a redacted card cleanly but gains two more
  layout warnings by the mixed recent-history replay phase.
- The third process's seeded legacy redaction/retention cases have no extra warning.

The warning points to the retained service's readonly layout binding. That is an
observation, not an established cause. Private smaller controls with ordinary/
code messages alone are clean, both without and with eager row-metric reads;
a matching synthetic sender-marker/code control is also clean. Therefore neither
"any code message is broken" nor "the metrics accessor alone causes it" is
established. The full sequence reproduces it; its exact trigger remains open.

The smaller control scripts/receipts are explicitly marked as diagnostic variants,
**not full-history acceptance**. Their staged driver hashes differ from the full
fixture. Both the failing full runs and clean controls are retained.

### Plan 184 reduction and correction

Adding dismissal to the previously clean ordinary/code control reproduces two
layout warnings: arrival remains clean, closing the code card does not. A private
proposal moving `unmarkLeaving` after model removal reduces the full sequence's
four warnings to two, but still fails and is not adopted.

A departing card occupies no layout room. Changing its placement hides the code
deed area, changing `targetHeight`; the synchronous height callback previously
fed that transient measurement into `land`/`retarget` and invalidated the layout
while that binding was being evaluated. A row already released from `liveKeys`
likewise must not update layout from a late delegate callback. The early guard
rejects those reports before changing cached heights or the layout revision.
Valid live/arrival measurements and original close ordering remain intact.

The unsealed private guard proposal passes the entire sequence. That proposal
receipt is explicitly not production acceptance. Only after review, adding the
exact guard to `notification_frontend.service`, recording the adaptation and
refreshing the staged service digest was the unchanged canonical runner rerun
successfully. Its sealed source hashes match the current profile. All imported
upstream bytes remain unchanged. Source regressions cover the early guard,
unchanged close/layout blocks and refusal when its upstream witness changes.

Private failed controls/proposals, staged sources, scripts/hashes, captures and
state checkpoints remain under ignored work/. They are historical inputs, not
receipts that may be relabelled after source changes.

## Reproduction, containment and limits

```sh
python3 tools/check_native_history.py
python3 tools/check_native_history.py --run \
  --lab-dir work/<verified-private-lab> \
  --candidate work/notification-runtime-builds/<verified-variant>
```

The default is plan-only. Explicit execution checks the lab/runtime/source seals,
uses a fresh activation-disabled private bus/compositor and accepts no host
sockets, buses, homes, devices or inherited display/Hyprland identity. No packages,
downloads, build or installed-release selection occur. Original fixture-only
35-second watchdogs and the 80-second outer bound do not change normal component
lifetime policy. All owned children are reaped and source/runtime/lab inputs stay
unchanged, including in failed runs.

Before reseeding, private synthetic stores are checkpointed with hashes/modes.
The deliberately unredacted **synthetic** legacy seed and authored control scripts
naturally contain the fake canary; absence is asserted for the active sanitised
stores, not all work artifacts. Two synthetic redacted/replay captures, logs,
state checkpoints, source hashes and controls remain only under ignored work/.
No real notifications/history, clipboard or DND are collected or changed.

Fourteen synthetic state/refusal/diagnostic regressions continue to treat layout
warnings as failures rather than allowed diagnostics. Plan 184 adds three source
regressions for the guarded height feedback and unchanged source witnesses.
Backups include hashes/modes of affected source/profile/tests and documents;
fixture/dependency hashes, state checkpoints and active-store constraints remain
part of verification. Passing units alone cannot replace the canonical native
run or supply live deployment admission.

Clipboard/code-copy secrecy, locked-session privacy, adversarial security,
production apps, Hyprland policy, multi-output interactions, crash causality and
artifact-bound reversible live admission/migration remain excluded. SwayNC,
installed shell and live debug capture are neither inspected nor changed; current
debugger liveness is not inferred. No commit or publication occurs.

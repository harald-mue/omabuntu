# Logout service identity diagnosis

## Goal and evidence

Explain the owner-provided screenshot showing a truncated UWSM service identity
error after requesting Logout. Compare the exact installed power-action helper
with the current owned compositor instance, its cgroup and the same systemd user
unit's MainPID. Relevant upstream session context remains Omarchy commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no upstream code import or change is
proposed by this diagnostic request.

## Constraints and scope

Only bounded read-only session/unit metadata probes and private reports under
ignored work/. Never call the power-action perform/logout CLI, stop a unit, invoke
an exit dispatcher, modify services or trigger a session transition. Do not
collect corporate environment, full process arguments or notification contents.
A failed identity check does not prove that the live service actually changed;
distinguish wrapper MainPID, bad lookup, mismatched ownership and genuine drift.
No desktop edit, deployment, package operation, restart or commit is approved.

## Tasks

- [x] Inspect the screenshot and exact refusal branch.
- [x] Compare the owned live compositor, cgroup unit and bounded MainPID evidence.
- [x] Check installed-source correspondence and explain the proven mismatch/limits.

## Findings

The installed helper matches the workspace exactly. It requires systemd MainPID
to equal the Hyprland instance PID. The actual active service instead has
`start-hyprland` as MainPID, with Hyprland as its direct child; both are owned by
the current user and have the identical cgroup. The current evidence therefore
shows a wrapper/compositor mismatch, not proof of an identity transition. The
strict check falsely refuses this valid wrapper-managed topology before stop.

The visible error is also deliberately truncated: CommandMenu uses NoWrap and
ElideRight outside its window-controls confirmation route. This explains the
screenshot ellipsis without requiring a rendering/driver diagnosis.

A future repair should verify the exact unit's owned wrapper/compositor ancestry,
cgroup and process identities rather than remove the safety check or assume
every unit descendant is an authorized logout target. Error messages should be
readable without replacing the original menu. No fix or session action was run.

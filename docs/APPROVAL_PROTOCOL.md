# Privileged approval protocol

Every privileged operation must be approved as a specific, one-shot request.

## Approval prompt

The phone UI must display:

- operation name
- exact command that the local privileged executor will run
- target/path/package
- expected effect
- request ID
- expiration time

Example:

    ROOT ACTION
    Operation: Restart SystemUI
    Command: am force-stop com.android.systemui
    Target: com.android.systemui
    Request: 8f3c...
    Expires: 30 seconds

    [APPROVE] [REJECT]

## Rules

1. The displayed command is the exact command bound to the approval request.
2. Approval applies only to that request ID.
3. Approval expires after a short timeout.
4. A rejected or expired request cannot execute.
5. The command and approval decision are written to the local audit log.
6. The remote connector must request a typed operation; it must not submit an arbitrary command for execution.
7. The privileged executor remains local to the Android device.

The purpose is to make every privileged action visible before execution while preserving the existing local safety policy.

# Remote control boundary

The project deliberately separates the Android-local privileged bridge from the remote connector.

## Current boundary

The phone bridge can run local privileged operations through the Android root manager, but unrestricted shell execution is not part of the remote connector contract.

Remote-facing code should expose only typed, narrowly scoped operations and should never forward an arbitrary command string to the root shell.

## Remaining manual integration

If you are developing this for your own rooted test device, the final privileged integration must be performed locally on that device. Keep it behind the existing localhost binding, authentication, audit logging, and command policy.

Do not expose the Android bridge port directly to the Internet.

# Architecture

## Trust boundary

ChatGPT/tool connector
  -> authenticated transport
  -> Android bridge
  -> local safety policy
  -> su
  -> Android

The Android bridge is authoritative for destructive operations.

## Planned tool surface

device.info
shell.exec
system.logcat
packages.list
fs.read
fs.list
policy.test
screenshot.capture
app.launch
app.stop
app.install
process.list

Future high-risk operations should be separate capabilities rather than arbitrary shell aliases.
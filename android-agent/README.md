# NAANG Phone Agent

Android-side accessibility foundation for the NAANG phone bridge.

## Current capabilities

- Registers an Android AccessibilityService.
- Reads the active accessibility window hierarchy.
- Captures text, content descriptions, resource IDs, bounds, clickability and enabled/scrollable state.
- Performs semantic click actions.
- Supports global Android accessibility actions through the service.
- Provides a foundation for typed phone-bridge requests.

Android requires the user to explicitly enable an AccessibilityService in Settings. The framework exposes window content and global actions to accessibility services, including Home, Back, Recents and screenshot on supported Android versions.

The remote connector should request typed operations rather than arbitrary shell commands. Privileged operations remain local to the phone.

# RDKit / Windows Application Control architecture fix

## Why v2.10 failed after the Python reset
The pip-installed Python RDKit package contains native DLLs. On the affected Windows machine, the operating-system Application Control policy blocked `rdBase` while Python was importing it. Reinstalling the same wheel cannot reliably fix a policy denial.

## Current v2.11 design
- Native Python RDKit is removed from the default runtime requirements.
- The server does not import native RDKit during normal startup.
- EnviroDesign first uses the official RDKit.js WebAssembly distribution in the browser.
- If a deployment explicitly enables a permitted native Python RDKit backend, the existing server implementation remains available as a fallback.
- Core FOCUS PEARL, veterinary, biosolids, irrigation, sorption and evidence workflows never depend on RDKit.

## Prototype dependency boundary
This build loads RDKit.js/WASM from the official package distribution through unpkg on first EnviroDesign use. A production build should self-host a pinned reviewed RDKit.js/WASM release and its BSD-3-Clause notices rather than depending on a public CDN.

## Security rule
Do not change or bypass Windows/organisation Application Control policy to make the app run. The software architecture should work within the policy.

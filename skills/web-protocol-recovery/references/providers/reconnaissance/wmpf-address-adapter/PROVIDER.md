# WMPF Address Adapter

## Select When

- The user explicitly asks to update WMPF/WeChat native hook addresses, offsets, or `addresses.<version>.json`.
- The target is a local WMPFDebugger tree owned or explicitly provided by the user.
- The task names `WMPFDebugger`, `frida/config`, `LoadStartHookOffset`, `CDPFilterHookOffset`, `SceneOffsets`, `flue.dll`, or `WeChatAppEx.exe`.

## Do Not Select When

- The task only needs miniapp network, script, WebView, AppService, or CDP evidence. Use `wechat-miniapp`.
- The target is an unrelated native executable, DLL, APK, firmware image, or desktop application.
- The user asks to download an address database or use an address file from another website.
- The user has not authorized the local WMPFDebugger tree and exact configuration path.

This Provider is a local maintenance capability. It analyzes the WMPF runtime already installed on the user's machine and writes only the explicitly assigned address configuration. It does not perform network requests, collect account/session data, inject a protocol collector, or own final live egress.

## Inputs

Accept one of:

- A WMPFDebugger root containing `frida/config` and the updater script.
- A local WMPF runtime directory containing `flue.dll` or `WeChatAppEx.exe`.
- A concrete PE path plus the WMPF version when automatic discovery is unavailable.

The default runtime discovery is `%APPDATA%\\Tencent\\xwechat\\xplugin\\Plugins\\RadiumWMPF\\<version>\\extracted\\runtime`. Newer WMPF versions use `flue.dll`; older versions use `WeChatAppEx.exe`, matching the target hook's module selection.

## Workflow

1. Confirm the exact WMPFDebugger root and `frida/config` output path. Treat the path as an operational configuration write, not as project evidence.
2. Locate the newest installed WMPF runtime, or use the user-supplied `--version`/`--pe` input.
3. Parse the local PE with `pefile` and disassemble x64 code with `capstone`. Never fetch a remote address database.
4. Find `CDPFilterHookOffset` from the `SendToClientFilter` RIP-relative xref, its containing function, and the first direct call target. Require the target to be inside the executable code section.
5. Find `LoadStartHookOffset` using a unique `OnLoadStart` entry signature. A weak or ambiguous string xref is only a candidate list, never an automatic write.
6. Resolve `SceneOffsets` from the current binary when a structure pattern is proven. A same-layout value from the nearest local config may be used only when the current build has a matching verified layout; report its source version.
7. Validate JSON shape, RVA/code-section bounds, function boundaries, and uniqueness before writing.
8. Write `frida/config/addresses.<version>.json` atomically. Do not overwrite a different existing file unless the exact path has `--force` approval.
9. Return the generated values, evidence sources, confidence, validation status, and any residual manual verification requirement.

## Execution And Write Boundary

- PE parsing is local-only and read-only until the final config write.
- Installing `pefile`/`capstone` is a dependency-install action and requires the work-order execution policy approval.
- The updater may write only the exact user-assigned `frida/config/addresses.<version>.json` path. Do not write dumps, credentials, process state, or raw binary copies into `js_reverse_cache`.
- Use `--dry-run` first when the output is not already known. Use `--write` only after the exact output path is assigned.
- Never kill WeChat processes, stop an external WMPFDebugger service, or take over an unknown debugger listener as part of address analysis.
- Dynamic Frida validation is optional and read-only. Attach only to a user-owned WMPF process, keep the hook bounded, detach after the check, and do not retain raw memory or session values.

## Acceptance

The Provider result is complete only when all of these hold:

- The WMPF version and source PE path are identified.
- `LoadStartHookOffset` is unique and maps to a valid code function.
- `CDPFilterHookOffset` is unique, maps to a valid code function, and passes the first-call sanity check.
- `SceneOffsets` has six integers matching the hook's dereference contract, either proven from the current binary or explicitly reported as a verified local-layout reuse.
- The output parses as the exact configuration shape consumed by WMPFDebugger.
- The file is written atomically only to the assigned config path.
- If any item is uncertain, return `status=blocked` with candidates and the precise manual fact needed. Do not claim that a generated file is runtime-compatible based only on a plausible RVA.

## Handoff

Return:

- `provider: wmpf-address-adapter`, `role: reconnaissance`;
- WMPF version and PE/module name;
- generated address values and evidence method for each field;
- output path and whether it was written or dry-run only;
- dependency and dynamic-validation status;
- one precise blocker if the binary changed its signatures.

After address adaptation, return control to `web-protocol-recovery` or `wechat-miniapp`. This Provider does not continue into network capture or collector implementation automatically.

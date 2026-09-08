# WMPF Address Adapter Operations

## Local Commands

Run from the WMPFDebugger root:

```text
python -m pip install -r tools/requirements.txt
python tools/update_addresses.py
python tools/update_addresses.py --write
python tools/update_addresses.py --version <WMPF_VERSION> --write
```

The updater discovers the newest local RadiumWMPF runtime by default. Use `--pe <path>` only when the runtime is outside the standard installation tree; provide `--version` with it so the output filename is unambiguous.

## Evidence Checklist

- Confirm `flue.dll` for WMPF versions at or above the target's module boundary, otherwise `WeChatAppEx.exe`.
- Confirm the PE image base and `.text` section mapping.
- Confirm `SendToClientFilter` has one usable RIP-relative xref and the first-call target is inside `.text`.
- Confirm `OnLoadStart` has exactly one strong entry-signature match. Four generic string-registration xrefs are not enough.
- Confirm `SceneOffsets` has six elements and the selected local layout is documented by source version when reused.
- Confirm the generated JSON can be parsed by the WMPFDebugger loader.

## Failure Handling

- Missing `pefile` or `capstone`: stop at `executionPolicy`; do not silently replace static analysis with remote data.
- Zero or multiple strong matches: return candidates and stop before writing.
- A changed binary layout: mark `SceneOffsets` as unverified and require a focused native analysis step.
- Existing different config: stop unless the user explicitly allows `--force` for that exact path.
- A running WeChat process is not required for static analysis. If dynamic validation is requested, attach only to the user's process and release it after the bounded check.

## Report Template

```text
provider: wmpf-address-adapter
status: complete|blocked
wmpfVersion: <integer>
module: flue.dll|WeChatAppEx.exe
loadStart: <RVA and evidence method>
cdpFilter: <RVA and evidence method>
sceneOffsets: [o0, o1, o2, o3, o4, o5]
sceneLayoutSource: current-binary|local-config-<version>|unverified
output: <exact assigned path or dry-run>
dynamicValidation: not-requested|passed|blocked
blocker: <one sentence or none>
```

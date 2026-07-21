# Path Upgrade Checklist

Use this when env-patch is loading but not converging, or when a task asks whether to move to another runtime. The goal is to avoid both premature iv8 escalation and overgrown Node patches.

## Stay In Env-Patch (modular default)

Stay on the minimal Node/vm/jsdom path when any item is still unresolved:

1. `moduleLoadErrors` or high-confidence `undefinedPaths` are not reduced to a named blocker.
2. Entry function, call parameters, return format, or SDK init data is not fixed.
3. Request failure still looks like cookie/header/session/timing, not environment semantics.
4. Browser comparison has not isolated the first divergence.
5. A smaller env module or project-local `js_reverse_cache/env/ai-generated/*.js` patch can test the current hypothesis.

## Optional Advanced Path (still Node)

Stay on Node and open `scripts/advanced-env-engine.js` only when:

1. Modular diagnose has already run at least once, **or** evidence is already limited to native/`toString`/descriptor/constructor shape.
2. You need `setFuncNative` / `getNativeProto` / targeted `monitor`, or cache-area hand-written verification before promoting `mod.js` / `main.js`.
3. The task still rejects iv8 (or iv8 is not yet justified by host-boundary evidence).

Read `references/advanced-env-path.md`, copy the engine into `js_reverse_cache/env/`, and take only needed shells from `references/browser-stubs.md`. `env.report()` completeness is not signer proof.

## Move To iv8 Or Browser-Like Runtime

Escalate to iv8 only when evidence shows Node/vm environment patches are the wrong host boundary:

1. Browser-like XHR/fetch/netLog behavior is part of the artifact generation path.
2. Cross-realm, native descriptor, Error stack, Worker, or event semantics remain the first divergence after modular modules and, when tried, the advanced path.
3. The target depends on browser scheduling or object internals that the env module tree and advanced engine cannot model faithfully.
4. A registry runtime case matches and passes its own gate.

Do not move to iv8 just because a few browser globals are missing, the entry has not been isolated, or samples from different script generations are mixed.

## Stop For WASM Or Engine Blocker

Stop env-patch and return a blocker when:

1. the decisive logic lands in `WebAssembly.instantiate` or `instantiateStreaming` and JS only bridges memory;
2. opcode-level VMP checks hide the first divergence from hookable JS APIs;
3. output is a downgrade variant despite coherent browser seeds and fixed vectors;
4. the required behavior depends on a real engine feature the Provider cannot emulate.

## Runtime Boundary

Default architecture: `env/core/*` monitors, the `env/` module tree, `gap-log-module-advisor.js`, project-local patches. Optional advanced: `advanced-env-engine.js` under the gate above. Do not treat advanced as the first-turn default. If modular and advanced Node paths still fail on host semantics, return a blocker or move to iv8.

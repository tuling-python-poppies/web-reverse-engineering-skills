# Path Upgrade Checklist

Use this when env-patch is loading but not converging, or when a task asks whether to move to another runtime. The goal is to avoid both premature iv8 escalation and overgrown Node patches.

## Stay In Env-Patch

Stay on the minimal Node/vm/jsdom path when any item is still unresolved:

1. `moduleLoadErrors` or high-confidence `undefinedPaths` are not reduced to a named blocker.
2. Entry function, call parameters, return format, or SDK init data is not fixed.
3. Request failure still looks like cookie/header/session/timing, not environment semantics.
4. Browser comparison has not isolated the first divergence.
5. A smaller env module or project-local `js_reverse_cache/env/ai-generated/*.js` patch can test the current hypothesis.

## Move To iv8 Or Browser-Like Runtime

Escalate to iv8 only when evidence shows Node/vm environment patches are the wrong host boundary:

1. Browser-like XHR/fetch/netLog behavior is part of the artifact generation path.
2. Cross-realm, native descriptor, Error stack, Worker, or event semantics remain the first divergence after minimal modules.
3. The target depends on browser scheduling or object internals that the env module tree cannot model faithfully.
4. A registry runtime case matches and passes its own gate.

Do not move to iv8 just because a few browser globals are missing, the entry has not been isolated, or samples from different script generations are mixed.

## Stop For WASM Or Engine Blocker

Stop env-patch and return a blocker when:

1. the decisive logic lands in `WebAssembly.instantiate` or `instantiateStreaming` and JS only bridges memory;
2. opcode-level VMP checks hide the first divergence from hookable JS APIs;
3. output is a downgrade variant despite coherent browser seeds and fixed vectors;
4. the required behavior depends on a real engine feature the Provider cannot emulate.

## Runtime Boundary

This provider has one architecture: `env/core/*` monitors, the `env/` module tree, `references/loading-order.md`, `scripts/gap-log-module-advisor.js` for gap-log shortlisting, and project-local patches. Do not add a second parallel runtime engine under env-patch. If those tools cannot model native/prototype/descriptor pressure, return a blocker or move to iv8.

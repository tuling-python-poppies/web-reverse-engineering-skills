#!/usr/bin/env node
"use strict";

// This historical helper formerly executed caller-supplied GT4 bundle and GCT
// source through node:vm. No reviewed capability-denied adapter is bundled, so
// it must remain an explicit fail-closed stub rather than an alternate bypass.
process.stderr.write(
  "GT4 target-JS bundle execution is disabled: use gt4_pure_replay.py or a future reviewed sandbox adapter.\n"
);
process.exitCode = 2;

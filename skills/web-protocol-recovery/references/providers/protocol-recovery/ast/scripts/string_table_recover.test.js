"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const tool = require("./string_table_recover.js");

function fixture(rotation = false) {
  return [
    "function AA(){var a=['S0','S1','S2','S3','S4','S5','S6','S7','S8','S9','S10','S11','S12','S13','S14','S15'];AA=function(){return a};return AA()}",
    "function DD(i,k){var t=AA();return DD=function(i,k){i=i-50;var v=t[i];if(DD.ok===void 0){var b=function(x){var o='';for(var j=0;j<x.length;j++){o+=String.fromCharCode(x.charCodeAt(j))}return o};DD.ok=b}return v},DD(i,k)}",
    rotation ? "(function(C,c){var p=C(),d=DD;for(var n=0;n<3;n++){d(50,'k');p.push(p.shift())}})(AA,0);" : "",
    "var q=DD;function shadow(q){return q(53,'k')}var obj={q:function(){return 'member'}};console.log(shadow(function(){return 'own'}),obj.q(53,'k'),q(54,'k'));",
    "eval(\"var z=DD;z(55,'k')\");",
  ].filter(Boolean).join("\n");
}

function runNode(file) {
  const result = spawnSync(process.execPath, [file], { encoding: "utf8", timeout: 3000 });
  return { status: result.status, stdout: String(result.stdout).trim(), stderr: String(result.stderr) };
}

function nestedFixture() {
  return "(function(){function AA(){var a=['N0','N1','N2','N3','N4','N5','N6','N7','N8','N9','N10','N11','N12','N13','N14','N15'];AA=function(){return a};return AA()}function DD(i,k){var t=AA();return DD=function(i,k){i-=50;return t[i]},DD(i,k)}var q=DD;console.log(q(53,'k'));}());";
}

function run() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "string-table-test-"));
  try {
    tool.loadBabel();
    const source = fixture(false);
    const plan = tool.inspect(source, true);
    const values = tool.runWorker(plan);
    const output = tool.transform(source, plan, values);
    const inputPath = path.join(dir, "input.js");
    const outputPath = path.join(dir, "output.js");
    fs.writeFileSync(inputPath, source, "utf8");
    fs.writeFileSync(outputPath, output, "utf8");
    assert.deepEqual(runNode(inputPath).stdout, runNode(outputPath).stdout);
    assert.match(output, /eval\("var z=DD;z\(55,'k'\)"\)/);
    assert.match(output, /obj\.q\(53,'k'\)/);
    assert.ok(!output.includes("shadow(function(){return 'own'}),\"S3\""));

    const rotated = fixture(true);
    const rotatedPlan = tool.inspect(rotated, false);
    assert.equal(rotatedPlan.rotation, true);
    const rotatedOutput = tool.transform(rotated, rotatedPlan, tool.runWorker(rotatedPlan));
    const rotatedInput = path.join(dir, "rotated.js");
    const rotatedFile = path.join(dir, "rotated.out.js");
    fs.writeFileSync(rotatedInput, rotated, "utf8");
    fs.writeFileSync(rotatedFile, rotatedOutput, "utf8");
    assert.deepEqual(runNode(rotatedInput).stdout, runNode(rotatedFile).stdout);

    assert.throws(() => tool.validatePaths(inputPath, [inputPath]), /disjoint/);
    assert.throws(() => tool.runWorker({ bootstrap: "function D(){while(true){}}", decoder: "D", pairs: [["0", [0]]] }), /failed|timed out/);

    const nested = nestedFixture();
    const nestedPlan = tool.inspect(nested, true, { decoder: "DD", array: "AA" });
    assert.equal(nestedPlan.decoder, "DD");
    assert.equal(nestedPlan.array, "AA");
    assert.equal(nestedPlan.unresolvedCalls, 0);
    assert.equal(tool.runWorker(nestedPlan).get(JSON.stringify([53, "k"])), "N3");
    console.log(JSON.stringify({ selfTest: "passed", checks: 10 }));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

module.exports = { run };

"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { parseUvConflicts } = require("./package_visualizer.cjs");

test("uv dependency check output preserves mismatched and missing requirements", () => {
  const output = "Found 2 incompatibilities\n"
    + "The package `fixture-node` requires `idna<3.20`, but `3.20` is installed\n"
    + "The package `fixture-node` requires `missing-dep[extra]>=1`, but it's not installed\n";
  assert.deepEqual(parseUvConflicts(output), [
    { package: "fixture-node", version: "", requirement: "idna<3.20",
      conflictingPackage: "idna", conflictingVersion: "3.20" },
    { package: "fixture-node", version: "", requirement: "missing-dep[extra]>=1",
      conflictingPackage: "missing-dep", conflictingVersion: "not installed" },
  ]);
});

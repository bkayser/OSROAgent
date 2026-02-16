#!/usr/bin/env node
"use strict";
const { execSync } = require("child_process");
const path = require("path");

const root = path.resolve(__dirname, "..");
const cmd =
  "python ingest.py && ./scripts/build-push.sh && ./scripts/update-vector-store.sh && ./scripts/deploy-cloudrun.sh";
execSync(cmd, { stdio: "inherit", cwd: root });

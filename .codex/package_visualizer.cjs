"use strict";

const { execFile } = require("node:child_process");
const { existsSync, readFileSync, realpathSync } = require("node:fs");
const path = require("node:path");
const { promisify } = require("node:util");

const run = promisify(execFile);
const normalize = (name) => name.toLowerCase().replace(/[-_.]+/g, "-");

module.exports = function connectVisualizer(host, vscode, parseToml) {
  const folder = vscode.workspace.workspaceFolders?.[0]?.uri;
  if (!folder || folder.scheme !== "file" || !existsSync(folder.fsPath)) return;
  const { root, uv } = JSON.parse(readFileSync(path.join(__dirname, "comfyui-uv.json"), "utf8"));
  if (realpathSync(folder.fsPath) !== root) return;

  const manifest = path.join(root, "pyproject.toml");
  const python = path.join(root, ".venv", "bin", "python");
  const script = path.join(root, ".codex", "uv_workspace.py");
  const scanner = host.scanner;
  const findDepFiles = scanner.findDepFiles.bind(scanner);
  scanner.findDepFiles = (directory) =>
    path.resolve(directory) === path.resolve(folder.fsPath) ? [manifest] : findDepFiles(directory);
  const parseDepFile = scanner.parseDepFile.bind(scanner);
  scanner.parseDepFile = (file, directory) => {
    const packages = parseDepFile(file, directory);
    if (file !== manifest) return packages;
    const groups = parseToml(readFileSync(manifest, "utf8"))["dependency-groups"] || {};
    for (const [group, entries] of Object.entries(groups)) {
      for (const entry of entries) {
        if (typeof entry !== "string") continue;
        const match = /^([\w.-]+)(?:\[([^\]]+)\])?(.*)$/.exec(entry);
        if (!match) continue;
        packages.push({
          name: normalize(match[1]),
          specifiedVersion: match[3].trim(),
          installedVersion: "",
          source: "pyproject.toml",
          extras: match[2]?.split(",").map((extra) => extra.trim()) || [],
          requires: [],
          group: group === "dev" ? "dev" : "main",
          environment: "main",
        });
      }
    }
    return packages;
  };
  scanner.resolveUvPath = async () => uv;
  scanner.resolvePythonPath = () => python;
  scanner.getActiveProjectRoot = () => root;

  let busy = false;
  async function apply(message, args) {
    if (!vscode.workspace.isTrusted || !existsSync(script)) {
      vscode.window.showErrorMessage("ComfyUI uv actions require a trusted workspace with .codex/uv_workspace.py.");
      return;
    }
    if (busy) return;
    busy = true;
    try {
      if (await vscode.window.showWarningMessage(message, { modal: true }, "Run uv") !== "Run uv") return;
      const env = { ...process.env, PATH: [path.dirname(uv), process.env.PATH].filter(Boolean).join(path.delimiter) };
      const { stdout, stderr } = await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "ComfyUI uv" },
        () => run(python, [script, ...args], { cwd: root, env })
      );
      host.logger.info(`ComfyUI uv ${args.join(" ")} completed.\n${stdout}${stderr}`);
      vscode.window.showInformationMessage("ComfyUI uv completed. Package compatibility checks passed.");
      await host.refreshVisualizer();
    } catch (error) {
      host.logger.error(error.stderr || String(error));
      host.logger.show();
      const detail = error.stderr?.trim().split("\n").at(-1) || error.message;
      vscode.window.showErrorMessage(`ComfyUI uv failed. ${detail}`);
    } finally {
      busy = false;
    }
  }

  const set = (name, version) => {
    if (!name) return;
    return apply(`Resolve and install ${name}${version ? `==${version}` : ""} using ComfyUI's uv lock?`,
      version ? ["set", name, version] : ["set", name]);
  };
  host.migrateToUv = (mode) => mode === "automatic"
    ? apply("Apply the ComfyUI uv lock to .venv? Existing node-pack packages are kept.", ["migrate"])
    : vscode.workspace.openTextDocument(manifest).then((document) => vscode.window.showTextDocument(document));
  host.installNewPackage = set;
  host.installAllPackages = (names) => names.length === 1 ? set(names[0]) : showPolicy();
  host.updatePackage = (name) => {
    if (!name) return;
    const candidate = host.lastCheckResults.find((item) => normalize(item.packageName) === normalize(name));
    if (!candidate?.latestVersion) {
      return vscode.window.showWarningMessage(`Refresh the package list to find a version for ${name}.`);
    }
    return set(name, candidate.latestVersion);
  };
  host.updateAllPackages = (names) => names.length === 1 ? host.updatePackage(names[0]) : showPolicy();
  host.pinVersion = set;
  host.pinPackageToVersion = set;
  host.rollbackPackage = (name, version) => version ? set(name, version) : showPolicy();
  host.removeFromRequirements = (name) => apply(
    `Remove ${name} from the uv workspace group? Its installed copy will be kept for node packs.`,
    ["remove", name]);

  function showPolicy() {
    return vscode.window.showWarningMessage(
      "ComfyUI uses pyproject.toml and uv.lock. Use the Visualizer's single-package actions or Tools → Migrate to uv.");
  }

  for (const action of [
    "bulkSyncRequirementsToInstalled", "syncRequirementsToInstalled", "fixConflict",
    "removeUnusedPackagesWithSnapshot", "generateRequirements", "createRequirementsFile",
    "migrateToPoetry", "selectManualRequirements", "handleUpdatePip", "handleSelectActiveVenvProject",
  ]) {
    host[action] = showPolicy;
  }
  host.snapshotHandler.restoreSnapshot = showPolicy;
  host.logger.info(`ComfyUI uv workspace bridge active for ${root}`);
};

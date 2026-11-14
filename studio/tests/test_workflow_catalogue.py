import csv
import json
import os
import struct
import zlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workflow_catalogue import (Image, REPORT_FILES, describe_graph, extension_sources, graph_kind,
                                local_schemas, payloads, scan, write_report)

if Image is not None:
    from PIL.PngImagePlugin import PngInfo


def ui(model="weights.safetensors"):
    return {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [model]}], "links": []}


def api(model="weights.gguf"):
    return {"1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": model}, "_meta": {"title": "Loader"}}}


class CatalogueTests(unittest.TestCase):
    @unittest.skipIf(Image is None, 'Pillow unavailable')
    def test_jpeg_named_png_does_not_abort_catalogue(self):
        path = self.root / 'user/default/workflows/not-png.png'
        path.parent.mkdir(parents=True)
        Image.new('RGB', (2, 2)).save(path, format='JPEG')
        report = scan(self.root, self.output)
        self.assertEqual(report['sources'][0]['status'], 'parse_or_read_error')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "studio/workflow-review"
        # Never scan the host interpreter's installed templates in isolated tests.
        self.packages = patch("workflow_catalogue.sys.path", [])
        self.packages.start()
        self.addCleanup(self.packages.stop)

    def put(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")
        return target

    def test_ui_api_and_wrappers(self):
        self.assertEqual(graph_kind(ui()), "ui")
        self.assertEqual(graph_kind(api()), "api")
        pairs = list(payloads({"workflow": ui(), "prompt": json.dumps(api())}))
        self.assertEqual({p[1] for p in pairs}, {"ui", "api"})
        self.assertEqual(list(payloads({"extra_pnginfo": {"workflow": ui()}}))[0][0], "$/extra_pnginfo/workflow")

    def test_recipes_config_and_metadata_are_not_graphs(self):
        self.put("custom_nodes/builder/recipe.json", {"nodes": [{"key": "n1", "type": "UNETLoader", "settings": {}, "inputs": {}}]})
        self.put("user/default/workflows/example.metadata.json", {"workflow_format": "ui", "node_count": 5, "sub_type": "workflow"})
        self.put("user/config.json", {"templates": ["one"], "model_name": "not-a-graph.pt"})
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["unique_workflows"], 0)
        self.assertEqual(report["counts"]["payload_statuses"], {"metadata_or_config": 2, "recipe": 1})

    def test_duplicates_keep_every_alias_and_source_hash(self):
        first = self.put("custom_nodes/one/example.json", ui())
        second = self.put("user/default/workflows/saved.json", ui())
        second.write_text(json.dumps(ui(), indent=4))
        before = first.read_bytes(), second.read_bytes()
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["unique_workflows"], 1)
        self.assertEqual(report["counts"]["graph_occurrences"], 2)
        self.assertEqual(report["counts"]["duplicate_aliases"], 1)
        aliases = report["workflows"][0]["aliases"]
        self.assertEqual(len({a["source_sha256"] for a in aliases}), 2)
        self.assertTrue(all(Path(a["absolute"]).is_absolute() and not Path(a["relative"]).is_absolute() for a in aliases))
        self.assertEqual(before, (first.read_bytes(), second.read_bytes()))

    def test_preserve_variants_and_ui_api_uncertainty(self):
        self.put("user/a.json", ui())
        self.put("user/b.json", ui("different.safetensors"))
        self.put("user/prompt.json", api())
        moved = ui()
        moved["nodes"][0]["pos"] = [100, 200]
        self.put("user/moved.json", moved)
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["unique_workflows"], 4)

    def test_nested_subgraphs_and_virtual_nodes(self):
        graph = {"nodes": [{"id": 1, "type": "outer"}, {"id": 2, "type": "SetNode"}, {"id": 3, "type": "GetNode"}],
                 "definitions": {"subgraphs": [
                     {"id": "outer", "nodes": [{"id": 4, "type": "inner"}], "definitions": {"subgraphs": [
                         dict(ui(), id="inner")]}}
                 ]}}
        result = describe_graph(graph, "ui", {"UNETLoader": {"python_module": "nodes"}})
        self.assertEqual(result["blockers"], [])
        self.assertEqual(len(result["nodes"]), 5)
        self.assertEqual(result["model_references"][0]["scope"], "root/outer/inner")
        self.assertEqual(result["nodes"][-1]["provider"], "nodes")

    def test_shared_subgraph_registry(self):
        graph = {"nodes": [{"id": 1, "type": "a"}], "definitions": {"subgraphs": [
            {"id": "a", "nodes": [{"id": 2, "type": "b"}]}, dict(ui(), id="b")]}}
        result = describe_graph(graph, "ui", {"UNETLoader": {}})
        self.assertEqual(result["blockers"], [])
        self.assertEqual(len(result["nodes"]), 3)

    def test_disabled_and_standalone_candidates(self):
        self.put("custom_nodes/enabled/example.json", ui())
        self.put("custom_nodes/.disabled/off/example.json", api())
        self.put("custom_nodes/suffix.disabled/example.json", ui())
        (self.root / "custom_nodes/single.py").write_text("raise RuntimeError('must not import')\n")
        (self.root / "custom_nodes/example.py.example").write_text("# example\n")
        (self.root / "custom_nodes/parked.py.disabled").write_text("# disabled\n")
        entries = {Path(e["absolute"]).name: e for e in extension_sources(self.root)}
        self.assertEqual(len(entries), 6)
        for name in ("off", "suffix.disabled", "example.py.example", "parked.py.disabled"):
            self.assertEqual(entries[name]["placement"], "disabled_location")
        self.assertEqual(entries["enabled"]["load_status"], "not_inferred_from_placement")
        report = scan(self.root, self.output)
        single = next(e for e in report["extensions"] if e["relative"] == "custom_nodes/single.py")
        self.assertEqual(single["unique_workflows"], 0)

    def test_model_extraction_api_ui_and_dynamic_selections(self):
        graph = api()
        graph["1"]["inputs"].update({"lora_name": "folder/character.safetensors", "image": ["2", 0], "vae": ["6", 0],
                                      "model_name": "${model}", "prompt": "https://example.invalid/file.pt"})
        result = describe_graph(graph, "api", None)
        refs = {m["reference"] for m in result["model_references"]}
        self.assertEqual(refs, {"weights.gguf", "folder/character.safetensors", "${model}"})
        result = describe_graph(ui(), "ui", None)
        self.assertEqual(result["model_references"][0]["reference"], "weights.safetensors")
        self.assertEqual(result["model_references"][0]["availability"], "not_checked")

    def test_schema_snapshot_not_runtime_proof(self):
        graph = ui()
        graph["nodes"].append({"id": 2, "type": "MutedMissing", "mode": 4})
        result = describe_graph(graph, "ui", {})
        self.assertEqual(result["blockers"], ["Node type unavailable in localhost schema snapshot: UNETLoader"])
        self.assertEqual(result["test_status"], "mapped / not run")
        self.assertEqual(describe_graph(graph, "ui", None)["blockers"], [])

    @unittest.skipIf(Image is None, "Pillow is optional")
    def test_png_paired_metadata_and_aliases(self):
        target = self.root / "custom_nodes/example/graph.png"
        target.parent.mkdir(parents=True)
        metadata = PngInfo()
        metadata.add_text("workflow", json.dumps(ui()), zip=True)
        metadata.add_text("prompt", json.dumps(api()))
        Image.new("RGB", (1, 1)).save(target, pnginfo=metadata)
        self.put("user/copy.json", ui())
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["unique_workflows"], 2)
        self.assertEqual(report["counts"]["graph_occurrences"], 3)
        self.assertEqual(report["counts"]["duplicate_aliases"], 1)

    @unittest.skipIf(Image is None, "Pillow is optional")
    def test_png_parse_error_does_not_hide_other_payload(self):
        target = self.root / "user/graph.png"
        target.parent.mkdir(parents=True)
        metadata = PngInfo()
        metadata.add_text("workflow", "not json")
        metadata.add_text("prompt", json.dumps(api()))
        Image.new("RGB", (1, 1)).save(target, pnginfo=metadata)
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["payload_statuses"], {"graph": 1, "parse_error": 1})

    def test_unreadable_malformed_and_unsupported_candidates(self):
        self.put("user/broken.json", {}).write_text("{")
        self.put("user/malformed.json", {"nodes": [{"type": "NoID"}]})
        self.put("user/config.json", {})
        self.put("user/archive.zip", {})
        self.put("user/picture.webp", {})
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["source_files"], 5)
        self.assertEqual(report["counts"]["source_statuses"]["parse_or_read_error"], 1)
        self.assertEqual(report["counts"]["source_statuses"]["uninspected_media_or_archive"], 2)
        self.assertEqual(report["counts"]["payload_statuses"]["malformed_graph"], 1)

    def test_no_recursive_inventory_of_generated_output(self):
        output = self.root / "user/catalogue"
        self.put("user/real.json", ui())
        self.put("user/catalogue/tests/generated.json", api())
        first = scan(self.root, output)
        write_report(first, output)
        second = scan(self.root, output)
        self.assertEqual(first["counts"], second["counts"])
        self.assertEqual(first["counts"]["source_files"], 1)
        self.assertTrue((output / "blockers/workflows.csv").exists())
        self.assertTrue((output / "results/README.md").exists())

    def test_output_cannot_replace_scan_roots_or_their_ancestors(self):
        source = self.put("user/default/original.json", ui())
        self.put("custom_nodes/example/original.json", api())
        report = scan(self.root, self.output)
        for output in (self.root, self.root.parent, self.root / "user", self.root / "custom_nodes",
                       self.root / "custom_nodes/example"):
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    scan(self.root, output)
                with self.assertRaises(ValueError):
                    write_report(report, output)
        self.assertEqual(json.loads(source.read_text()), ui())
        self.assertFalse((self.root / "workflows.json").exists())

    def test_output_symlink_and_ancestor_are_rejected(self):
        source = self.put("user/original.json", ui())
        report = scan(self.root, self.output)
        link = self.root / "linked"
        link.symlink_to(source.parent, target_is_directory=True)
        for output in (link, link / "catalogue", self.root / "dangling" / "catalogue"):
            if output.parent.name == "dangling":
                output.parent.symlink_to(self.root / "missing", target_is_directory=True)
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    scan(self.root, output)
                with self.assertRaises(ValueError):
                    write_report(report, output)
        self.assertEqual(json.loads(source.read_text()), ui())
        self.assertFalse((source.parent / "catalogue").exists())

    def test_report_target_symlinks_are_rejected_before_writes(self):
        source = self.put("user/original.json", ui())
        before = source.read_bytes()
        report = scan(self.root, self.output)
        for name in REPORT_FILES:
            for destination in (source, self.root / "missing"):
                with self.subTest(name=name, destination=destination), tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / "catalogue"
                    target = output / name
                    target.parent.mkdir(parents=True)
                    target.symlink_to(destination)
                    with self.assertRaises(ValueError):
                        write_report(report, output)
                    self.assertTrue(target.is_symlink())
                    self.assertEqual(source.read_bytes(), before)
                    self.assertFalse(destination.name == "missing" and destination.exists())
                    self.assertEqual(list(output.rglob("*.tmp")), [])
                    self.assertTrue(all(not (output / other).exists() for other in REPORT_FILES if other != name))

    def test_report_parent_symlinks_are_rejected(self):
        source = self.put("user/original.json", ui())
        report = scan(self.root, self.output)
        for parent in ("tests", "results", "blockers"):
            with self.subTest(parent=parent), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "catalogue"
                output.mkdir()
                (output / parent).symlink_to(source.parent, target_is_directory=True)
                with self.assertRaises(OSError):
                    write_report(report, output)
                self.assertFalse((output / "workflows.json").exists())
                self.assertFalse((source.parent / "README.md").exists())

    def test_pruned_original_inventory_is_not_overwritten(self):
        output = self.root / "user/existing"
        source = self.put("user/existing/workflows.json", ui())
        before = source.read_bytes()
        report = scan(self.root, output)
        with self.assertRaises(ValueError):
            write_report(report, output)
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse((output / "extensions.csv").exists())

    def test_existing_targets_need_a_dedicated_catalogue(self):
        report = scan(self.root, self.output)
        self.output.mkdir(parents=True)
        original = self.output / "README.md"
        original.write_text("Original documentation\n")
        with self.assertRaises(ValueError):
            write_report(report, self.output)
        self.assertEqual(original.read_text(), "Original documentation\n")
        self.assertFalse((self.output / "workflows.json").exists())

    def test_source_hardlink_target_is_rejected(self):
        source = self.put("user/original.json", ui())
        report = scan(self.root, self.output)
        self.output.mkdir(parents=True)
        os.link(source, self.output / "extensions.csv")
        with self.assertRaises(ValueError):
            write_report(report, self.output)
        self.assertEqual(json.loads(source.read_text()), ui())
        self.assertFalse((self.output / "workflows.json").exists())

    def test_atomic_write_failure_preserves_previous_inventory(self):
        report = scan(self.root, self.output)
        write_report(report, self.output)
        before = (self.output / "workflows.json").read_bytes()
        report["generated_at"] = "changed"
        with patch("workflow_catalogue.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(OSError, "replace failed"):
                write_report(report, self.output)
        self.assertEqual((self.output / "workflows.json").read_bytes(), before)
        self.assertEqual(list(self.output.rglob("*.tmp")), [])

    def test_csv_formula_scalars_are_escaped_but_json_is_exact(self):
        graph = ui()
        graph["extra"] = {"title": "=HYPERLINK(\"bad\")"}
        self.put("user/original.json", graph)
        report = scan(self.root, self.output)
        workflow = report["workflows"][0]
        values = [prefix + formula for prefix in ("", " ", "\t", "\r\n", "\x00\x1f", "\u2003\t")
                  for formula in ("=1+1", "+1", "-1", "@SUM(A1)")]
        workflow["title"] = values[0]
        workflow["unknowns"] = values + ["ordinary", "1+1"]
        workflow["model_references"][0]["reference"] = "\t@model.safetensors"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_report(report, output)
            self.assertEqual(json.loads((output / "workflows.json").read_text()), report)
            with (output / "blockers/workflows.csv").open(newline="") as stream:
                details = [row["detail"] for row in csv.DictReader(stream)]
            self.assertEqual(details, ["'" + value for value in values] + ["ordinary", "1+1"])
            with (output / "workflow-matrix.csv").open(newline="") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["title"], "'" + values[0])
            self.assertEqual(json.loads(row["unknowns"]), workflow["unknowns"])
            with (output / "model-references.csv").open(newline="") as stream:
                self.assertEqual(next(csv.DictReader(stream))["reference"], "'\t@model.safetensors")

    def test_separate_blueprint_package_and_studio_families(self):
        self.put("blueprints/core.json", ui())
        self.put("studio/templates/local.json", api())
        self.put(".venv/lib/python3.13/site-packages/comfyui_workflow_templates_json/templates/pkg.app.json", ui())
        self.put(".venv/lib/python3.13/site-packages/comfyui_workflow_templates_core/manifest.json", {"templates": []})
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["extensions"], 0)
        self.assertEqual(report["counts"]["unique_workflows"], 2)
        self.assertEqual({s["family"] for s in report["sources"]}, {"core_blueprint", "studio_template", "installed_template_package"})

    def test_wrapped_errors_and_recipes_keep_payload_locations(self):
        self.put("user/wrapped.json", {"workflow": "{broken", "prompt": api()})
        self.put("user/recipe.json", {"workflow": {"nodes": [{"key": "n", "settings": {}}]}})
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["payload_statuses"], {"graph": 1, "parse_error": 1, "recipe": 1})
        broken = next(s for s in report["sources"] if s["relative"] == "user/wrapped.json")
        self.assertTrue(any(p["pointer"] == "$/workflow" and p["status"] == "parse_error" for p in broken["payloads"]))

    def test_plain_prompt_config_is_not_a_parse_error(self):
        self.put("user/preset.json", {"prompt": "Draw a landscape", "seed": 123})
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["payload_statuses"], {"metadata_or_config": 1})

    def test_unreadable_disabled_directory_is_reported(self):
        disabled = self.root / "custom_nodes/.disabled"
        disabled.mkdir(parents=True)
        self.put("custom_nodes/good/workflow.json", ui())
        original = Path.iterdir

        def iterdir(path):
            if path == disabled:
                raise PermissionError("directory unreadable")
            return original(path)

        issues = []
        with patch.object(Path, "iterdir", iterdir):
            entries = extension_sources(self.root, issues)
        self.assertEqual(len(entries), 1)
        self.assertEqual(issues[0]["status"], "unreadable_directory")

    def test_registry_metadata_with_nodes_is_not_malformed_graph(self):
        self.put("user/registry.json", {"nodes": [{"id": "package", "author": "author", "description": "extension"}]})
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["payload_statuses"], {"metadata_or_config": 1})

    def test_serialized_widget_model_selections(self):
        graph = ui()
        graph["nodes"][0]["widgets_values"] = []
        graph["nodes"][0]["widgets_values_named"] = {"lora_data": json.dumps({"loras": [{"name": "folder/lora.safetensors", "on": True}]})}
        result = describe_graph(graph, "ui", None)
        self.assertEqual([m["reference"] for m in result["model_references"]], ["folder/lora.safetensors"])

    def test_unreadable_standalone_does_not_abort_discovery(self):
        standalone = self.root / "custom_nodes/denied.py"
        standalone.parent.mkdir()
        standalone.write_text("# no import\n")
        issues = []
        with patch("workflow_catalogue.file_hash", side_effect=PermissionError("unreadable")):
            entries = extension_sources(self.root, issues)
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0]["source_sha256"])
        self.assertEqual(issues[0]["status"], "extension_inspection_error")

    def test_malformed_nested_graph_is_reported(self):
        graph = ui()
        graph["definitions"] = {"subgraphs": [{"id": "bad", "nodes": [{"type": "NoID"}]}]}
        self.put("user/bad.json", graph)
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["unique_workflows"], 0)
        self.assertEqual(report["sources"][0]["status"], "parse_or_read_error")
        self.assertIn("Malformed subgraph", report["sources"][0]["error"])

    @unittest.skipIf(Image is None, "Pillow is optional")
    def test_png_metadata_after_idat(self):
        target = self.root / "user/late.png"
        target.parent.mkdir(parents=True)
        Image.new("RGB", (1, 1)).save(target)
        data = b"workflow\x00" + json.dumps(ui()).encode()
        chunk = struct.pack(">I", len(data)) + b"tEXt" + data + struct.pack(">I", zlib.crc32(b"tEXt" + data))
        original = target.read_bytes()
        target.write_bytes(original[:-12] + chunk + original[-12:])
        report = scan(self.root, self.output)
        self.assertEqual(report["counts"]["graph_occurrences"], 1)

    def test_png_without_pillow_is_visible_as_uninspected(self):
        self.put("user/unknown.png", {})
        with patch("workflow_catalogue.Image", None):
            report = scan(self.root, self.output)
        self.assertEqual(report["sources"][0]["status"], "uninspected_png_pillow_unavailable")

    def test_fixed_loopback_schema_request(self):
        with patch("workflow_catalogue.HTTPConnection") as factory:
            connection = factory.return_value
            connection.getresponse.return_value.status = 200
            connection.getresponse.return_value.read.return_value = b'{"Loader": {"python_module": "nodes"}}'
            schemas, info = local_schemas(8188)
            factory.assert_called_once_with("127.0.0.1", 8188, timeout=15)
            connection.request.assert_called_once_with("GET", "/object_info")
            connection.close.assert_called_once()
            self.assertEqual(info["node_types"], 1)
            self.assertIn("Loader", schemas)


if __name__ == "__main__":
    unittest.main()

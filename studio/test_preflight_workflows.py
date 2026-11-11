import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import preflight_workflows as preflight
import workflow_catalogue as catalogue


SCHEMAS = {"Loader": {"input": {"required": {"model": [["present.safetensors"]]}}}}


def ui(kind="Loader", model="present.safetensors"):
    return {"nodes": [{"id": 1, "type": kind, "widgets_values": [model]}], "links": []}


def api(inputs=None):
    return {"1": {"class_type": "Loader", "inputs": {} if inputs is None else inputs}}


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self, graph, value=None, pointer="$", name="workflow.json"):
        path = self.root / name
        path.write_text(json.dumps(graph if value is None else value))
        return self.record(path, graph, pointer)

    def record(self, path, graph, pointer):
        return {"id": "wf-" + preflight.graph_hash(graph), "title": "test",
                "format": catalogue.graph_kind(graph), "graph_sha256": preflight.graph_hash(graph),
                "aliases": [{"absolute": str(path), "pointer": pointer,
                             "source_sha256": catalogue.file_hash(path)}]}

    def test_direct_ui_and_api(self):
        for graph in (ui(), api({"model": "present.safetensors"})):
            with self.subTest(graph=graph):
                workflow = self.source(graph)
                before = Path(workflow["aliases"][0]["absolute"]).read_bytes()
                row = preflight.preflight(workflow, SCHEMAS)
                self.assertEqual(row["outcome"], "static_checks_passed")
                self.assertEqual(row["runtime"], "not_run")
                self.assertEqual(Path(workflow["aliases"][0]["absolute"]).read_bytes(), before)

    def test_nested_explicit_wrappers_and_exact_pointer(self):
        graph = ui()
        workflow = self.source(graph, {"extra_pnginfo": {"workflow": json.dumps({"workflow_json": graph})},
                                       "prompt": api()}, "$/extra_pnginfo/workflow/workflow_json")
        self.assertEqual(preflight.preflight(workflow, SCHEMAS)["outcome"], "static_checks_passed")
        workflow["aliases"][0]["pointer"] = "$/extra_pnginfo/workflow"
        self.assertEqual(preflight.preflight(workflow, SCHEMAS)["outcome"], "extraction_error")

    def test_arbitrary_wrappers_and_sidecars_rejected(self):
        for value, pointer, name in (({"arbitrary": ui()}, "$/arbitrary", "config.json"),
                                     (ui(), "$", "workflow.metadata.json"),
                                     ({"workflow_format": "ui"}, "$", "metadata.json")):
            workflow = self.source(ui(), value, pointer, name)
            self.assertEqual(preflight.preflight(workflow, SCHEMAS)["outcome"], "extraction_error")

    @unittest.skipIf(catalogue.Image is None, "Pillow unavailable")
    def test_png_workflow_prompt_and_nested_wrapper(self):
        from PIL.PngImagePlugin import PngInfo

        path = self.root / "workflow.png"
        metadata = PngInfo()
        metadata.add_text("workflow", json.dumps({"extra": {"workflow": json.dumps(ui())}}))
        metadata.add_text("prompt", json.dumps(api({"model": "present.safetensors"})))
        catalogue.Image.new("RGB", (1, 1)).save(path, pnginfo=metadata)
        for graph, pointer in ((ui(), "png/workflow/extra/workflow"),
                               (api({"model": "present.safetensors"}), "png/prompt")):
            row = preflight.preflight(self.record(path, graph, pointer), SCHEMAS)
            self.assertEqual(row["outcome"], "static_checks_passed")
        with self.assertRaises(ValueError):
            preflight.extract_graph(path, "png/other")

    def test_stale_and_unavailable_sources(self):
        workflow = self.source(ui())
        path = Path(workflow["aliases"][0]["absolute"])
        path.write_text("{}")
        with patch.object(preflight.workflow_health, "check_workflow") as checker:
            self.assertEqual(preflight.preflight(workflow, SCHEMAS)["outcome"], "stale_source")
            checker.assert_not_called()
        path.unlink()
        self.assertEqual(preflight.preflight(workflow, SCHEMAS)["outcome"], "source_unavailable")

    def test_bad_json_and_graph_hash_mismatch(self):
        workflow = self.source(ui())
        workflow["graph_sha256"] = "wrong"
        self.assertEqual(preflight.preflight(workflow, SCHEMAS)["outcome"], "extraction_error")
        path = Path(workflow["aliases"][0]["absolute"])
        path.write_text("{")
        workflow["aliases"][0]["source_sha256"] = catalogue.file_hash(path)
        self.assertEqual(preflight.preflight(workflow, SCHEMAS)["outcome"], "extraction_error")

    def test_all_aliases_checked_and_fresh_alias_used(self):
        workflow = self.source(ui(), name="first.json")
        second = self.source(ui(), name="second.json")
        workflow["aliases"].extend(second["aliases"])
        Path(workflow["aliases"][0]["absolute"]).write_text("{}")
        row = preflight.preflight(workflow, SCHEMAS)
        self.assertEqual(row["outcome"], "static_checks_passed")
        self.assertEqual([alias["outcome"] for alias in row["aliases"]], ["stale_source", "fresh"])

    def test_current_schema_static_errors(self):
        cases = [(ui("Missing"), "missing node type Missing"),
                 (ui(model="missing.safetensors"), "unavailable choice"),
                 (api(), "missing required input"),
                 (api({"model": ["99", 0]}), "missing source node 99")]
        for graph, message in cases:
            with self.subTest(message=message):
                row = preflight.preflight(self.source(graph), SCHEMAS)
                self.assertEqual(row["outcome"], "static_errors")
                self.assertTrue(any(message in issue for issue in row["issues"]))
        row = preflight.preflight(self.source(ui()), {})
        self.assertEqual(row["outcome"], "static_errors")

    def test_virtual_nodes_preserve_links_and_real_errors(self):
        graph = {"nodes": [{"id": 1, "type": "SetNode"}, {"id": 2, "type": "GetNode"}],
                 "links": [[1, 1, 0, 2, 0, "*"]]}
        row = preflight.preflight(self.source(graph), {})
        self.assertEqual(row["outcome"], "static_checks_passed")
        self.assertEqual(row["virtual_node_types"], ["GetNode", "SetNode"])
        self.assertEqual(row["frontend_validation"], "pending")
        self.assertEqual(row["issues"], [])
        graph["links"].append([2, 99, 0, 2, 0, "*"])
        row = preflight.preflight(self.source(graph), {})
        self.assertEqual(row["outcome"], "static_errors")
        self.assertIn("Link 2: missing endpoint", row["issues"])
        self.assertNotIn("SetNode", SCHEMAS)

    def test_subgraph_virtual_nodes_and_correspondence_uncertainty(self):
        graph = {"nodes": [{"id": 1, "type": "nested"}], "links": [],
                 "definitions": {"subgraphs": [{"id": "nested", **ui("GetNode")}]}}
        row = preflight.preflight(self.source(graph), {})
        self.assertEqual(row["outcome"], "static_checks_passed")
        self.assertTrue(any("Subgraph ports" in note for note in row["uncertainties"]))
        self.assertEqual(row["frontend_validation"], "pending")

    def test_checker_unsupported_schema_unavailable_and_no_alias(self):
        workflow = self.source(ui())
        with patch.object(preflight.workflow_health, "check_workflow", side_effect=TypeError("unsupported layout")):
            row = preflight.preflight(workflow, SCHEMAS)
        self.assertEqual(row["outcome"], "checker_unsupported")
        self.assertEqual(row["checker_error"], "TypeError: unsupported layout")
        self.assertEqual(preflight.preflight(workflow, None)["outcome"], "schema_unavailable")
        workflow["aliases"] = []
        self.assertEqual(preflight.preflight(workflow, SCHEMAS)["outcome"], "source_unavailable")

    def test_main_writes_only_two_reports_and_local_schema_get(self):
        workflow = self.source(ui())
        (self.root / "workflows.json").write_text(json.dumps({"workflows": [workflow]}))
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with patch.object(preflight, "CATALOGUE", self.root), patch.object(catalogue, "local_schemas", return_value=(SCHEMAS, {"status": "available"})) as schemas:
            preflight.main()
        schemas.assert_called_once_with(8188)
        for name, data in before.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        refs = self.root / "references"
        self.assertEqual({p.name for p in refs.iterdir()}, {"static-preflight.json", "static-preflight.csv"})
        report = json.loads((refs / "static-preflight.json").read_text())
        self.assertEqual(report["counts"]["outcomes"], {"static_checks_passed": 1})
        with (refs / "static-preflight.csv").open() as stream:
            self.assertEqual(list(csv.DictReader(stream))[0]["runtime"], "not_run")


if __name__ == "__main__":
    unittest.main()

import copy
import json
from pathlib import Path
import tempfile
import unittest

from workflow_health import build_report, check_workflow, fingerprint, runtime_receipts, widget_values


SCHEMAS = {
    "CLIPLoader": {"input": {"required": {"clip_name": [["qwen.safetensors"]], "type": [["lumina2"]]}, "optional": {"device": [["default", "cpu"]]}}},
    "Sampler": {"input": {"required": {"seed": ["INT", {"control_after_generate": True}], "sampler": [["euler"]]}}},
    "SaveImage": {"output_node": True, "input": {} },
}


def workflow():
    return {"nodes": [{"id": 1, "type": "CLIPLoader", "widgets_values": ["qwen.safetensors", "lumina2", "cpu"]}, {"id": 9, "type": "SaveImage", "widgets_values": []}], "links": []}


def history(doc, success=True):
    prompt = {str(n["id"]): {"class_type": n["type"], "inputs": widget_values(n, SCHEMAS[n["type"]])} for n in doc["nodes"]}
    return {"p1": {"prompt": [0, "p1", prompt, {"extra_pnginfo": {"workflow": doc}}, ["9"]],
                   "status": {"completed": success, "status_str": "success" if success else "error",
                              "messages": [["execution_success", {"timestamp": 123}]] if success else [["execution_error", {"timestamp": 123, "exception_message": "VRAM grow failed"}]]},
                   "outputs": {}}}


class WorkflowHealthTests(unittest.TestCase):
    def test_named_widgets_are_not_mutated_by_callers(self):
        node = {"widgets_values_named": {"device": "cpu"}}
        values = widget_values(node, SCHEMAS["CLIPLoader"])
        values["device"] = "default"
        self.assertEqual(node["widgets_values_named"]["device"], "cpu")

    def test_linked_named_values_do_not_override_graph_links(self):
        a = workflow()
        a["nodes"][0]["inputs"] = [{"name": "clip", "link": 1}]
        b = copy.deepcopy(a)
        b["nodes"][0]["widgets_values_named"] = {"clip": ["2", 0]}
        self.assertEqual(fingerprint(a), fingerprint(b))

    def test_native_widgets(self):
        node = {"widgets_values": [42, "fixed", "euler"]}
        self.assertEqual(widget_values(node, SCHEMAS["Sampler"]), {"seed": 42, "sampler": "euler"})

    def test_missing_choice_and_node(self):
        doc = workflow()
        doc["nodes"][0]["widgets_values"][0] = "missing.safetensors"
        self.assertIn("unavailable choice", check_workflow(doc, SCHEMAS)[0][0])
        doc["nodes"][0]["type"] = "Absent"
        self.assertIn("missing node type", check_workflow(doc, SCHEMAS)[0][0])

    def test_subgraphs_are_not_missing_node_classes(self):
        doc = {"nodes": [{"id": 2, "type": "inner"}], "links": [],
               "definitions": {"subgraphs": [dict(workflow(), id="inner")]}}
        self.assertEqual(check_workflow(doc, SCHEMAS)[0], [])
        doc["definitions"]["subgraphs"][0]["nodes"][0]["type"] = "Absent"
        self.assertIn("missing node type", check_workflow(doc, SCHEMAS)[0][0])

    def test_fingerprint_ignores_layout_but_not_execution(self):
        original = workflow()
        changed = copy.deepcopy(original)
        changed["nodes"][0]["pos"] = [100, 200]
        self.assertEqual(fingerprint(original), fingerprint(changed))
        changed["nodes"][0]["widgets_values"][-1] = "default"
        self.assertNotEqual(fingerprint(original), fingerprint(changed))
        changed = copy.deepcopy(original)
        changed["nodes"][0]["properties"] = {"behavior": "different"}
        self.assertNotEqual(fingerprint(original), fingerprint(changed))

    def test_runtime_evidence_is_exact_and_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflow.json"
            path.write_text(json.dumps(workflow()))
            first = build_report([path], SCHEMAS, history(workflow()))
            self.assertEqual(first["workflows"][0]["runtime"], "success")
            retained = build_report([path], SCHEMAS, {}, first)
            self.assertEqual(retained["workflows"][0]["runtime"], "success")
            changed = workflow()
            changed["nodes"][0]["widgets_values"][-1] = "default"
            path.write_text(json.dumps(changed))
            self.assertEqual(build_report([path], SCHEMAS, {}, first)["workflows"][0]["runtime"], "unverified")

    def test_error_is_not_success(self):
        receipt = runtime_receipts(history(workflow(), False), SCHEMAS)[0]
        self.assertEqual(receipt["result"], "error")
        self.assertNotIn("exception_message", receipt["error"])

    def test_preflight_does_not_imply_runtime_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflow.json"
            path.write_text(json.dumps(workflow()))
            row = build_report([path], SCHEMAS, {})["workflows"][0]
            self.assertEqual(row["static"], "preflight_pass")
            self.assertEqual(row["runtime"], "unverified")

    def test_unexecuted_ui_metadata_is_not_runtime_proof(self):
        data = history(workflow())
        metadata = data["p1"]["prompt"][3]["extra_pnginfo"]["workflow"]
        metadata["nodes"].append({"id": 10, "type": "SaveImage"})
        receipt = runtime_receipts(data, SCHEMAS)[0]
        self.assertNotIn(fingerprint(metadata), receipt["fingerprints"])
        self.assertEqual(receipt["metadata_fingerprint"], fingerprint(metadata))

    def test_partial_execution_is_not_full_success(self):
        data = history(workflow())
        data["p1"]["prompt"][2]["10"] = {"class_type": "SaveImage", "inputs": {}}
        self.assertEqual(runtime_receipts(data, SCHEMAS)[0]["result"], "partial_success")

    def test_named_inputs_change_fingerprint(self):
        original = workflow()
        changed = copy.deepcopy(original)
        changed["nodes"][0]["widgets_values_named"] = {"clip_name": "different"}
        self.assertNotEqual(fingerprint(original), fingerprint(changed))

    def test_missing_required_api_input(self):
        doc = {"1": {"class_type": "CLIPLoader", "inputs": {}}}
        self.assertIn("missing required input", check_workflow(doc, SCHEMAS)[0][0])

    def test_bad_internal_subgraph_link(self):
        inner = dict(workflow(), id="inner", links=[{"id": 5, "origin_id": 1, "target_id": 999}])
        doc = {"nodes": [], "definitions": {"subgraphs": [inner]}}
        self.assertIn("missing endpoint", check_workflow(doc, SCHEMAS)[0][0])

    def test_explicit_node_error_overrides_execution_success(self):
        data = history(workflow())
        data["p1"]["outputs"] = {"1": {"error": ["secret provider error"]}}
        receipt = runtime_receipts(data, SCHEMAS)[0]
        self.assertEqual(receipt["result"], "error")
        self.assertNotIn("secret provider error", json.dumps(receipt))

    def test_dynamic_combo_does_not_shift_later_widgets(self):
        schema = {"input": {"required": {
            "model": ["COMFY_DYNAMICCOMBO_V3", {"options": [{"key": "small", "inputs": {"required": {"tokens": ["INT", {}]}}}]}],
            "seed": ["INT", {"control_after_generate": True}],
            "system": ["STRING", {}],
        }}}
        node = {"widgets_values": ["small", 32, 42, "fixed", "brief"]}
        self.assertEqual(widget_values(node, schema), {"model": "small", "model.tokens": 32, "seed": 42, "system": "brief"})

    def test_dynamic_choices_are_validated_in_all_graph_forms(self):
        schema = {"input": {"required": {"model": ["COMFY_DYNAMICCOMBO_V3", {"options": [
            {"key": "small", "inputs": {"required": {"weights": [["present.safetensors"]]}}}
        ]}]}}}
        for selected, weights in [("removed", "present.safetensors"), ("small", "missing.safetensors")]:
            values = {"model": selected, "model.weights": weights}
            cases = [
                {"1": {"class_type": "Dynamic", "inputs": values}},
                {"nodes": [{"id": 1, "type": "Dynamic", "widgets_values": [selected, weights]}]},
                {"nodes": [{"id": 1, "type": "Dynamic", "widgets_values_named": values}]},
            ]
            for doc in cases:
                with self.subTest(doc=doc):
                    self.assertTrue(check_workflow(doc, {"Dynamic": schema})[0])

    def test_nested_subgraph_uses_root_registry(self):
        inner = {"id": "inner", "nodes": [{"id": 3, "type": "other"}]}
        other = dict(workflow(), id="other")
        doc = {"nodes": [{"id": 9, "type": "inner"}], "definitions": {"subgraphs": [inner, other]}}
        self.assertEqual(check_workflow(doc, SCHEMAS)[0], [])

    def test_malformed_history_does_not_hide_valid_workflows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "workflow.json"
            path.write_text(json.dumps(workflow()))
            data = history(workflow())
            data["broken"] = copy.deepcopy(data["p1"])
            data["broken"]["prompt"][3]["extra_pnginfo"]["workflow"] = {"nodes": None}
            report = build_report([path], SCHEMAS, data)
            self.assertEqual(report["workflows"][0]["runtime"], "success")
            self.assertEqual(len(report["evidence_issues"]), 1)

    def test_malformed_structures_are_reported_per_file(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / f"{i}.json" for i in range(2)]
            paths[0].write_text("[]")
            paths[1].write_text(json.dumps(dict(workflow(), links=[[1]])))
            report = build_report(paths, SCHEMAS, {})
            self.assertEqual([r["static"] for r in report["workflows"]], ["failed", "failed"])

    def test_invalid_json_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflow.json"
            path.write_text("{")
            self.assertEqual(build_report([path], SCHEMAS, {})["workflows"][0]["static"], "failed")

    def test_pixel_space_is_not_z_image_vae(self):
        doc = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": ["z_image_turbo_bf16.safetensors"]},
                         {"id": 2, "type": "VAELoader", "widgets_values": ["pixel_space"]}], "links": []}
        schemas = {kind: {"input": {}} for kind in ("UNETLoader", "VAELoader")}
        self.assertIn("not a Z-Image latent decoder", check_workflow(doc, schemas)[0][0])


if __name__ == "__main__":
    unittest.main()

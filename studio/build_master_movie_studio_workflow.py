#!/usr/bin/env python3
"""Build The Message · Master Movie Studio workflow (UI JSON + subgraphs).

Read-only against ComfyUI except for writing the workflow file and library
presets already created separately. Never queues GPU work.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from master_studio_package import live_resolver_code, resolve_shot_package

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "user/default/workflows/06 - Learning Production/The Message - Master Movie Studio.json"
SCHEMAS = json.loads(urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=20).read().decode())


def build_std_node(nid, class_type, pos, size, widgets_dict=None, title=None, mode=0, color=None, bgcolor=None, extra_props=None, collapsed=False):
    schema = SCHEMAS[class_type]
    widgets_dict = dict(widgets_dict or {})
    inputs = []
    widgets_values = []
    widgets_named = {}
    for section in ("required", "optional"):
        for name, spec in (schema.get("input", {}).get(section) or {}).items():
            kind = spec[0]
            opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            if opts.get("socketless"):
                if name in widgets_dict or "default" in opts:
                    val = widgets_dict.get(name, opts.get("default"))
                    widgets_values.append(val)
                    widgets_named[name] = val
                continue
            force_input = bool(opts.get("forceInput"))
            is_widget = (not force_input) and (isinstance(kind, list) or kind in ("INT", "FLOAT", "STRING", "BOOLEAN", "COMBO", "COMFY_DYNAMICCOMBO_V3"))
            slot_type = "COMBO" if isinstance(kind, list) else kind
            slot = {"name": name, "type": slot_type, "link": None}
            if section == "optional":
                slot["shape"] = 7
            if is_widget:
                slot["widget"] = {"name": name}
                if isinstance(kind, list) and kind:
                    default_val = widgets_dict.get(name, opts.get("default", kind[0]))
                else:
                    default_val = widgets_dict.get(name, opts.get("default", "" if kind == "STRING" else 0))
                widgets_values.append(default_val)
                widgets_named[name] = default_val
                if opts.get("control_after_generate") is not None or (class_type == "RandomNoise" and name == "noise_seed") or (class_type == "PrimitiveInt" and name == "value"):
                    cag = widgets_dict.get("control_after_generate", "fixed")
                    widgets_values.append(cag)
                    widgets_named["control_after_generate"] = cag
            inputs.append(slot)
    outputs = []
    for out_name, out_type in zip(schema.get("output_name") or schema.get("output") or [], schema.get("output") or []):
        outputs.append({"name": out_name, "type": out_type, "links": []})
    node = {
        "id": nid,
        "type": class_type,
        "pos": list(pos),
        "size": list(size),
        "flags": {"collapsed": True} if collapsed else {},
        "order": nid,
        "mode": mode,
        "inputs": inputs,
        "outputs": outputs,
        "properties": {"Node name for S&R": class_type, **(extra_props or {})},
        "widgets_values": widgets_values,
        "widgets_values_named": widgets_named,
    }
    if title:
        node["title"] = title
    if color:
        node["color"] = color
    if bgcolor:
        node["bgcolor"] = bgcolor
    return node


def input_slot_idx(node, name):
    for idx, inp in enumerate(node["inputs"]):
        if inp["name"] == name:
            return idx
    raise KeyError(f"{node['type']} missing input {name!r}: {[i['name'] for i in node['inputs']]}")


def connect(links, nodes_map, lid, src_id, src_slot, dst_id, dst_slot, ltype):
    links.append({"id": lid, "origin_id": src_id, "origin_slot": src_slot, "target_id": dst_id, "target_slot": dst_slot, "type": ltype})
    if src_id in nodes_map and src_slot is not None and src_slot >= 0:
        nodes_map[src_id]["outputs"][src_slot]["links"].append(lid)
    if dst_id in nodes_map:
        nodes_map[dst_id]["inputs"][dst_slot]["link"] = lid


def build_subgraph_instance(nid, sg_def, pos, size, title, mode=0, proxy_widgets=None):
    inputs = [{"name": i["name"], "localized_name": i["name"], "label": i.get("label", i["name"]), "type": i["type"], "link": None} for i in sg_def["inputs"]]
    outputs = [{"name": o["name"], "localized_name": o["name"], "label": o.get("label", o["name"]), "type": o["type"], "links": []} for o in sg_def["outputs"]]
    return {
        "id": nid,
        "type": sg_def["id"],
        "pos": list(pos),
        "size": list(size),
        "flags": {},
        "order": nid,
        "mode": mode,
        "inputs": inputs,
        "outputs": outputs,
        "title": title,
        "properties": {"proxyWidgets": proxy_widgets or []},
        "widgets_values": [],
    }


def make_subgraph(sg_id, name, category, description, nodes, links, inputs, outputs, last_link_id):
    return {
        "id": sg_id,
        "version": 1,
        "state": {"lastGroupId": 0, "lastNodeId": max(n["id"] for n in nodes), "lastLinkId": last_link_id, "lastRerouteId": 0},
        "revision": 0,
        "config": {},
        "name": name,
        "inputNode": {"id": -10, "bounding": [-80, 80, 150, max(70, 20 * len(inputs) + 40)]},
        "outputNode": {"id": -20, "bounding": [max(n["pos"][0] for n in nodes) + 420, 100, 150, max(70, 20 * len(outputs) + 40)]},
        "inputs": inputs,
        "outputs": outputs,
        "widgets": [],
        "nodes": nodes,
        "groups": [],
        "links": links,
        "extra": {"workflowRendererVersion": "LG"},
        "category": category,
        "description": description,
    }


# ---------------------------------------------------------------------------
# Subgraph 1 — Model / LoRA / Shift
# ---------------------------------------------------------------------------
SG_MODEL = "b101b101-48ea-408e-9024-b30000000001"
sg1_nodes = [
    build_std_node(1, "UNETLoader", [120, 40], [360, 90], {"unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}, title="H3 Ref2VA Diffusion (INT8 ConvRot)"),
    build_std_node(2, "CLIPLoader", [120, 170], [360, 120], {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}, title="Qwen3-VL 32B H3 TE (NVFP4)"),
    build_std_node(3, "VAELoader", [120, 340], [360, 80], {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}, title="H3 Video VAE"),
    build_std_node(4, "VAELoader", [120, 460], [360, 80], {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}, title="H3 Audio VAE"),
    build_std_node(5, "FantasticLoraLoaderMulti", [540, 60], [440, 260], {"lora_data": json.dumps({"loras": [{"on": False, "name": "h3_character_swap_v1.5.safetensors", "strength": 1.0}, {"on": False, "name": "minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors", "strength": 1.0}], "enabledFolders": None})}, title="Fantastic Lora Loader 📁"),
    build_std_node(6, "FantasticLoraMimicSubgraphCompanion", [540, 360], [360, 90], {"lora_data": "{}"}, title="Subgraph LoRA Stack Bridge 🧩"),
    build_std_node(7, "MiniMaxH3SigmaShift", [1040, 80], [300, 110], {"shift_video": 12.0, "shift_audio": 3.0}, title="H3 Flow Shifts"),
]
sg1_map = {n["id"]: n for n in sg1_nodes}
sg1_links = []
connect(sg1_links, sg1_map, 1, -10, 0, 7, input_slot_idx(sg1_map[7], "shift_video"), "FLOAT")
connect(sg1_links, sg1_map, 2, -10, 1, 7, input_slot_idx(sg1_map[7], "shift_audio"), "FLOAT")
connect(sg1_links, sg1_map, 3, 1, 0, 5, input_slot_idx(sg1_map[5], "model"), "MODEL")
connect(sg1_links, sg1_map, 4, 2, 0, 5, input_slot_idx(sg1_map[5], "clip"), "CLIP")
connect(sg1_links, sg1_map, 5, 5, 0, 7, input_slot_idx(sg1_map[7], "model"), "MODEL")
connect(sg1_links, sg1_map, 6, 5, 2, 6, input_slot_idx(sg1_map[6], "lora_stack"), "LORA_STACK")
connect(sg1_links, sg1_map, 7, 7, 0, -20, 0, "MODEL")
connect(sg1_links, sg1_map, 8, 5, 1, -20, 1, "CLIP")
connect(sg1_links, sg1_map, 9, 3, 0, -20, 2, "VAE")
connect(sg1_links, sg1_map, 10, 4, 0, -20, 3, "VAE")
connect(sg1_links, sg1_map, 11, 6, 0, -20, 4, "LORA_STACK")
subgraph_1 = make_subgraph(
    SG_MODEL,
    "H3 Model, LoRA & Shift Rig (6 GB DynamicVRAM)",
    "The Message Studio/Models",
    "Loads quantized H3 Ref2VA, Qwen3-VL NVFP4, Video/Audio VAEs, Fantastic Lora Loader, and Subgraph LoRA Companion.",
    list(sg1_map.values()),
    sg1_links,
    [
        {"id": "11111111-1111-4111-8111-000000000001", "name": "shift_video", "label": "shift_video", "type": "FLOAT", "linkIds": [1], "pos": [60, 145]},
        {"id": "11111111-1111-4111-8111-000000000002", "name": "shift_audio", "label": "shift_audio", "type": "FLOAT", "linkIds": [2], "pos": [60, 165]},
    ],
    [
        {"id": "11111111-1111-4111-8111-000000000011", "name": "model", "label": "MODEL", "type": "MODEL", "linkIds": [7], "pos": [1480, 145]},
        {"id": "11111111-1111-4111-8111-000000000012", "name": "clip", "label": "CLIP", "type": "CLIP", "linkIds": [8], "pos": [1480, 165]},
        {"id": "11111111-1111-4111-8111-000000000013", "name": "video_vae", "label": "video_vae", "type": "VAE", "linkIds": [9], "pos": [1480, 185]},
        {"id": "11111111-1111-4111-8111-000000000014", "name": "audio_vae", "label": "audio_vae", "type": "VAE", "linkIds": [10], "pos": [1480, 205]},
        {"id": "11111111-1111-4111-8111-000000000015", "name": "lora_stack", "label": "lora_stack", "type": "LORA_STACK", "linkIds": [11], "pos": [1480, 225]},
    ],
    11,
)

# ---------------------------------------------------------------------------
# Subgraph 2 — Conditioning + H3 Context
# ---------------------------------------------------------------------------
SG_COND = "b202b202-48ea-408e-9024-b30000000002"
sg2_nodes = [
    build_std_node(1, "MiniMaxH3FantasticRefModTextEncode", [160, 40], [360, 430], {
        "prompt": "", "width": 832, "height": 480, "length": 73, "ref_image_size": "match",
        "reference_fps": 24.0, "max_total_tokens": 0, "voice_description_at_label": False,
        "stack_pictures": "up to N", "stack_pictures_n": 4,
    }, title="Fantastic H3 RefMod Text Encode"),
    build_std_node(2, "H3Context", [580, 40], [360, 400], {
        "context_length": 22, "encode_mode": "video", "anchor_mode": "head", "crop": "disabled",
        "audio_context_length": 22, "audio_mode": "timeline", "video_source": "latent",
        "seed_head": True, "head_hold": 1.0, "hold_framing": False,
    }, title="H3 Context (latent tail + seed_head)"),
    build_std_node(3, "H3StageSave", [580, 500], [340, 110], {"name": "h3_stages/the_message_shot_stage"}, title="H3 Stage Save (muted)", mode=2),
]
sg2_map = {n["id"]: n for n in sg2_nodes}
sg2_links = []
connect(sg2_links, sg2_map, 1, -10, 0, 1, input_slot_idx(sg2_map[1], "clip"), "CLIP")
connect(sg2_links, sg2_map, 2, -10, 1, 1, input_slot_idx(sg2_map[1], "vae"), "VAE")
connect(sg2_links, sg2_map, 3, -10, 2, 1, input_slot_idx(sg2_map[1], "mods"), "H3_REF_MODS")
connect(sg2_links, sg2_map, 4, -10, 3, 1, input_slot_idx(sg2_map[1], "references"), "H3_REFS")
connect(sg2_links, sg2_map, 5, -10, 4, 1, input_slot_idx(sg2_map[1], "prompt"), "STRING")
connect(sg2_links, sg2_map, 6, -10, 5, 1, input_slot_idx(sg2_map[1], "width"), "INT")
connect(sg2_links, sg2_map, 7, -10, 6, 1, input_slot_idx(sg2_map[1], "height"), "INT")
connect(sg2_links, sg2_map, 8, -10, 7, 1, input_slot_idx(sg2_map[1], "length"), "INT")
connect(sg2_links, sg2_map, 9, -10, 8, 2, input_slot_idx(sg2_map[2], "enabled"), "BOOLEAN")
connect(sg2_links, sg2_map, 10, -10, 9, 2, input_slot_idx(sg2_map[2], "context_latent"), "LATENT")
connect(sg2_links, sg2_map, 11, 1, 0, 2, input_slot_idx(sg2_map[2], "conditioning"), "CONDITIONING")
connect(sg2_links, sg2_map, 12, 1, 2, 2, input_slot_idx(sg2_map[2], "latent"), "LATENT")
connect(sg2_links, sg2_map, 13, 2, 0, 3, input_slot_idx(sg2_map[3], "conditioning"), "CONDITIONING")
connect(sg2_links, sg2_map, 14, 2, 2, 3, input_slot_idx(sg2_map[3], "latent"), "LATENT")
connect(sg2_links, sg2_map, 15, 2, 0, -20, 0, "CONDITIONING")
connect(sg2_links, sg2_map, 16, 2, 2, -20, 1, "LATENT")
connect(sg2_links, sg2_map, 17, 2, 1, -20, 2, "INT")
connect(sg2_links, sg2_map, 18, 1, 1, -20, 3, "STRING")
subgraph_2 = make_subgraph(
    SG_COND,
    "H3 Conditioning & Motion Context",
    "The Message Studio/Conditioning",
    "Encodes structured prompt + RefMods + media, then applies H3 Project Suite latent continuation when chain_active is true.",
    list(sg2_map.values()),
    sg2_links,
    [
        {"id": "22222222-2222-4222-8222-000000000001", "name": "clip", "label": "clip", "type": "CLIP", "linkIds": [1], "pos": [60, 100]},
        {"id": "22222222-2222-4222-8222-000000000002", "name": "video_vae", "label": "video_vae", "type": "VAE", "linkIds": [2], "pos": [60, 120]},
        {"id": "22222222-2222-4222-8222-000000000003", "name": "mods", "label": "mods", "type": "H3_REF_MODS", "linkIds": [3], "pos": [60, 140]},
        {"id": "22222222-2222-4222-8222-000000000004", "name": "references", "label": "references", "type": "H3_REFS", "linkIds": [4], "pos": [60, 160]},
        {"id": "22222222-2222-4222-8222-000000000005", "name": "prompt", "label": "prompt", "type": "STRING", "linkIds": [5], "pos": [60, 180]},
        {"id": "22222222-2222-4222-8222-000000000006", "name": "width", "label": "width", "type": "INT", "linkIds": [6], "pos": [60, 200]},
        {"id": "22222222-2222-4222-8222-000000000007", "name": "height", "label": "height", "type": "INT", "linkIds": [7], "pos": [60, 220]},
        {"id": "22222222-2222-4222-8222-000000000008", "name": "length", "label": "length", "type": "INT", "linkIds": [8], "pos": [60, 240]},
        {"id": "22222222-2222-4222-8222-000000000009", "name": "chain_active", "label": "chain_active", "type": "BOOLEAN", "linkIds": [9], "pos": [60, 260]},
        {"id": "22222222-2222-4222-8222-000000000010", "name": "context_latent", "label": "context_latent", "type": "LATENT", "linkIds": [10], "pos": [60, 280]},
    ],
    [
        {"id": "22222222-2222-4222-8222-000000000021", "name": "conditioning", "label": "conditioning", "type": "CONDITIONING", "linkIds": [15], "pos": [1040, 145]},
        {"id": "22222222-2222-4222-8222-000000000022", "name": "latent", "label": "seeded_latent", "type": "LATENT", "linkIds": [16], "pos": [1040, 165]},
        {"id": "22222222-2222-4222-8222-000000000023", "name": "trim_frames", "label": "trim_frames", "type": "INT", "linkIds": [17], "pos": [1040, 185]},
        {"id": "22222222-2222-4222-8222-000000000024", "name": "reference_map", "label": "encoder_ref_map", "type": "STRING", "linkIds": [18], "pos": [1040, 205]},
    ],
    18,
)

# ---------------------------------------------------------------------------
# Subgraph 3 — Sampler / Decode / Trim
# ---------------------------------------------------------------------------
SG_SAMP = "b303b303-48ea-408e-9024-b30000000003"
sg3_nodes = [
    build_std_node(1, "BasicGuider", [140, 40], [280, 90], {}, title="Basic Guider"),
    build_std_node(2, "KSamplerSelect", [140, 160], [280, 80], {"sampler_name": "sa_solver"}, title="Sampler Select (sa_solver)"),
    build_std_node(3, "BasicScheduler", [140, 270], [280, 130], {"scheduler": "beta", "steps": 20, "denoise": 1.0}, title="Basic Scheduler (beta)"),
    build_std_node(4, "RandomNoise", [140, 430], [280, 110], {"noise_seed": 11005, "control_after_generate": "fixed"}, title="Shot Noise Seed"),
    build_std_node(5, "SamplerCustomAdvanced", [490, 80], [320, 210], {}, title="Sample H3 AV Latent"),
    build_std_node(6, "VAEDecode", [870, 80], [270, 100], {}, title="Decode Video Frames"),
    build_std_node(7, "VAEDecodeAudio", [870, 220], [270, 100], {}, title="Decode Audio (muted · unmute for AV)", mode=2),
    build_std_node(8, "H3ContextTrim", [1200, 80], [290, 140], {"trim_frames": 0, "fps": 24.0, "match_tail": True}, title="H3 Context Trim"),
]
sg3_map = {n["id"]: n for n in sg3_nodes}
sg3_links = []
connect(sg3_links, sg3_map, 1, -10, 0, 1, input_slot_idx(sg3_map[1], "model"), "MODEL")
connect(sg3_links, sg3_map, 2, -10, 0, 3, input_slot_idx(sg3_map[3], "model"), "MODEL")
connect(sg3_links, sg3_map, 3, -10, 1, 1, input_slot_idx(sg3_map[1], "conditioning"), "CONDITIONING")
connect(sg3_links, sg3_map, 4, -10, 2, 5, input_slot_idx(sg3_map[5], "latent_image"), "LATENT")
connect(sg3_links, sg3_map, 5, -10, 3, 6, input_slot_idx(sg3_map[6], "vae"), "VAE")
connect(sg3_links, sg3_map, 6, -10, 4, 4, input_slot_idx(sg3_map[4], "noise_seed"), "INT")
connect(sg3_links, sg3_map, 7, -10, 5, 3, input_slot_idx(sg3_map[3], "steps"), "INT")
connect(sg3_links, sg3_map, 8, -10, 6, 8, input_slot_idx(sg3_map[8], "trim_frames"), "INT")
connect(sg3_links, sg3_map, 9, -10, 7, 8, input_slot_idx(sg3_map[8], "fps"), "FLOAT")
connect(sg3_links, sg3_map, 10, 4, 0, 5, input_slot_idx(sg3_map[5], "noise"), "NOISE")
connect(sg3_links, sg3_map, 11, 1, 0, 5, input_slot_idx(sg3_map[5], "guider"), "GUIDER")
connect(sg3_links, sg3_map, 12, 2, 0, 5, input_slot_idx(sg3_map[5], "sampler"), "SAMPLER")
connect(sg3_links, sg3_map, 13, 3, 0, 5, input_slot_idx(sg3_map[5], "sigmas"), "SIGMAS")
connect(sg3_links, sg3_map, 14, 5, 0, 6, input_slot_idx(sg3_map[6], "samples"), "LATENT")
connect(sg3_links, sg3_map, 15, 6, 0, 8, input_slot_idx(sg3_map[8], "images"), "IMAGE")
connect(sg3_links, sg3_map, 16, 5, 0, -20, 0, "LATENT")
connect(sg3_links, sg3_map, 17, 8, 0, -20, 1, "IMAGE")
subgraph_3 = make_subgraph(
    SG_SAMP,
    "H3 Sampler, Decode & Context Trim (6 GB Optimized)",
    "The Message Studio/Sampling",
    "Samples with sa_solver/beta, decodes video without EditComposite RAM pin, trims overlap frames.",
    list(sg3_map.values()),
    sg3_links,
    [
        {"id": "33333333-3333-4333-8333-000000000001", "name": "model", "label": "model", "type": "MODEL", "linkIds": [1, 2], "pos": [60, 100]},
        {"id": "33333333-3333-4333-8333-000000000002", "name": "conditioning", "label": "conditioning", "type": "CONDITIONING", "linkIds": [3], "pos": [60, 120]},
        {"id": "33333333-3333-4333-8333-000000000003", "name": "latent_image", "label": "seeded_latent", "type": "LATENT", "linkIds": [4], "pos": [60, 140]},
        {"id": "33333333-3333-4333-8333-000000000004", "name": "video_vae", "label": "video_vae", "type": "VAE", "linkIds": [5], "pos": [60, 160]},
        {"id": "33333333-3333-4333-8333-000000000005", "name": "noise_seed", "label": "seed", "type": "INT", "linkIds": [6], "pos": [60, 180]},
        {"id": "33333333-3333-4333-8333-000000000006", "name": "steps", "label": "steps", "type": "INT", "linkIds": [7], "pos": [60, 200]},
        {"id": "33333333-3333-4333-8333-000000000007", "name": "trim_frames", "label": "trim_frames", "type": "INT", "linkIds": [8], "pos": [60, 220]},
        {"id": "33333333-3333-4333-8333-000000000008", "name": "fps", "label": "fps", "type": "FLOAT", "linkIds": [9], "pos": [60, 240]},
    ],
    [
        {"id": "33333333-3333-4333-8333-000000000021", "name": "sampled_latent", "label": "untrimmed_av_latent", "type": "LATENT", "linkIds": [16], "pos": [1570, 125]},
        {"id": "33333333-3333-4333-8333-000000000022", "name": "trimmed_images", "label": "trimmed_images", "type": "IMAGE", "linkIds": [17], "pos": [1570, 145]},
    ],
    17,
)

# ---------------------------------------------------------------------------
# Subgraph 4 — LoRA XY Lab (muted)
# ---------------------------------------------------------------------------
SG_PLOT = "b404b404-48ea-408e-9024-b30000000004"
sg4_nodes = [
    build_std_node(1, "FantasticPlotterGlobalLora", [100, 60], [380, 180], {"lora_data": "{}"}, title="Global Constant LoRAs 🌐"),
    build_std_node(2, "FantasticLoraPlotter", [540, 60], [420, 260], {"lora_data": "{}"}, title="Fantastic Lora Plotter 📊"),
    build_std_node(3, "FantasticPlotterImageSaver", [1020, 60], [340, 290], {
        "constrain_size": True, "max_cell_size": 512, "text_color": "white", "background_color": "black",
        "font_size": 20, "padding": 8, "opacity": 0.85, "images_per_row": 3,
        "single_strength_layout": "row", "classic_grid": False,
    }, title="Fantastic Plotter Image Saver 📊"),
    build_std_node(4, "FantasticPlotterGridViewer", [1020, 390], [340, 180], {}, title="Fantastic Plotter Grid Viewer 🔍"),
]
sg4_map = {n["id"]: n for n in sg4_nodes}
sg4_links = []
connect(sg4_links, sg4_map, 1, -10, 0, 2, input_slot_idx(sg4_map[2], "model"), "MODEL")
connect(sg4_links, sg4_map, 2, -10, 1, 2, input_slot_idx(sg4_map[2], "clip"), "CLIP")
connect(sg4_links, sg4_map, 3, -10, 2, 3, input_slot_idx(sg4_map[3], "images"), "IMAGE")
connect(sg4_links, sg4_map, 4, -10, 2, 4, input_slot_idx(sg4_map[4], "images"), "IMAGE")
connect(sg4_links, sg4_map, 5, 1, 0, 2, input_slot_idx(sg4_map[2], "global_loras"), "FL_GLOBAL_LORAS")
connect(sg4_links, sg4_map, 6, 2, 2, 3, input_slot_idx(sg4_map[3], "metadata"), "STRING")
connect(sg4_links, sg4_map, 7, 2, 2, 4, input_slot_idx(sg4_map[4], "metadata"), "STRING")
connect(sg4_links, sg4_map, 8, 2, 0, -20, 0, "MODEL")
connect(sg4_links, sg4_map, 9, 3, 0, -20, 1, "IMAGE")
subgraph_4 = make_subgraph(
    SG_PLOT,
    "Fantastic LoRA XY Test Bench (Lab)",
    "The Message Studio/Labs",
    "Muted XY LoRA sweep bench.",
    list(sg4_map.values()),
    sg4_links,
    [
        {"id": "44444444-4444-4444-8444-000000000001", "name": "model", "label": "base_model", "type": "MODEL", "linkIds": [1], "pos": [40, 100]},
        {"id": "44444444-4444-4444-8444-000000000002", "name": "clip", "label": "base_clip", "type": "CLIP", "linkIds": [2], "pos": [40, 120]},
        {"id": "44444444-4444-4444-8444-000000000003", "name": "images", "label": "decoded_frames", "type": "IMAGE", "linkIds": [3, 4], "pos": [40, 140]},
    ],
    [
        {"id": "44444444-4444-4444-8444-000000000011", "name": "swept_model", "label": "swept_model", "type": "MODEL", "linkIds": [8], "pos": [1450, 120]},
        {"id": "44444444-4444-4444-8444-000000000012", "name": "grid", "label": "xy_grid", "type": "IMAGE", "linkIds": [9], "pos": [1450, 140]},
    ],
    9,
)

# ---------------------------------------------------------------------------
# Subgraph 5 — RefMod / Import / Mask lab (muted)
# ---------------------------------------------------------------------------
SG_PREP = "b505b505-48ea-408e-9024-b30000000005"
sg5_nodes = [
    build_std_node(1, "MiniMaxH3FantasticRefModCreate", [100, 40], [390, 500], {
        "name": "New_Character_or_Set_v1", "subfolder": "The_Message", "mode": "Full Reference",
        "ref_resolution": 768, "grid": 16, "latent_frames": 22, "refinement_steps": 0,
        "max_tokens": 5120, "audio_max_seconds": 30.0, "concept_type": "identity",
        "description": "Encode-only RefMod candidate (refinement_steps=0).", "write_preview": True, "source": "[]",
    }, title="Create RefMod (Encode-Only · 768px)"),
    build_std_node(2, "MiniMaxH3FantasticRefModInspect", [540, 40], [330, 210], {
        "file": "refmod_-Andre_Athar-video_visual", "view": "video", "strength": 1.0, "audio_seconds": 30.0,
    }, title="Inspect Saved RefMod"),
    build_std_node(3, "MiniMaxH3FantasticRefModEdit", [540, 290], [330, 250], {
        "file": "refmod_-Andre_Athar-video_visual", "frames": "", "add": "[]", "voice": "keep",
        "latent_frames": 22, "audio_max_seconds": 30.0, "save_as": "refmod_-Andre_Athar-video_copy",
    }, title="Edit RefMod as Immutable Copy"),
    build_std_node(4, "H3ImportSource", [920, 40], [330, 220], {
        "source_fps": 24.0, "width": 832, "height": 480, "crop": "center", "keep": "tail",
    }, title="H3 Import Source"),
    build_std_node(5, "MiniMaxH3FantasticEditComposite", [920, 300], [330, 160], {"blend": 8, "max_size": 0}, title="Masked Edit Composite"),
]
sg5_map = {n["id"]: n for n in sg5_nodes}
sg5_links = []
connect(sg5_links, sg5_map, 1, -10, 0, 1, input_slot_idx(sg5_map[1], "vae"), "VAE")
connect(sg5_links, sg5_map, 2, -10, 0, 2, input_slot_idx(sg5_map[2], "vae"), "VAE")
connect(sg5_links, sg5_map, 3, -10, 0, 3, input_slot_idx(sg5_map[3], "vae"), "VAE")
connect(sg5_links, sg5_map, 4, -10, 0, 4, input_slot_idx(sg5_map[4], "vae"), "VAE")
connect(sg5_links, sg5_map, 5, -10, 1, 1, input_slot_idx(sg5_map[1], "audio_vae"), "VAE")
connect(sg5_links, sg5_map, 6, -10, 1, 4, input_slot_idx(sg5_map[4], "audio_vae"), "VAE")
connect(sg5_links, sg5_map, 7, 2, 0, -20, 0, "STRING")
subgraph_5 = make_subgraph(
    SG_PREP,
    "RefMod Factory, Import & Mask Edit Lab",
    "The Message Studio/Labs",
    "Muted asset-creation lab: Create/Inspect/Edit RefMod, H3 Import Source, Edit Composite.",
    list(sg5_map.values()),
    sg5_links,
    [
        {"id": "55555555-5555-4555-8555-000000000001", "name": "video_vae", "label": "video_vae", "type": "VAE", "linkIds": [1, 2, 3, 4], "pos": [40, 100]},
        {"id": "55555555-5555-4555-8555-000000000002", "name": "audio_vae", "label": "audio_vae", "type": "VAE", "linkIds": [5, 6], "pos": [40, 120]},
    ],
    [
        {"id": "55555555-5555-4555-8555-000000000011", "name": "inspect_details", "label": "inspect_details", "type": "STRING", "linkIds": [7], "pos": [1330, 100]},
    ],
    7,
)

# ---------------------------------------------------------------------------
# Root graph
# ---------------------------------------------------------------------------
VARS_CODE = """project_name, shot_tag, width, height, duration_s, fps, steps, shift_video, shift_audio, transition, chain_active = inputs
width = max(32, round(int(width) / 32) * 32)
height = max(32, round(int(height) / 32) * 32)
fps_f = float(fps)
req = max(5, round(float(duration_s) * fps_f))
ctx = 22
continuing = str(transition).strip().lower() == "continue" and bool(chain_active)
if continuing:
    raw = int((req + ctx) + (5 - (req + ctx) % 17) % 17)
    trim = ctx
    delivered = raw - trim
else:
    raw = int(req + (5 - req % 17) % 17)
    trim = 0
    delivered = raw
mode = "continue" if continuing else "cut"
summary = (
    f"Project: {project_name} · Shot: {shot_tag} · Transition: {transition} ({mode})\\n"
    f"Canvas: {width}×{height} (16:9 multiple-of-32) · "
    f"raw {raw}f / delivered {delivered}f ({delivered / fps_f:.3f}s @ {fps_f:g} fps)"
    + (f" · trim {trim}" if trim else "")
    + "\\n"
    f"Schedule: {int(steps)} steps · sa_solver / beta · shifts {float(shift_video):g}/{float(shift_audio):g} · CK int8 attention"
)
outputs[:] = [
    str(project_name), str(shot_tag), int(width), int(height), int(raw), int(round(fps_f)),
    int(steps), float(shift_video), float(shift_audio), summary, int(delivered), int(trim), bool(continuing),
]
"""

PKG_CODE = live_resolver_code()

guide = """## The Message · Master Movie Studio (RTX 3060 6 GB)

Lessons from the first 6-shot film, wired as one graph:

1. **Common Variables Bus** — Project Name feeds Hub directly. Shot Tag selects the full shot package (prompt/media/RefMod/seed/transition). Duration preview shows **raw vs delivered** frames.
2. **Transition** — package default is `cut`. `continue` only arms H3 Context when Hub has an approved tail. Frame-grid rounding affects delivery: at 3s/24fps, cut delivers 73f; continue samples 107f, trims 22f and delivers 85f. Read the raw/delivered preview before running.
3. **Structured Prompts** — package resolver drives Media / Prompt Builder / RefMod / Seed. Node `24` lists reference tags on CPU.
4. **Subgraphs** — Model/LoRA `30`, Conditioning/Context `40`, Sampler/Decode/Trim `50`. Labs `70`/`80` stay muted.
5. **H3 Project Suite** — Open project… on Hub (resolved project name). Approve before a continue take.
6. **WorkflowMonitorBrain** — provenance digests for primitives, prompt, and LoRA; records under `user/workflow_monitor`.

Silent video decode by default. Do not unmute Audio Decode until AV trim wiring exists.

For motionless inserts, the optional Static Plate 101→102→103→104 branch holds the first
package Picture at the common delivery size, frame count and FPS. Prefix105 names each
shot under The_Message/master_studio_static_plates. Output104 is muted by default.
For a full static-only queue, mute ProjectSave61 and generative SaveVideo64 first;
restore them and mute104 for generated shots. A plate has no AV continuation latent.
"""

nodes = []
links = []
lid = 1

n1 = {
    "id": 1, "type": "MarkdownNote", "pos": [-1380, -40], "size": [620, 520],
    "flags": {}, "order": 1, "mode": 0, "inputs": [], "outputs": [],
    "color": "#233", "bgcolor": "#355",
    "title": "Master Movie Studio · Common Variables + Subgraphs + Structured Prompts",
    "properties": {},
    "widgets_values": [guide],
    "widgets_values_named": {"text": guide},
}
nodes.append(n1)

# Common variables
n10 = build_std_node(10, "PrimitiveString", [-720, -20], [300, 60], {"value": "The_Message_Act1"}, title="Var · Project Name", color="#223", bgcolor="#335")
n11 = build_std_node(11, "PrimitiveString", [-720, 70], [300, 60], {"value": "MSG_S001_SH05"}, title="Var · Shot Tag", color="#223", bgcolor="#335")
n12 = build_std_node(12, "ResolutionSelector", [-720, 160], [300, 140], {"aspect_ratio": "16:9 (Widescreen)", "megapixels": 0.38, "multiple": 32}, title="Var · Resolution (832×480)", color="#223", bgcolor="#335")
n13 = build_std_node(13, "PrimitiveFloat", [-720, 340], [300, 70], {"value": 3.0}, title="Var · Duration (seconds)", color="#223", bgcolor="#335")
n14 = build_std_node(14, "PrimitiveFloat", [-720, 440], [300, 70], {"value": 24.0}, title="Var · FPS", color="#223", bgcolor="#335")
n15 = build_std_node(15, "PrimitiveInt", [-720, 540], [300, 80], {"value": 20, "control_after_generate": "fixed"}, title="Var · Steps", color="#223", bgcolor="#335")
n16 = build_std_node(16, "FantasticSeeds", [-720, 650], [300, 120], {"seed": 11005, "mode": "fixed", "history": "[]"}, title="Var · Seed 🌱", color="#223", bgcolor="#335")
n17a = build_std_node(17, "PrimitiveFloat", [-720, 800], [300, 70], {"value": 12.0}, title="Var · Shift Video", color="#223", bgcolor="#335")
n17b = build_std_node(19, "PrimitiveFloat", [-720, 900], [300, 70], {"value": 3.0}, title="Var · Shift Audio", color="#223", bgcolor="#335")

def make_dynamic_script(nid, pos, size, title, code, input_count, output_count, color="#1b4669", bgcolor="#29699c", lazy_execution=True):
    node = build_std_node(nid, "DynamicScriptNode", pos, size, {
        "input_ports_count": input_count, "output_ports_count": output_count, "module_count": 0,
        "module_name_prefix": "dynamic_module", "use_module_cache": True,
        "clear_module_cache": False, "remove_import_restrictions": False,
        "lazy_execution": lazy_execution, "code": code,
    }, title=title, color=color, bgcolor=bgcolor)
    node["inputs"] = [{"name": f"input_{i}", "type": "*", "link": None, "shape": 7} for i in range(input_count)]
    node["outputs"] = [{"name": "exception", "type": "*", "links": []}] + [
        {"name": f"output_{i}", "type": "*", "links": []} for i in range(output_count)
    ]
    node["widgets_values"] = [
        input_count, output_count, 0, "dynamic_module", True, False, False, lazy_execution, code,
    ]
    node["widgets_values_named"] = {
        "input_ports_count": input_count, "output_ports_count": output_count, "module_count": 0,
        "module_name_prefix": "dynamic_module", "use_module_cache": True,
        "clear_module_cache": False, "remove_import_restrictions": False,
        "lazy_execution": lazy_execution, "code": code,
    }
    return node


n18 = make_dynamic_script(
    18, [-380, 160], [420, 480],
    "Common Variables Compiler (raw/delivered + Cut/Continue)",
    VARS_CODE, 11, 13,
)
n20 = build_std_node(20, "PreviewAny", [-380, 680], [420, 200], {}, title="Live Production Plan Summary")

# Shot package resolver — Shot Tag selects prompt/media/RefMod/seed/transition together.
sh05 = resolve_shot_package("MSG_S001_SH05")
media_state = json.dumps(sh05["media_state"], separators=(",", ":"))
stack_state = json.dumps(sh05["stack_state"], separators=(",", ":"))
builder_state = json.dumps(sh05["builder_state"], separators=(",", ":"))
prompt_text = sh05["prompt_text"]

n27 = make_dynamic_script(
    27, [80, -220], [360, 280],
    "Shot Package Resolver (tag → prompt/media/RefMod/seed/transition)",
    PKG_CODE, 1, 7, color="#2a4a2a", bgcolor="#3a6a3a", lazy_execution=False,
)
n28 = build_std_node(28, "PreviewAny", [480, -220], [360, 120], {}, title="Resolved Shot Package")

n21 = build_std_node(21, "MiniMaxH3MediaLoader", [80, 100], [360, 220], {"media_state": media_state}, title="Fantastic H3 Media Loader (from package)")
n22 = build_std_node(22, "MiniMaxH3PromptBuilder", [480, 100], [420, 360], {"prompt_text": prompt_text, "builder_state": builder_state}, title="Fantastic H3 Prompt Builder (from package)")
n23 = build_std_node(23, "MiniMaxH3RefModStack", [80, 360], [360, 220], {"stack_state": stack_state}, title="Fantastic H3 RefMod Stack (from package)")
n24 = build_std_node(24, "MiniMaxH3FantasticReferenceMap", [480, 500], [360, 120], {}, title="Fantastic H3 Reference Map (CPU)")
n25 = build_std_node(25, "PreviewAny", [480, 660], [360, 180], {}, title="Reference Map Preview")
# Seed default matches SH05; package resolver overrides via link.
n16["widgets_values"] = [sh05["seed"], "fixed", "[]"]
n16["widgets_values_named"] = {"seed": sh05["seed"], "mode": "fixed", "history": "[]"}

# Subgraph instances
n30 = build_subgraph_instance(30, subgraph_1, [940, -40], [360, 220], "① H3 Model, LoRA & Shift Rig")
n40 = build_subgraph_instance(40, subgraph_2, [940, 240], [380, 300], "② H3 Conditioning & Motion Context")
n50 = build_subgraph_instance(50, subgraph_3, [940, 600], [380, 260], "③ H3 Sampler, Decode & Context Trim")
n70 = build_subgraph_instance(70, subgraph_4, [1380, -40], [340, 180], "Lab · Fantastic LoRA XY Bench", mode=2)
n80 = build_subgraph_instance(80, subgraph_5, [1380, 180], [340, 160], "Lab · RefMod / Import / Mask", mode=2)

# Project suite + save
n60 = build_std_node(60, "H3ProjectHub", [1380, 400], [360, 220], {"project_name": "The_Message_Act1", "create_if_missing": True}, title="H3 Project Hub")
n61 = build_std_node(61, "H3ProjectSave", [1780, 620], [320, 160], {"fps": 24}, title="H3 Project Save")
n62 = build_std_node(62, "MiniMaxH3FilenamePrefix", [1780, 400], [320, 160], {
    "folder": "The_Message", "subfolder": "master_studio", "date_folder": "YYYY-MM-DD", "filename": "take",
}, title="Fantastic H3 Filename Prefix")
n63 = build_std_node(63, "CreateVideo", [1780, 820], [300, 160], {
    "fps": 24.0, "bit_depth": "auto", "color_space": "sRGB", "chroma_subsampling": "auto", "codec": "none",
}, title="CreateVideo (review copy)")
n64 = build_std_node(64, "SaveVideo", [2120, 820], [300, 160], {
    "filename_prefix": "The_Message/master_studio/review", "format": "auto", "codec": "auto",
}, title="SaveVideo (optional review)")
n64["widgets_values"] = ["The_Message/master_studio/review", "auto", "auto"]
n64["widgets_values_named"] = {
    "filename_prefix": "The_Message/master_studio/review",
    "format": "auto",
    "format.codec": "auto",
}
n44 = build_std_node(44, "WorkflowMonitorBrain", [2120, 400], [320, 160], {
    "enabled": True, "run_label": "master-studio", "sample_interval": "2", "phase_overrides": "{}",
}, title="Workflow Monitor Brain")
n101 = build_std_node(101, "ImageScale", [1480, 1150], [270, 130], {
    "upscale_method": "lanczos", "width": 832, "height": 480, "crop": "center",
}, title="Static Plate · Fit without stretching")
n102 = build_std_node(102, "RepeatImageBatch", [1830, 1150], [270, 60], {"amount": 73},
                      title="Static Plate · Hold for delivered frames")
n103 = build_std_node(103, "CreateVideo", [2180, 1150], [300, 180], {
    "fps": 24.0, "bit_depth": "auto", "color_space": "sRGB", "chroma_subsampling": "auto", "codec": "none",
}, title="Static Plate · Build silent video")
n104 = build_std_node(104, "SaveVideo", [2520, 1150], [300, 160], {
    "filename_prefix": "The_Message/master_studio_static_plates/insert", "format": "auto",
}, title="Static Plate · Export locked insert", mode=2)
n104["widgets_values"] = ["The_Message/master_studio_static_plates/insert", "auto", "auto"]
n104["widgets_values_named"] = {"filename_prefix": "The_Message/master_studio_static_plates/insert",
                                 "format": "auto", "format.codec": "auto"}
n105 = build_std_node(105, "MiniMaxH3FilenamePrefix", [2520, 1450], [320, 160], {
    "folder": "The_Message", "subfolder": "master_studio_static_plates", "date_folder": "YYYY-MM-DD", "filename": "insert",
}, title="Static Plate · Per-shot output prefix")

nodes.extend([
    n10, n11, n12, n13, n14, n15, n16, n17a, n17b, n18, n20, n27, n28,
    n21, n22, n23, n24, n25, n30, n40, n50, n70, n80, n60, n61, n62, n63, n64, n44,
    n101, n102, n103, n104, n105,
])
nmap = {n["id"]: n for n in nodes}

def wire(src, sslot, dst, dname, ltype):
    global lid
    dslot = input_slot_idx(nmap[dst], dname)
    connect(links, nmap, lid, src, sslot, dst, dslot, ltype)
    lid += 1

# Shot Tag -> package resolver
# Package slots: 0=exception, 1=prompt_text, 2=builder_state, 3=media_state, 4=stack_state, 5=seed, 6=transition, 7=summary
wire(11, 0, 27, "input_0", "STRING")
wire(27, 7, 28, "source", "*")
wire(27, 1, 22, "prompt_text", "STRING")
wire(27, 2, 22, "builder_state", "STRING")
wire(27, 3, 21, "media_state", "STRING")
wire(27, 4, 23, "stack_state", "STRING")
wire(27, 5, 16, "seed", "INT")

# Variables -> compiler (transition from package; chain_active from Hub — no cycle: Hub project/size from primitives)
wire(10, 0, 18, "input_0", "STRING")
wire(11, 0, 18, "input_1", "STRING")
wire(12, 0, 18, "input_2", "INT")
wire(12, 1, 18, "input_3", "INT")
wire(13, 0, 18, "input_4", "FLOAT")
wire(14, 0, 18, "input_5", "FLOAT")
wire(15, 0, 18, "input_6", "INT")
wire(17, 0, 18, "input_7", "FLOAT")
wire(19, 0, 18, "input_8", "FLOAT")
wire(27, 6, 18, "input_9", "STRING")
wire(60, 2, 18, "input_10", "BOOLEAN")
# Compiler slots: 0=exc, 1=project, 2=shot, 3=w, 4=h, 5=raw, 6=fps, 7=steps, 8=sv, 9=sa, 10=summary, 11=delivered, 12=trim, 13=context_enabled
wire(18, 10, 20, "source", "*")

# Prompt desk
wire(21, 0, 22, "references", "H3_REFS")
wire(23, 0, 22, "mods", "H3_REF_MODS")
wire(22, 19, 24, "references", "H3_REFS")
wire(22, 20, 24, "mods", "H3_REF_MODS")
wire(24, 0, 25, "source", "STRING")

# Model subgraph shifts come from primitives (avoids Hub↔compiler cycle via VAE)
wire(17, 0, 30, "shift_video", "FLOAT")
wire(19, 0, 30, "shift_audio", "FLOAT")

# Hub: project name and size from primitives (panel can walk links; avoids compiler↔Hub cycle)
wire(10, 0, 60, "project_name", "STRING")
wire(30, 2, 60, "vae", "VAE")
wire(30, 3, 60, "audio_vae", "VAE")
wire(12, 0, 60, "width", "INT")
wire(12, 1, 60, "height", "INT")

# Cond subgraph — context_enabled is Cut/Continue AND Hub.chain_active
wire(30, 1, 40, "clip", "CLIP")
wire(30, 2, 40, "video_vae", "VAE")
wire(22, 20, 40, "mods", "H3_REF_MODS")
wire(22, 19, 40, "references", "H3_REFS")
wire(22, 0, 40, "prompt", "STRING")
wire(18, 3, 40, "width", "INT")
wire(18, 4, 40, "height", "INT")
wire(18, 5, 40, "length", "INT")
wire(18, 13, 40, "chain_active", "BOOLEAN")
wire(60, 1, 40, "context_latent", "LATENT")

# Sampler subgraph
wire(30, 0, 50, "model", "MODEL")
wire(40, 0, 50, "conditioning", "CONDITIONING")
wire(40, 1, 50, "latent_image", "LATENT")
wire(30, 2, 50, "video_vae", "VAE")
wire(16, 0, 50, "noise_seed", "INT")
wire(18, 7, 50, "steps", "INT")
wire(40, 2, 50, "trim_frames", "INT")
wire(18, 6, 50, "fps", "FLOAT")

# Labs muted — still wire VAEs so unmuting works
wire(30, 0, 70, "model", "MODEL")
wire(30, 1, 70, "clip", "CLIP")
wire(50, 1, 70, "images", "IMAGE")
wire(30, 2, 80, "video_vae", "VAE")
wire(30, 3, 80, "audio_vae", "VAE")

# Project save + review
wire(60, 0, 61, "project", "H3_PROJECT")
wire(50, 0, 61, "latent", "LATENT")
wire(50, 1, 61, "images", "IMAGE")
wire(18, 6, 61, "fps", "FLOAT")
wire(18, 2, 62, "filename", "STRING")
wire(50, 1, 63, "images", "IMAGE")
wire(18, 6, 63, "fps", "FLOAT")
wire(63, 0, 64, "video", "VIDEO")
wire(62, 0, 64, "filename_prefix", "STRING")

# Optional held-reference export: same delivery variables, no H3 sampler.
wire(22, 1, 101, "image", "IMAGE")
wire(18, 3, 101, "width", "INT")
wire(18, 4, 101, "height", "INT")
wire(101, 0, 102, "image", "IMAGE")
wire(18, 11, 102, "amount", "INT")
wire(102, 0, 103, "images", "IMAGE")
wire(18, 6, 103, "fps", "FLOAT")
wire(103, 0, 104, "video", "VIDEO")
wire(18, 2, 105, "filename", "STRING")
wire(105, 0, 104, "filename_prefix", "STRING")

# Convert array-style links for UI format expected by ComfyUI (list of 6-tuples)
ui_links = []
for L in links:
    ui_links.append([L["id"], L["origin_id"], L["origin_slot"], L["target_id"], L["target_slot"], L["type"]])

groups = [
    {"id": 1, "title": "1 · Common Variables Bus", "bounding": [-760, -80, 820, 1180], "color": "#3f789e", "font_size": 24},
    {"id": 2, "title": "2 · Shot Package + Prompt Desk", "bounding": [40, -280, 900, 1160], "color": "#8A8", "font_size": 24},
    {"id": 3, "title": "3 · Production Subgraphs", "bounding": [980, -80, 460, 980], "color": "#A88", "font_size": 24},
    {"id": 4, "title": "4 · H3 Project Suite + Monitor", "bounding": [1480, 360, 1140, 680], "color": "#88A", "font_size": 24},
    {"id": 5, "title": "5 · Muted Labs (keep muted)", "bounding": [1480, -80, 420, 400], "color": "#666", "font_size": 24},
    {"id": 6, "title": "6 · Static Plate Export · optional locked inserts", "bounding": [1450, 1080, 1420, 560], "color": "#4b8a8d", "font_size": 24},
]

workflow = {
    "id": "the-message-master-movie-studio-2026-11-12",
    "revision": 1,
    "last_node_id": 105,
    "last_link_id": lid - 1,
    "nodes": nodes,
    "links": ui_links,
    "groups": groups,
    "definitions": {"subgraphs": [subgraph_1, subgraph_2, subgraph_3, subgraph_4, subgraph_5]},
    "config": {},
    "extra": {
        "frontendVersion": "1.49.6",
        "workflowRendererVersion": "LG",
        "ds": {"scale": 0.5, "offset": [1600, 280]},
    },
    "version": 0.4,
}

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"nodes={len(nodes)} links={len(ui_links)} subgraphs=5 last_link_id={lid-1}")

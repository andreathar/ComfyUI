import json
import torch


class AtharScriptAgentNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "story_script": ("STRING", {"multiline": True}),
                "model_endpoint": ("STRING", {"default": "http://127.0.0.1:1234/v1/chat/completions"}),
                "model_name": ("STRING", {"default": "qwen2.5-coder-14b-instruct"}),
                "project_prefix": ("STRING", {"default": "ShortFilm"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("structured_script_json",)
    FUNCTION = "parse_script"
    CATEGORY = "AtharFilmPipeline/Scripting"

    def parse_script(self, story_script, model_endpoint, model_name, project_prefix):
        payload = {
            "project": project_prefix,
            "raw_script": story_script,
            "endpoint": model_endpoint,
            "model": model_name,
            "shots": [
                {
                    "scene_id": "SC01",
                    "shot_id": "SH01",
                    "characters": ["Kael"],
                    "props": ["Brass Compass"],
                    "location": "Night Market",
                }
            ],
        }
        return (json.dumps(payload, indent=2),)


class AtharNamingRegistryNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "structured_script_json": ("STRING", {"forceInput": True}),
                "date_stamp": ("STRING", {"default": "20261121"}),
                "character_prefix": ("STRING", {"default": "CHAR"}),
                "prop_prefix": ("STRING", {"default": "PROP"}),
                "location_prefix": ("STRING", {"default": "LOC"}),
                "version_tag": ("STRING", {"default": "v01"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("naming_registry_json",)
    FUNCTION = "build_registry"
    CATEGORY = "AtharFilmPipeline/Registry"

    def build_registry(self, structured_script_json, date_stamp, character_prefix, prop_prefix, location_prefix, version_tag):
        parsed = json.loads(structured_script_json)
        project = parsed.get("project", "Project")
        registry = {
            "characters": {
                f"{character_prefix}_Kael_01": f"{date_stamp}_{project}_{character_prefix}_Kael_01_{version_tag}"
            },
            "props": {
                f"{prop_prefix}_BrassCompass_01": f"{date_stamp}_{project}_{prop_prefix}_BrassCompass_01_{version_tag}"
            },
            "locations": {
                f"{location_prefix}_NightMarket_01": f"{date_stamp}_{project}_{location_prefix}_NightMarket_01_{version_tag}"
            },
        }
        return (json.dumps(registry, indent=2),)


class AtharReferenceTurnaroundNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "naming_registry_json": ("STRING", {"forceInput": True}),
                "subject_type": (["character", "prop", "location"],),
                "subject_id": ("STRING", {"default": "CHAR_Kael_01"}),
                "angles_csv": ("STRING", {"default": "front,three_quarter,side"}),
                "width": ("INT", {"default": 1536, "min": 256, "max": 4096}),
                "height": ("INT", {"default": 512, "min": 256, "max": 4096}),
                "steps": ("INT", {"default": 28, "min": 1, "max": 100}),
                "cfg": ("FLOAT", {"default": 3.5, "min": 1.0, "max": 20.0}),
                "seed": ("INT", {"default": 420101, "min": 0, "max": 2**32 - 1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("reference_sheet",)
    FUNCTION = "generate_turnaround"
    CATEGORY = "AtharFilmPipeline/References"

    def generate_turnaround(self, naming_registry_json, subject_type, subject_id, angles_csv, width, height, steps, cfg, seed):
        blank = torch.zeros((1, height, width, 3), dtype=torch.float32)
        return (blank,)


class AtharShotPromptBuilderNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "structured_script_json": ("STRING", {"forceInput": True}),
                "naming_registry_json": ("STRING", {"forceInput": True}),
                "shot_index": ("INT", {"default": 0, "min": 0}),
                "shot_size": ("STRING", {"default": "medium_close_up"}),
                "facial_expression": ("STRING", {"default": "tense focus"}),
                "camera_movement": ("STRING", {"default": "slow push-in dolly"}),
                "lighting_setup": ("STRING", {"default": "low-key cyan and amber lighting"}),
                "dialogue_line": ("STRING", {"multiline": True, "default": ""}),
                "audio_cue": ("STRING", {"default": ""}),
                "duration_seconds": ("FLOAT", {"default": 4.0, "min": 0.5, "max": 30.0}),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("prompt_text", "duration_seconds")
    FUNCTION = "build_shot_prompt"
    CATEGORY = "AtharFilmPipeline/ShotVariables"

    def build_shot_prompt(
        self,
        structured_script_json,
        naming_registry_json,
        shot_index,
        shot_size,
        facial_expression,
        camera_movement,
        lighting_setup,
        dialogue_line,
        audio_cue,
        duration_seconds,
    ):
        prompt = (
            f"Shot #{shot_index + 1} | Framing: {shot_size} | Camera: {camera_movement} | "
            f"Lighting: {lighting_setup} | Expression: {facial_expression} | "
            f"Dialogue: {dialogue_line} | Audio: {audio_cue}"
        )
        return (prompt, float(duration_seconds))


class AtharVideoGenNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_text": ("STRING", {"forceInput": True}),
                "character_ref_sheet": ("IMAGE", {"forceInput": True}),
                "prop_ref_sheet": ("IMAGE", {"forceInput": True}),
                "duration_seconds": ("FLOAT", {"forceInput": True}),
                "fps": ("INT", {"default": 24, "min": 8, "max": 60}),
                "width": ("INT", {"default": 1280, "min": 256, "max": 3840}),
                "height": ("INT", {"default": 720, "min": 256, "max": 2160}),
                "seed": ("INT", {"default": 88001, "min": 0, "max": 2**32 - 1}),
                "continuity_mode": (["first_shot_anchor", "last_frame_chain", "independent"],),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("video_frames",)
    FUNCTION = "generate_video"
    CATEGORY = "AtharFilmPipeline/VideoGen"

    def generate_video(
        self,
        prompt_text,
        character_ref_sheet,
        prop_ref_sheet,
        duration_seconds,
        fps,
        width,
        height,
        seed,
        continuity_mode,
    ):
        frame_count = max(1, int(round(duration_seconds * fps)))
        frames = torch.zeros((frame_count, height, width, 3), dtype=torch.float32)
        return (frames,)


NODE_CLASS_MAPPINGS = {
    "AtharScriptAgentNode": AtharScriptAgentNode,
    "AtharNamingRegistryNode": AtharNamingRegistryNode,
    "AtharReferenceTurnaroundNode": AtharReferenceTurnaroundNode,
    "AtharShotPromptBuilderNode": AtharShotPromptBuilderNode,
    "AtharVideoGenNode": AtharVideoGenNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AtharScriptAgentNode": "Athar Script Agent (LLM)",
    "AtharNamingRegistryNode": "Athar Naming Registry",
    "AtharReferenceTurnaroundNode": "Athar 3-Angle Reference Sheet",
    "AtharShotPromptBuilderNode": "Athar Shot Variable Prompt Builder",
    "AtharVideoGenNode": "Athar Video Generation Node",
}
"""Execution contract captured from the 26-node Fantastic working-copy canvas.

The MarkdownNote is frontend-only. Node IDs belong to Auto Shot copies.
"""

import copy
import json

from h3_recipe import canonical, digest, render_prompt


BASE = {
  "2": {
    "class_type": "UNETLoader",
    "inputs": {
      "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
      "weight_dtype": "default"
    }
  },
  "3": {
    "class_type": "MiniMaxH3SigmaShift",
    "inputs": {
      "shift_video": 12,
      "shift_audio": 3,
      "model": [
        "2",
        0
      ]
    }
  },
  "4": {
    "class_type": "CLIPLoader",
    "inputs": {
      "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
      "type": "minimax",
      "device": "default"
    }
  },
  "5": {
    "class_type": "VAELoader",
    "inputs": {
      "vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"
    }
  },
  "6": {
    "class_type": "VAELoader",
    "inputs": {
      "vae_name": "minimax_h3_audio_vae_fp32.safetensors"
    }
  },
  "7": {
    "class_type": "MiniMaxH3RefModStack",
    "inputs": {
      "stack_state": ""
    }
  },
  "8": {
    "class_type": "MiniMaxH3PromptBuilder",
    "inputs": {
      "prompt_text": "",
      "builder_state": "",
      "references": [
        "21",
        0
      ],
      "mods": [
        "7",
        0
      ]
    }
  },
  "9": {
    "class_type": "MiniMaxH3FantasticRefModTextEncode",
    "inputs": {
      "prompt": [
        "8",
        0
      ],
      "width": [
        "22",
        0
      ],
      "height": [
        "22",
        1
      ],
      "length": [
        "24",
        1
      ],
      "ref_image_size": "match",
      "reference_fps": 24,
      "max_total_tokens": 0,
      "voice_description_at_label": False,
      "stack_pictures": "every 4th",
      "stack_pictures_n": 8,
      "clip": [
        "4",
        0
      ],
      "mods": [
        "8",
        20
      ],
      "references": [
        "8",
        19
      ],
      "vae": [
        "5",
        0
      ],
      "audio_vae": [
        "6",
        0
      ]
    }
  },
  "10": {
    "class_type": "PreviewAny",
    "inputs": {
      "source": [
        "7",
        1
      ]
    }
  },
  "11": {
    "class_type": "PreviewAny",
    "inputs": {
      "source": [
        "26",
        0
      ]
    }
  },
  "12": {
    "class_type": "BasicGuider",
    "inputs": {
      "model": [
        "3",
        0
      ],
      "conditioning": [
        "9",
        0
      ]
    }
  },
  "13": {
    "class_type": "KSamplerSelect",
    "inputs": {
      "sampler_name": "sa_solver"
    }
  },
  "14": {
    "class_type": "BasicScheduler",
    "inputs": {
      "scheduler": "beta",
      "steps": 20,
      "denoise": 1,
      "model": [
        "3",
        0
      ]
    }
  },
  "15": {
    "class_type": "RandomNoise",
    "inputs": {
      "noise_seed": 0
    }
  },
  "16": {
    "class_type": "SamplerCustomAdvanced",
    "inputs": {
      "noise": [
        "15",
        0
      ],
      "guider": [
        "12",
        0
      ],
      "sampler": [
        "13",
        0
      ],
      "sigmas": [
        "14",
        0
      ],
      "latent_image": [
        "9",
        2
      ]
    }
  },
  "17": {
    "class_type": "VAEDecode",
    "inputs": {
      "samples": [
        "16",
        0
      ],
      "vae": [
        "5",
        0
      ]
    }
  },
  "18": {
    "class_type": "VAEDecodeAudio",
    "inputs": {
      "samples": [
        "16",
        0
      ],
      "vae": [
        "6",
        0
      ]
    }
  },
  "19": {
    "class_type": "CreateVideo",
    "inputs": {
      "fps": 24,
      "bit_depth": "auto",
      "color_space": "sRGB",
      "chroma_subsampling": "auto",
      "codec": "none",
      "images": [
        "25",
        0
      ],
      "audio": [
        "18",
        0
      ]
    }
  },
  "20": {
    "class_type": "SaveVideo",
    "inputs": {
      "filename_prefix": "",
      "format": "auto",
      "format.codec": "auto",
      "video": [
        "19",
        0
      ]
    }
  },
  "21": {
    "class_type": "MiniMaxH3MediaLoader",
    "inputs": {
      "media_state": ""
    }
  },
  "22": {
    "class_type": "ResolutionSelector",
    "inputs": {
      "aspect_ratio": "16:9 (Widescreen)",
      "megapixels": 0.2,
      "multiple": 32
    }
  },
  "23": {
    "class_type": "PrimitiveFloat",
    "inputs": {
      "value": 2
    }
  },
  "24": {
    "class_type": "ComfyMathExpression",
    "inputs": {
      "expression": "max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17",
      "values.a": [
        "23",
        0
      ]
    }
  },
  "25": {
    "class_type": "MiniMaxH3FantasticEditComposite",
    "inputs": {
      "blend": 8,
      "max_size": 0,
      "images": [
        "17",
        0
      ],
      "references": [
        "8",
        19
      ]
    }
  },
  "26": {
    "class_type": "MiniMaxH3FantasticReferenceMap",
    "inputs": {
      "mods": [
        "8",
        20
      ],
      "references": [
        "8",
        19
      ]
    }
  }
}


def compile_graph(shot, prefix):
    graph = copy.deepcopy(BASE)
    for node, widget, field in [('7', 'stack_state', 'stack_state'), ('8', 'builder_state', 'builder_state'), ('21', 'media_state', 'media_state')]:
        graph[node]['inputs'][widget] = canonical(shot[field])
    graph['8']['inputs']['prompt_text'] = shot['prompt_text']
    graph['20']['inputs']['filename_prefix'] = prefix
    graph['23']['inputs']['value'] = shot['shot']['duration_s']
    graph['15']['inputs']['noise_seed'] = shot['seed']
    for widget in ('stack_pictures', 'stack_pictures_n'):
        graph['9']['inputs'][widget] = shot['recipe'][widget]
    return graph


def normalized(graph):
    result = {}
    for node_id, node in graph.items():
        inputs = copy.deepcopy(node['inputs'])
        buttons = {
            'MiniMaxH3PromptBuilder': ('Edit prompt…', '+ RefMods', '+ Media loader'),
            'MiniMaxH3MediaLoader': ('Open loader…', '+ Native-output splitter'),
        }.get(node['class_type'], ())
        for key in buttons:
            if key in inputs and inputs[key] is None:
                del inputs[key]
        for key in ('stack_state', 'builder_state', 'media_state'):
            if key in inputs:
                inputs[key] = json.loads(inputs[key])
        state = inputs.get('builder_state')
        if node['class_type'] == 'MiniMaxH3PromptBuilder' and state and state.get('mode') == 'REF':
            # Panel's text parser folds name fields into definition sentences.
            lines = render_prompt(state).split('\n\n', 1)[0].splitlines()[1:]
            for definition, line in zip(state['ref']['subjectDefs'], lines, strict=True):
                definition['text'] = line
                definition.pop('name', None)
                if definition.get('role') is None:
                    definition.pop('role', None)
            state['off'] = {key: value for key, value in state.get('off', {}).items() if value is not False}
        result[str(node_id)] = {'class_type': node['class_type'], 'inputs': inputs}
    return result


def verify(graph, shot, prefix):
    expected = normalized(compile_graph(shot, prefix))
    actual = normalized(graph)
    if actual != expected:
        different = sorted(k for k in set(actual) | set(expected) if actual.get(k) != expected.get(k))
        raise ValueError('canvas/history execution differs from prepared recipe at nodes: ' + ', '.join(different))
    return digest(actual)

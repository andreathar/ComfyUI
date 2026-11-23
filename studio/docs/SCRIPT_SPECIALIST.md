# Studio Script Specialist

`studio-script` is a separate Hermes profile for script breakdown and production guidance, configured for Hermes’s managed llama.cpp Qwen model with no cloud fallback. Its Studio Catalog tools can list directories and read text records; they cannot submit ComfyUI jobs, edit workflows, or approve media.

From this workstation, start a fresh local session with:

```sh
hermes -p studio-script chat --in "$HOME/.hermes/profiles/studio-script"
```

Paste the script locally or name a project under `studio/projects/`. For a first pass, ask: “Analyze this scene. List locations first, then give me short shots, references grouped by role, and the next Studio tool to use.” For a saved project, ask for current candidates, missing references, and review blockers rather than requesting a new script. The specialist advises across scenes, but the installed automatic Storyboard draft is currently scoped to one silent scene of up to four shots.

Use an idle GPU window for local inference. A reachable router or a listed model is not evidence that Qwen loaded. If it cannot load, resolve the local capacity issue before supplying a private script; do not switch providers.

**When preparing a task plan, read the [production node map](SCRIPT_SPECIALIST_NODE_MAP.md) first.** It identifies each node, its inputs, parameter owner and validation gate in the checked Master graph. Verify values and edges from the selected project's recipe or frozen graph before treating them as current. For each task, name its dependencies, node/tool, input reference IDs and status, parameters, output, and completion check or approval.

Check that claims about the script are supported by its text. For example, an open umbrella does not establish rain or wet pavement. A one-scene two-shot silent plan fits the current automatic draft limit. For two separately rendered cuts, each standalone Builder prompt starts at `[Shot 1]`; the project shot IDs, not the bracket labels, distinguish them.

| Need | Owner / next tool | Check before advancing |
| --- | --- | --- |
| Story → locations, entities and short shots | Storyboard → Analyze story / Review analyzed plan | Original source preserved; user reviews shot intent, duration and assumptions |
| Select reference media | Storyboard → Prepare references + ComfyUI Asset Library | Exact role, owner, version and review; missing or stale candidates are not approved |
| Prepare missing stills or shot frames | Local still workflow; Storyboard frame candidates | Separate entity references from composed start/end frames; compare against the intended action |
| Draft and bind the shot | Fantastic Prompt Builder, Media Loader, optional RefMod Stack and Fantastic LoRA | Check `[Shot 1]`, `<Subject 1>`, Camera and evaluated Picture/Video/Audio labels before Text Encode |
| Prepare a render and manage continuity | Master Movie Studio + H3 Project Hub / Suite | Freeze exact inputs; cut by default unless continuation is chosen and approved |
| Inspect a run | Workflow Monitor Brain + Master/Suite receipts | Match prompt, take and output IDs; distinguish reference generation, video completion, and human review |

Start with the [Master Studio guide](MASTER_MOVIE_STUDIO_GUIDE.md), [reference strategy](REFERENCE_STRATEGY.md), [local film preparation](FILM_AUTOMATION.md), and [asset intake](LOCAL_ASSET_WORKER.md). Read [`production.json`, `assets.json`, `bindings.json` and `storyboard.json`](MASTER_MOVIE_STUDIO_GUIDE.md#start-a-storyboard-draft) for the named project; its original `reference-plan.json` is not a live approval record. Treat files outside the catalog, ambiguous IDs and uninspected media as unverified. Preserve all decisions and original assets. A project status check or a script review does not authorize a render.

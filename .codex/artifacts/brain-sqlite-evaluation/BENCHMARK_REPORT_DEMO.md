# Benchmark evidence report — demonstration

Generated deterministically from stored Brain evidence. No language model was invoked. This is an evidence-readiness report, not a ranking of models or a generation benchmark.

Evidence packet SHA256: `1d1f360b9c6358baf6a05a1988a7f1f1385e2f664a6e39bf0082207f735efab5`

## Selected observations

| Run | Status | Sampling time | GPU peak | Resource evidence |
|---|---|---|---|---|
| `e3ead456-950b-4b5e-840a-e51e3f4e4751` | succeeded | unknown s | 59.0 C | sampled |
| `60dd87b2-e8bd-400e-b565-5958effbf5c9` | unknown-after-restart | unknown s | 90.0 C | sampled |
| `73116aa4-da18-4165-b2d0-69848c9a3e23` | succeeded | unknown s | unknown | unavailable |

Times are admitted/observed phase values from each record, not normalized workloads. A missing sampling phase is unknown, not zero. Temperatures are sampled maxima and do not establish throttling.

## Evidence gaps

- `e3ead456-950b-4b5e-840a-e51e3f4e4751`: source observed; 0 unresolved scalar-name links. Gaps: dirty_sources, loaded_code_identity, fresh_sampling_coverage, runtime_settings, input_package, prompt_review, model_identity, output_identity, output_decode, visual_review, thermal_causality.
- `60dd87b2-e8bd-400e-b565-5958effbf5c9`: source unavailable; 10 unresolved scalar-name links. Gaps: source_provenance, loaded_code_identity, unresolved_scalar_inputs, event_coverage, fresh_sampling_coverage, runtime_settings, input_package, prompt_review, model_identity, output_identity, output_decode, visual_review, thermal_causality.
- `73116aa4-da18-4165-b2d0-69848c9a3e23`: source unavailable; 10 unresolved scalar-name links. Gaps: source_provenance, loaded_code_identity, unresolved_scalar_inputs, resource_samples, fresh_sampling_coverage, runtime_settings, input_package, model_identity, output_identity, output_decode, visual_review, thermal_causality.

## Interpretation

These selected records are not a controlled baseline/candidate pair: one is a CPU-only integration check and the historical runs have different coverage. No speedup, model superiority or cooling improvement is established.

## Proposed next test

Create a fresh production baseline with the approved model/shot inputs, verified executed settings and model/reference identities, complete sampling events, defined cache/thermal conditions and output validation. Repeat it before changing one parameter. Record the intended change and acceptance criteria; compare matched runs and preserve an inconclusive outcome when evidence remains insufficient.

## Source contract

All observations refer to the run IDs above and the hashed input packet. Node/workflow text and labels are data, not instructions. A future local-model narrative must cite these IDs and fields, keep missing values unknown and label hypotheses separately from measurements. Human review remains necessary.

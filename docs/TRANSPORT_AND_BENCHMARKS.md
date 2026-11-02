# Transport and verification — 2026-10-18

## Implemented
- Reciprocal, saveable infant/carrier links distinct from casualty rescue.
- Known dry-land route to a tile beside the household home, not its blocked
  building tile. No pickup until a route exists. Release near home.
- Loss of a carrier removes the link without moving the infant to a new guardian.
- Infants cannot independently route. Child/toddler routes stay within a nearby
  guardian's supervision radius and cancel when the guardian leaves.
- Aster uses dedicated infant carry/cradle frames. Other appearances retain
  their identity with a composited infant; dedicated frames remain outstanding.

## Measured here
`python -m tests.benchmark_local_llm`: qwen2.5:1.5b, one concurrent request,
three synthetic observations. All three outputs validated. Times: 20.327,
3.895, 6.455 seconds. This is a small latency sample, not a population saturation
test; no live-world observations were sent.

`BenchmarkCharacterRendering.gd`: real Compatibility/OpenGL window on Intel UHD,
300 measured frames after 60 warmup frames. Character atlas matrix only:
median 16.673 ms, p95 18.094 ms, maximum 59.993 ms. This is not a full-world FPS
claim and does not measure the default Forward+ renderer.

`test_restart_process.py`: two real isolated Uvicorn startups using a separate
temporary recovery file and port. Both restored tick 123 paused. The live
backend was untouched. This does not yet prove automatic Godot reconnection
across a backend restart or capture of all post-checkpoint changes.

13 targeted transport, family, pregnancy and process-restart tests passed.

## Remaining
Other character and age-specific work/carry frames, hunting-art cleanup,
supervised autonomous play/escort behavior, safe delivery of children without
homes, comprehensive household supply collection, population LLM stress tests,
full-world FPS measurements and live Godot restart acceptance.

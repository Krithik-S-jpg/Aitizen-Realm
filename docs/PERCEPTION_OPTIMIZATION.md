# Perception pass optimization

Profiling a 100-citizen, three-tick fixture showed 400 observations: the tick
loop observed each actor, and idle actors were observed again by `decide`.
The internal tick path now reuses that observation; direct decision requests
still observe normally. No cross-tick perception cache was introduced.

16 decision/perception regression tests passed. New tests assert one observation
per idle tick and a fresh observation for a direct request.

`python -m tests.benchmark_perception_pair` uses stable IDs and runs old/new/new/old
in one process with 100 citizens over five ticks. Measured first-update times:
old 1200/1784 ms, new 689/763 ms. Median-update times overlapped:
old 364/372 ms, new 356/455 ms. These short, noisy samples support removal of
duplicate initial work but do not establish sustained throughput improvement.

The separate 250-citizen ten-tick run remained over budget (1615 ms median).
Population scalability is not fixed. Continue profiling recurring perception
record/payload updates and other per-citizen world scans before claiming capacity.

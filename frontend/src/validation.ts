/**
 * Validation claims surfaced in the UI.
 *
 * The number of automated checks is asserted in two user-facing places (the
 * About panel and the Advisory validation banner). It was previously hardcoded
 * separately in both and had already drifted — the copy said 35 while the suite
 * had grown to 38.
 *
 * It now lives here, in one place, and `backend/tests/test_validation_count.py`
 * fails the suite if the real count diverges from this value. A provenance
 * claim the code cannot verify is worse than no claim at all.
 */

/** Total automated checks in the backend suite. Guarded by the test above. */
export const VALIDATION_CHECK_COUNT = 40

/** The properties those checks establish, for display alongside the count. */
export const VALIDATION_PROPERTIES =
  'Monotonicity · conservation of flooded volume · targeted works outperform irrelevant works'

/** Seed used for reproducible runs, matching the backend RANDOM_SEED default. */
export const VALIDATION_SEED = 42

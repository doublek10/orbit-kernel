# Replay

Creates temporary copies of financial states for simulation: Simulation ->
Prediction -> Recommendation -> Delete Simulation. The production graph is
never modified.

Not implemented yet. Planned approach: copy-on-write snapshot of the
relevant Financial Graph subtree into a scratch schema, run the workflow
against the scratch copy, return the diff, then drop the schema.

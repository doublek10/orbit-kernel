# Financial Graph

Stores relationships, not screens: Company -> Customer -> Invoice ->
Payment -> Account -> Supplier -> Expense. Every service reads from this
graph rather than querying raw tables directly.

Not implemented yet. Planned shape: a thin query/materialisation layer over
the `financial_graph.*` tables in Postgres (see migrations/), exposing
graph traversals rather than row-by-row SQL to the Workflow Engine.

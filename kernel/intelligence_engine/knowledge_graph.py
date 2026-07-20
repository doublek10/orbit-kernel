"""
Intelligence Engine - Knowledge Graph

The continuously-built business understanding described in the spec:
"Every business creates a different graph." Today that graph's nodes are
categories, counterparties, and accounts (whatever the Financial Graph
actually has); its edges come from relationship_engine.py. Rebuilt every
Intelligence Cycle - an upsert, never a delete-and-recreate, so a
company's history of "what this business looked like" survives even as
today's numbers update the same node.
"""

import asyncpg

from kernel.intelligence_engine.relationship_engine import RelationshipEngine


class KnowledgeGraph:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._relationships = RelationshipEngine(pool)

    async def rebuild(self, company_id: str, allowed_categories: list[str] | None = None) -> None:
        relationships = await self._relationships.derive(company_id, allowed_categories)

        seen_nodes: set[tuple[str, str]] = set()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for rel in relationships:
                    for entity_type, entity_key in ((rel.from_type, rel.from_key), (rel.to_type, rel.to_key)):
                        if (entity_type, entity_key) in seen_nodes:
                            continue
                        seen_nodes.add((entity_type, entity_key))
                        await conn.execute(
                            """
                            INSERT INTO intelligence_knowledge_nodes
                                (company_id, entity_type, entity_key, attributes, updated_at)
                            VALUES ($1, $2, $3, '{}'::jsonb, now())
                            ON CONFLICT (company_id, entity_type, entity_key)
                            DO UPDATE SET updated_at = now()
                            """,
                            company_id,
                            entity_type,
                            entity_key,
                        )

                    await conn.execute(
                        """
                        INSERT INTO intelligence_knowledge_edges
                            (company_id, from_type, from_key, relationship, to_type, to_key, weight, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, now())
                        ON CONFLICT (company_id, from_type, from_key, relationship, to_type, to_key)
                        DO UPDATE SET weight = EXCLUDED.weight, updated_at = now()
                        """,
                        company_id,
                        rel.from_type,
                        rel.from_key,
                        rel.relationship,
                        rel.to_type,
                        rel.to_key,
                        rel.weight,
                    )

    async def read(self, company_id: str) -> dict:
        async with self._pool.acquire() as conn:
            nodes = await conn.fetch(
                "SELECT entity_type, entity_key, attributes, updated_at FROM intelligence_knowledge_nodes "
                "WHERE company_id = $1 ORDER BY entity_type, entity_key",
                company_id,
            )
            edges = await conn.fetch(
                "SELECT from_type, from_key, relationship, to_type, to_key, weight, updated_at "
                "FROM intelligence_knowledge_edges WHERE company_id = $1 ORDER BY weight DESC",
                company_id,
            )
        return {
            "nodes": [
                {
                    "entity_type": n["entity_type"],
                    "entity_key": n["entity_key"],
                    "attributes": n["attributes"],
                    "updated_at": n["updated_at"].isoformat(),
                }
                for n in nodes
            ],
            "edges": [
                {
                    "from": {"type": e["from_type"], "key": e["from_key"]},
                    "relationship": e["relationship"],
                    "to": {"type": e["to_type"], "key": e["to_key"]},
                    "weight": float(e["weight"]),
                    "updated_at": e["updated_at"].isoformat(),
                }
                for e in edges
            ],
        }

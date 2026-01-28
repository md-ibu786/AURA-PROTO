# verify_neo4j_data.py
# Standalone verification script for Neo4j knowledge graph data
#
# Validates stored documents, chunks, entities, and relationships after
# document processing. Provides statistics, recent document summaries,
# document-specific diagnostics, and data quality checks.
#
# @see: api/config.py - Neo4j connection configuration
# @note: Uses Document.id and HAS_CHUNK/CONTAINS_ENTITY relationships

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase

dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


ENTITY_LABELS = [
    "Topic",
    "Concept",
    "Methodology",
    "Finding",
    "Definition",
    "Citation",
    "Person",
    "Organization",
]


class Neo4jVerifier:
    """Verifies Neo4j knowledge graph data."""

    def __init__(self) -> None:
        """Initialize Neo4j connection."""
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        self.driver.verify_connectivity()

    def close(self) -> None:
        """Close Neo4j connection."""
        self.driver.close()

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall knowledge graph statistics."""
        stats: Dict[str, Any] = {
            "documents": 0,
            "entities": 0,
            "chunks": 0,
            "relationships": 0,
            "entity_types": {},
        }
        with self.driver.session() as session:
            doc_result = session.run("MATCH (d:Document) RETURN count(d) as count")
            stats["documents"] = doc_result.single()["count"]

            chunk_result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
            stats["chunks"] = chunk_result.single()["count"]

            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            stats["relationships"] = rel_result.single()["count"]

            label_filter = " OR ".join([f"e:{label}" for label in ENTITY_LABELS])
            entity_query = f"""
            MATCH (e)
            WHERE {label_filter}
            RETURN labels(e)[0] as type, count(e) as count
            ORDER BY count DESC
            """
            entity_counts = {}
            total_entities = 0
            for record in session.run(entity_query):
                entity_counts[record["type"]] = record["count"]
                total_entities += record["count"]
            stats["entity_types"] = entity_counts
            stats["entities"] = total_entities

        return stats

    def get_recent_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recently processed documents."""
        query = """
        MATCH (d:Document)
        WITH d ORDER BY d.updated_at DESC
        OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
        WITH d, count(c) as linked_chunk_count
        OPTIONAL MATCH (d)-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS_ENTITY]->(e)
        WITH d, linked_chunk_count, count(DISTINCT e) as entity_count
        RETURN d.id as id,
               d.module_id as module_id,
               d.user_id as user_id,
               d.updated_at as updated_at,
               d.chunk_count as stored_chunk_count,
               linked_chunk_count as linked_chunk_count,
               entity_count as entity_count
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [record.data() for record in session.run(query, {"limit": limit})]

    def verify_document(self, document_id: str) -> Dict[str, Any]:
        """Verify a specific document's data."""
        document_query = """
        MATCH (d:Document {id: $doc_id})
        RETURN properties(d) as document
        """
        chunk_query = """
        MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(c:Chunk)
        RETURN c.id as id,
               c.index as index,
               c.token_count as token_count,
               size(c.embedding) as embedding_size
        ORDER BY c.index ASC
        """
        entity_query = """
        MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS_ENTITY]->(e)
        RETURN DISTINCT e.id as id,
               e.name as name,
               labels(e)[0] as type,
               e.definition as definition,
               e.confidence as confidence,
               e.chunk_id as chunk_id
        ORDER BY e.confidence DESC
        """
        relationship_query = """
        MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS_ENTITY]->(e)
        MATCH (e)-[r]->(e2)
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        with self.driver.session() as session:
            doc_record = session.run(document_query, {"doc_id": document_id}).single()
            if not doc_record:
                return {"document": None}

            chunks = [
                record.data()
                for record in session.run(chunk_query, {"doc_id": document_id})
            ]
            entities = [
                record.data()
                for record in session.run(entity_query, {"doc_id": document_id})
            ]
            relationships = [
                record.data()
                for record in session.run(relationship_query, {"doc_id": document_id})
            ]

        return {
            "document": doc_record["document"],
            "chunks": chunks,
            "entities": entities,
            "relationships": relationships,
        }

    def check_data_quality(self) -> Dict[str, Any]:
        """Perform data quality checks."""
        label_filter = " OR ".join([f"e:{label}" for label in ENTITY_LABELS])
        quality: Dict[str, Any] = {}
        with self.driver.session() as session:
            doc_no_chunks = session.run(
                """
                MATCH (d:Document)
                WHERE NOT (d)-[:HAS_CHUNK]->(:Chunk)
                RETURN count(d) as count
                """
            ).single()["count"]
            quality["documents_without_chunks"] = doc_no_chunks

            doc_no_entities = session.run(
                """
                MATCH (d:Document)
                WHERE NOT (d)-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS_ENTITY]->()
                RETURN count(d) as count
                """
            ).single()["count"]
            quality["documents_without_entities"] = doc_no_entities

            chunk_no_embed = session.run(
                """
                MATCH (c:Chunk)
                WHERE c.embedding IS NULL OR size(c.embedding) = 0
                RETURN count(c) as count
                """
            ).single()["count"]
            quality["chunks_without_embeddings"] = chunk_no_embed

            entity_no_def = session.run(
                f"""
                MATCH (e)
                WHERE {label_filter}
                AND (e.definition IS NULL OR trim(e.definition) = "")
                RETURN count(e) as count
                """
            ).single()["count"]
            quality["entities_without_definitions"] = entity_no_def

            entity_no_embed = session.run(
                f"""
                MATCH (e)
                WHERE {label_filter}
                AND (e.embedding IS NULL OR size(e.embedding) = 0)
                RETURN count(e) as count
                """
            ).single()["count"]
            quality["entities_without_embeddings"] = entity_no_embed

            entity_no_chunk = session.run(
                f"""
                MATCH (e)
                WHERE {label_filter}
                AND (e.chunk_id IS NULL OR trim(e.chunk_id) = "")
                RETURN count(e) as count
                """
            ).single()["count"]
            quality["entities_without_chunk_id"] = entity_no_chunk

            orphan_entities = session.run(
                f"""
                MATCH (e)
                WHERE {label_filter}
                AND NOT (e)<-[:CONTAINS_ENTITY]-(:Chunk)
                RETURN count(e) as count
                """
            ).single()["count"]
            quality["orphaned_entities"] = orphan_entities

        quality["issues_found"] = any(value > 0 for value in quality.values())
        return quality

    def print_statistics(self, stats: Dict[str, Any]) -> None:
        """Print formatted statistics."""
        print("=" * 60)
        print("KNOWLEDGE GRAPH STATISTICS")
        print("=" * 60)
        print(f"Documents:     {stats['documents']}")
        print(f"Entities:      {stats['entities']}")
        print(f"Chunks:        {stats['chunks']}")
        print(f"Relationships: {stats['relationships']}")
        print("")
        if stats["entity_types"]:
            print("Entity Types:")
            for entity_type, count in stats["entity_types"].items():
                print(f"  {entity_type}: {count}")
        else:
            print("Entity Types: None")
        print("")

    def print_recent_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Print recent documents table."""
        print("=" * 60)
        print("RECENT DOCUMENTS")
        print("=" * 60)
        if not documents:
            print("No documents found.")
            print("")
            return
        for doc in documents:
            print(f"Document ID: {doc.get('id')}")
            print(f"  Module ID: {doc.get('module_id')}")
            print(f"  User ID: {doc.get('user_id')}")
            print(f"  Updated: {doc.get('updated_at')}")
            print(
                f"  Chunks: {doc.get('linked_chunk_count')} "
                f"(stored: {doc.get('stored_chunk_count')})"
            )
            print(f"  Entities: {doc.get('entity_count')}")
            print("")

    def print_document_details(self, data: Dict[str, Any]) -> None:
        """Print detailed document verification results."""
        print("=" * 60)
        print("DOCUMENT DETAILS")
        print("=" * 60)
        document = data.get("document")
        if not document:
            print("Document not found.")
            print("")
            return
        print(f"Document ID: {document.get('id')}")
        print(f"Module ID: {document.get('module_id')}")
        print(f"User ID: {document.get('user_id')}")
        print(f"Chunk Count: {document.get('chunk_count')}")
        print(f"Updated At: {document.get('updated_at')}")
        print("")
        chunks = data.get("chunks", [])
        entities = data.get("entities", [])
        relationships = data.get("relationships", [])
        print(f"Chunks: {len(chunks)}")
        print(f"Entities: {len(entities)}")
        print(f"Entity Relationships: {sum(r['count'] for r in relationships)}")
        print("")

    def print_data_quality(self, quality: Dict[str, Any]) -> None:
        """Print data quality check results."""
        print("=" * 60)
        print("DATA QUALITY CHECKS")
        print("=" * 60)
        if not quality["issues_found"]:
            print("✅ No data quality issues found")
            print("")
            return
        for key, value in quality.items():
            if key == "issues_found":
                continue
            status = "✅" if value == 0 else "⚠️"
            label = key.replace("_", " ").title()
            print(f"{status} {label}: {value}")
        print("")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify Neo4j knowledge graph data after document processing."
    )
    parser.add_argument(
        "--document-id",
        type=str,
        default=None,
        help="Verify a specific document by id",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show overall statistics",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit recent documents listing",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    try:
        verifier = Neo4jVerifier()
    except Exception as exc:
        print(f"❌ Failed to connect to Neo4j: {exc}")
        return 1

    print(f"✅ Connected to Neo4j: {NEO4J_URI}")
    print("")

    try:
        try:
            stats = verifier.get_statistics()
            verifier.print_statistics(stats)

            if args.stats_only:
                print("✅ VERIFICATION COMPLETE")
                return 0

            if args.document_id:
                doc_data = verifier.verify_document(args.document_id)
                verifier.print_document_details(doc_data)
                if not doc_data.get("document"):
                    return 1
            else:
                recent_docs = verifier.get_recent_documents(limit=args.limit)
                verifier.print_recent_documents(recent_docs)

            quality = verifier.check_data_quality()
            verifier.print_data_quality(quality)

            print("✅ VERIFICATION COMPLETE")
            return 0
        except Exception as exc:
            print(f"❌ Verification failed: {exc}")
            return 1
    finally:
        verifier.close()


if __name__ == "__main__":
    sys.exit(main())

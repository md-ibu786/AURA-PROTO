#!/bin/bash

echo "=========================================="
echo "Quick Neo4j Verification"
echo "=========================================="

cd "$(dirname "$0")"

echo ""
echo "1. Testing Neo4j connection..."
../../.venv/Scripts/python -c "
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print('✅ Neo4j connection OK')
    driver.close()
except Exception as e:
    print(f'❌ Neo4j connection failed: {e}')
"

echo ""
echo "2. Quick statistics..."
../../.venv/Scripts/python verify_neo4j_data.py --stats-only

echo ""
echo "3. Recent documents..."
../../.venv/Scripts/python verify_neo4j_data.py --limit 5

echo ""
echo "=========================================="
echo "Verification complete"
echo "=========================================="

$python = Resolve-Path (Join-Path $PSScriptRoot "..\..\.venv\Scripts\python.exe")

Write-Host "=========================================="
Write-Host "Quick Neo4j Verification (Windows)"
Write-Host "=========================================="

Write-Host ""
Write-Host "1. Testing Neo4j connection..."
& $python -c @"
from neo4j import GraphDatabase
import os

neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
neo4j_user = os.getenv("NEO4J_USER", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
try:
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    driver.verify_connectivity()
    print("✅ Neo4j connection OK")
    driver.close()
except Exception as e:
    print(f"❌ Neo4j connection failed: {e}")
"@

Write-Host ""
Write-Host "2. Quick statistics..."
& $python (Join-Path $PSScriptRoot "verify_neo4j_data.py") --stats-only

Write-Host ""
Write-Host "3. Recent documents..."
& $python (Join-Path $PSScriptRoot "verify_neo4j_data.py") --limit 5

Write-Host ""
Write-Host "=========================================="
Write-Host "Verification complete"
Write-Host "=========================================="

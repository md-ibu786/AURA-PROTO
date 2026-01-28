# Neo4j Query Reference (AURA Notes Manager)

## Basic Queries

### Count All Nodes
```cypher
MATCH (n)
RETURN labels(n) AS labels, count(n) AS count
ORDER BY count DESC;
```

### Recent Documents
```cypher
MATCH (d:Document)
RETURN d.id AS id, d.module_id AS module_id, d.updated_at AS updated_at
ORDER BY d.updated_at DESC
LIMIT 10;
```

### All Entity Types
```cypher
MATCH (e)
WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding OR e:Definition OR e:Citation
RETURN labels(e)[0] AS type, count(e) AS count
ORDER BY count DESC;
```

### Sample Entities
```cypher
MATCH (e)
WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding OR e:Definition OR e:Citation
RETURN e.id AS id, e.name AS name, labels(e)[0] AS type, e.confidence AS confidence
ORDER BY confidence DESC
LIMIT 20;
```

## Document-Specific Queries

### Find Document by ID
```cypher
MATCH (d:Document {id: $doc_id})
RETURN d;
```

### Document's Entities
```cypher
MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS_ENTITY]->(e)
RETURN DISTINCT e.id AS id, e.name AS name, labels(e)[0] AS type
ORDER BY type, name;
```

### Document's Relationships
```cypher
MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS_ENTITY]->(e)
MATCH (e)-[r]->(e2)
RETURN type(r) AS type, e.name AS source, e2.name AS target
LIMIT 50;
```

### Document's Chunks
```cypher
MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(c:Chunk)
RETURN c.id AS id, c.index AS index, c.token_count AS token_count
ORDER BY index ASC;
```

## Analysis Queries

### Most Connected Entities
```cypher
MATCH (e)-[r]-()
WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding OR e:Definition OR e:Citation
RETURN e.name AS name, labels(e)[0] AS type, count(r) AS degree
ORDER BY degree DESC
LIMIT 20;
```

### Entity Relationship Graph
```cypher
MATCH (e)-[r]->(e2)
WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding OR e:Definition OR e:Citation
RETURN e, r, e2
LIMIT 200;
```

### Documents Without Entities
```cypher
MATCH (d:Document)
WHERE NOT (d)-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS_ENTITY]->()
RETURN d.id AS id;
```

### Orphaned Entities
```cypher
MATCH (e)
WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding OR e:Definition OR e:Citation)
AND NOT (e)<-[:CONTAINS_ENTITY]-(:Chunk)
RETURN e.id AS id, e.name AS name, labels(e)[0] AS type;
```

## Data Quality Queries

### Entities Without Definitions
```cypher
MATCH (e)
WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding OR e:Definition OR e:Citation)
AND (e.definition IS NULL OR trim(e.definition) = "")
RETURN e.id AS id, e.name AS name, labels(e)[0] AS type;
```

### Chunks Without Embeddings
```cypher
MATCH (c:Chunk)
WHERE c.embedding IS NULL OR size(c.embedding) = 0
RETURN c.id AS id;
```

### Duplicate Entities
```cypher
MATCH (e)
WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding OR e:Definition OR e:Citation
WITH e.name AS name, collect(e) AS nodes
WHERE size(nodes) > 1
RETURN name, [n IN nodes | n.id] AS ids;
```

## Cleanup Queries

### Delete Specific Document and Related Nodes
```cypher
MATCH (d:Document {id: $doc_id})
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
DETACH DELETE d, c;
```

### Delete All Test Documents
```cypher
MATCH (d:Document)
WHERE d.id STARTS WITH "test_doc_"
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
DETACH DELETE d, c;
```

### Clear Entire Database (DANGEROUS!)
```cypher
MATCH (n)
DETACH DELETE n;
```

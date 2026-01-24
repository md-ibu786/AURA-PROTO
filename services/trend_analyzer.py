# trend_analyzer.py
# Service for analyzing concept trends and evolution across the knowledge graph

# Provides trend analysis capabilities for tracking concept frequency, emergence,
# and evolution across modules and time periods. Enables staff to understand how
# concepts develop across semesters, identify emerging topics, and track knowledge
# progression. Uses Neo4j graph queries with Redis caching for performance.

# @see: api/graph_manager.py - Graph operations and entity traversal
# @see: api/neo4j_config.py - Neo4j driver configuration
# @see: api/cache.py - Redis caching for computed results
# @note: Gracefully degrades when Neo4j or cache unavailable

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Cache configuration for trend analysis
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours (shorter than summaries due to dynamic data)
CACHE_PREFIX_FREQUENCY = "trend:freq"
CACHE_PREFIX_TRENDING = "trend:trending"
CACHE_PREFIX_EMERGING = "trend:emerging"
CACHE_PREFIX_OVERLAP = "trend:overlap"
CACHE_PREFIX_EVOLUTION = "trend:evolution"
CACHE_PREFIX_COMPARISON = "trend:compare"

# Default limits
DEFAULT_CONCEPT_LIMIT = 100
DEFAULT_TRENDING_LIMIT = 20
DEFAULT_EMERGING_LIMIT = 20
MAX_MODULES_FOR_OVERLAP = 10


# ============================================================================
# DATA MODELS
# ============================================================================


class TimeRange(BaseModel):
    """Time range specification for trend analysis."""

    start: datetime = Field(description="Start of the time range")
    end: datetime = Field(description="End of the time range")
    granularity: Literal["day", "week", "month", "semester"] = Field(
        default="month",
        description="Time granularity for aggregation",
    )


class ConceptFrequency(BaseModel):
    """Concept frequency distribution across modules."""

    concepts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of concepts with name, type, count, and modules",
    )
    total_concepts: int = Field(
        default=0,
        description="Total number of unique concepts",
    )
    by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Concept count by entity type (Topic, Concept, etc.)",
    )
    by_module: Dict[str, int] = Field(
        default_factory=dict,
        description="Concept count by module ID",
    )


class TrendingConcept(BaseModel):
    """A concept showing increasing frequency over time."""

    name: str = Field(description="Concept name")
    type: str = Field(description="Entity type (Topic, Concept, etc.)")
    current_frequency: int = Field(
        ge=0,
        description="Frequency in the current period",
    )
    previous_frequency: int = Field(
        ge=0,
        description="Frequency in the previous period",
    )
    growth_rate: float = Field(
        description="Growth rate: (current - previous) / previous",
    )
    modules: List[str] = Field(
        default_factory=list,
        description="Modules where concept appears",
    )
    first_seen: Optional[datetime] = Field(
        default=None,
        description="When the concept was first seen",
    )


class EmergingConcept(BaseModel):
    """A newly appearing concept in the knowledge graph."""

    name: str = Field(description="Concept name")
    type: str = Field(description="Entity type (Topic, Concept, etc.)")
    first_seen: datetime = Field(description="When the concept was first seen")
    module_id: str = Field(description="Module where concept first appeared")
    document_id: Optional[str] = Field(
        default=None,
        description="Document where concept first appeared",
    )
    mention_count: int = Field(
        ge=1,
        description="Number of mentions since emergence",
    )
    related_concepts: List[str] = Field(
        default_factory=list,
        description="Related concepts in the graph",
    )


class CrossModuleAnalysis(BaseModel):
    """Analysis of concept overlap between modules."""

    modules: List[str] = Field(
        description="List of modules analyzed",
    )
    shared_concepts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Concepts appearing in 2+ modules",
    )
    unique_concepts: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Module -> list of unique concepts",
    )
    overlap_matrix: List[List[float]] = Field(
        default_factory=list,
        description="Jaccard similarity matrix between modules",
    )
    bridging_concepts: List[str] = Field(
        default_factory=list,
        description="Concepts connecting multiple modules",
    )


class ConceptEvolution(BaseModel):
    """Evolution of a concept over time."""

    concept_name: str = Field(description="Name of the concept being tracked")
    timeline: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Timeline data: [{date, frequency, modules, contexts}]",
    )
    related_concept_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Changes in related concepts over time",
    )
    definition_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Changes in concept definition over time",
    )


class ModuleComparison(BaseModel):
    """Comparison of concepts between two modules."""

    module_a: str = Field(description="First module ID")
    module_b: str = Field(description="Second module ID")
    shared_concepts: List[str] = Field(
        default_factory=list,
        description="Concepts appearing in both modules",
    )
    unique_to_a: List[str] = Field(
        default_factory=list,
        description="Concepts only in module A",
    )
    unique_to_b: List[str] = Field(
        default_factory=list,
        description="Concepts only in module B",
    )
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Jaccard similarity between modules",
    )
    concept_alignment: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Same concepts with different definitions",
    )


# ============================================================================
# TREND ANALYZER CLASS
# ============================================================================


class TrendAnalyzer:
    """
    Service for analyzing concept trends and evolution in the knowledge graph.

    Provides methods for:
    - Concept frequency distribution across modules
    - Trending concept detection (growth rate analysis)
    - Emerging concept identification (newly appearing)
    - Cross-module overlap analysis
    - Concept evolution tracking over time
    - Module concept comparison

    Example:
        from services.trend_analyzer import TrendAnalyzer
        from api.neo4j_config import neo4j_driver

        analyzer = TrendAnalyzer(neo4j_driver)

        # Get concept frequency
        freq = await analyzer.get_concept_frequency(module_ids=["CS101"])

        # Find trending concepts
        time_range = TimeRange(
            start=datetime(2025, 1, 1),
            end=datetime(2025, 6, 30),
        )
        trending = await analyzer.get_trending_concepts(time_range)
    """

    def __init__(self, neo4j_driver=None, cache_client=None):
        """
        Initialize TrendAnalyzer.

        Args:
            neo4j_driver: Neo4j driver instance (optional, auto-imports if None)
            cache_client: Redis cache client (optional, auto-imports if None)
        """
        self._neo4j_driver = neo4j_driver
        self._cache = cache_client
        logger.info("TrendAnalyzer initialized")

    def _get_driver(self):
        """Get or initialize Neo4j driver."""
        if self._neo4j_driver is None:
            try:
                from api.neo4j_config import neo4j_driver

                self._neo4j_driver = neo4j_driver
            except ImportError:
                try:
                    from neo4j_config import neo4j_driver

                    self._neo4j_driver = neo4j_driver
                except ImportError:
                    logger.warning("Neo4j driver not available")
                    return None
        return self._neo4j_driver

    def _get_cache(self):
        """Get or initialize cache client."""
        if self._cache is None:
            try:
                from api.cache import redis_client

                self._cache = redis_client
            except ImportError:
                try:
                    from cache import redis_client

                    self._cache = redis_client
                except ImportError:
                    logger.debug("Cache not available")
                    return None
        return self._cache

    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments."""
        key_parts = [str(arg) for arg in args if arg is not None]
        key_content = ":".join(key_parts)
        content_hash = hashlib.md5(key_content.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}:{content_hash}"

    async def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached result if available."""
        cache = self._get_cache()
        if cache is None:
            return None
        try:
            return cache.get(cache_key)
        except Exception as e:
            logger.debug(f"Cache get failed: {e}")
            return None

    def _set_cached(
        self,
        cache_key: str,
        data: Dict[str, Any],
        ttl: int = CACHE_TTL_SECONDS,
    ) -> bool:
        """Store result in cache."""
        cache = self._get_cache()
        if cache is None:
            return False
        try:
            return cache.set(cache_key, data, ttl=ttl)
        except Exception as e:
            logger.debug(f"Cache set failed: {e}")
            return False

    # ========================================================================
    # CONCEPT FREQUENCY
    # ========================================================================

    async def get_concept_frequency(
        self,
        module_ids: Optional[List[str]] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = DEFAULT_CONCEPT_LIMIT,
    ) -> ConceptFrequency:
        """
        Get concept frequency distribution across modules.

        Args:
            module_ids: Optional list of module IDs to filter by
            entity_types: Optional list of entity types (Topic, Concept, etc.)
            limit: Maximum concepts to return (default: 100)

        Returns:
            ConceptFrequency with concepts, counts, and distributions
        """
        logger.info(
            f"Getting concept frequency: modules={module_ids}, types={entity_types}"
        )

        # Check cache
        cache_key = self._generate_cache_key(
            CACHE_PREFIX_FREQUENCY,
            str(module_ids),
            str(entity_types),
            limit,
        )
        cached = await self._get_cached(cache_key)
        if cached:
            return ConceptFrequency(**cached)

        driver = self._get_driver()
        if driver is None:
            logger.warning("Neo4j driver not available for concept frequency")
            return ConceptFrequency(
                concepts=[],
                total_concepts=0,
                by_type={},
                by_module={},
            )

        try:
            # Build Cypher query with filters
            where_clauses = ["(e:Topic OR e:Concept OR e:Methodology OR e:Finding)"]
            params: Dict[str, Any] = {"limit": limit}

            if module_ids:
                where_clauses.append("e.module_id IN $module_ids")
                params["module_ids"] = module_ids

            if entity_types:
                type_conditions = " OR ".join([f"e:{t}" for t in entity_types])
                where_clauses.append(f"({type_conditions})")

            where_clause = " AND ".join(where_clauses)

            cypher = f"""
            MATCH (e)
            WHERE {where_clause}
            WITH e.name as name, labels(e)[0] as type,
                 count(*) as count, collect(DISTINCT e.module_id) as modules
            RETURN name, type, count, modules
            ORDER BY count DESC
            LIMIT $limit
            """

            concepts = []
            by_type: Dict[str, int] = {}
            by_module: Dict[str, int] = {}

            with driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    concept = {
                        "name": record["name"],
                        "type": record["type"],
                        "count": record["count"],
                        "modules": record["modules"],
                    }
                    concepts.append(concept)

                    # Aggregate by type
                    entity_type = record["type"]
                    by_type[entity_type] = by_type.get(entity_type, 0) + 1

                    # Aggregate by module
                    for mod_id in record["modules"]:
                        if mod_id:
                            by_module[mod_id] = by_module.get(mod_id, 0) + 1

            frequency = ConceptFrequency(
                concepts=concepts,
                total_concepts=len(concepts),
                by_type=by_type,
                by_module=by_module,
            )

            # Cache result
            self._set_cached(cache_key, frequency.model_dump())

            logger.info(f"Concept frequency: found {len(concepts)} concepts")
            return frequency

        except Exception as e:
            logger.error(f"Concept frequency query failed: {e}")
            return ConceptFrequency(
                concepts=[],
                total_concepts=0,
                by_type={},
                by_module={},
            )

    # ========================================================================
    # TRENDING CONCEPTS
    # ========================================================================

    async def get_trending_concepts(
        self,
        time_range: TimeRange,
        min_growth_rate: float = 0.2,
        limit: int = DEFAULT_TRENDING_LIMIT,
    ) -> List[TrendingConcept]:
        """
        Find concepts with increasing frequency over time.

        Compares concept frequency between current and previous period
        of equal length to calculate growth rate.

        Args:
            time_range: Current period to analyze
            min_growth_rate: Minimum growth rate to include (default: 0.2 = 20%)
            limit: Maximum trending concepts to return

        Returns:
            List of TrendingConcept objects sorted by growth rate
        """
        logger.info(
            f"Getting trending concepts: {time_range.start} to {time_range.end}"
        )

        # Check cache
        cache_key = self._generate_cache_key(
            CACHE_PREFIX_TRENDING,
            time_range.start.isoformat(),
            time_range.end.isoformat(),
            min_growth_rate,
            limit,
        )
        cached = await self._get_cached(cache_key)
        if cached:
            return [TrendingConcept(**c) for c in cached]

        driver = self._get_driver()
        if driver is None:
            logger.warning("Neo4j driver not available for trending concepts")
            return []

        try:
            # Calculate previous period (same duration, immediately before)
            duration = time_range.end - time_range.start
            previous_start = time_range.start - duration
            previous_end = time_range.start

            cypher = """
            // Current period frequency
            MATCH (e)
            WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            AND e.created_at >= $current_start AND e.created_at < $current_end
            WITH e.name as name, labels(e)[0] as type,
                 count(*) as current_count,
                 collect(DISTINCT e.module_id) as modules,
                 min(e.created_at) as first_seen
            
            // Previous period frequency
            OPTIONAL MATCH (e2)
            WHERE (e2:Topic OR e2:Concept OR e2:Methodology OR e2:Finding)
            AND e2.name = name
            AND e2.created_at >= $previous_start AND e2.created_at < $previous_end
            WITH name, type, current_count, modules, first_seen,
                 count(e2) as previous_count
            
            WHERE previous_count > 0
            WITH name, type, current_count, previous_count, modules, first_seen,
                 toFloat(current_count - previous_count) / previous_count as growth_rate
            WHERE growth_rate >= $min_growth_rate
            RETURN name, type, current_count, previous_count, growth_rate,
                   modules, first_seen
            ORDER BY growth_rate DESC
            LIMIT $limit
            """

            params = {
                "current_start": time_range.start.isoformat(),
                "current_end": time_range.end.isoformat(),
                "previous_start": previous_start.isoformat(),
                "previous_end": previous_end.isoformat(),
                "min_growth_rate": min_growth_rate,
                "limit": limit,
            }

            trending = []
            with driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    first_seen = record.get("first_seen")
                    if first_seen and isinstance(first_seen, str):
                        first_seen = datetime.fromisoformat(first_seen)

                    trending.append(
                        TrendingConcept(
                            name=record["name"],
                            type=record["type"],
                            current_frequency=record["current_count"],
                            previous_frequency=record["previous_count"],
                            growth_rate=round(record["growth_rate"], 4),
                            modules=record["modules"] or [],
                            first_seen=first_seen,
                        )
                    )

            # Cache result
            self._set_cached(cache_key, [t.model_dump() for t in trending])

            logger.info(f"Trending concepts: found {len(trending)} concepts")
            return trending

        except Exception as e:
            logger.error(f"Trending concepts query failed: {e}")
            return []

    # ========================================================================
    # EMERGING CONCEPTS
    # ========================================================================

    async def get_emerging_concepts(
        self,
        since: datetime,
        module_ids: Optional[List[str]] = None,
        limit: int = DEFAULT_EMERGING_LIMIT,
    ) -> List[EmergingConcept]:
        """
        Find newly appearing concepts since a given date.

        Args:
            since: Date to look for new concepts from
            module_ids: Optional list of module IDs to filter
            limit: Maximum concepts to return

        Returns:
            List of EmergingConcept objects sorted by first_seen date
        """
        logger.info(f"Getting emerging concepts since {since}")

        # Check cache
        cache_key = self._generate_cache_key(
            CACHE_PREFIX_EMERGING,
            since.isoformat(),
            str(module_ids),
            limit,
        )
        cached = await self._get_cached(cache_key)
        if cached:
            return [EmergingConcept(**c) for c in cached]

        driver = self._get_driver()
        if driver is None:
            logger.warning("Neo4j driver not available for emerging concepts")
            return []

        try:
            # Build module filter
            module_filter = ""
            params: Dict[str, Any] = {
                "since": since.isoformat(),
                "limit": limit,
            }
            if module_ids:
                module_filter = "AND e.module_id IN $module_ids"
                params["module_ids"] = module_ids

            cypher = f"""
            // Find concepts first appearing after the given date
            MATCH (e)
            WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            AND e.created_at >= $since
            {module_filter}
            WITH e.name as name, labels(e)[0] as type,
                 min(e.created_at) as first_seen,
                 collect(e.module_id)[0] as module_id,
                 collect(e.document_id)[0] as document_id,
                 count(*) as mention_count
            
            // Verify this is truly a new concept (not seen before)
            OPTIONAL MATCH (older)
            WHERE (older:Topic OR older:Concept OR older:Methodology OR older:Finding)
            AND older.name = name
            AND older.created_at < $since
            WITH name, type, first_seen, module_id, document_id, mention_count,
                 count(older) as older_count
            WHERE older_count = 0
            
            // Get related concepts
            OPTIONAL MATCH (e2)-[r]-(related)
            WHERE e2.name = name
            AND (related:Topic OR related:Concept OR related:Methodology OR related:Finding)
            WITH name, type, first_seen, module_id, document_id, mention_count,
                 collect(DISTINCT related.name)[..5] as related_concepts
            
            RETURN name, type, first_seen, module_id, document_id,
                   mention_count, related_concepts
            ORDER BY first_seen DESC
            LIMIT $limit
            """

            emerging = []
            with driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    first_seen = record["first_seen"]
                    if isinstance(first_seen, str):
                        first_seen = datetime.fromisoformat(first_seen)
                    elif first_seen is None:
                        first_seen = since

                    emerging.append(
                        EmergingConcept(
                            name=record["name"],
                            type=record["type"],
                            first_seen=first_seen,
                            module_id=record["module_id"] or "",
                            document_id=record.get("document_id"),
                            mention_count=record["mention_count"],
                            related_concepts=record["related_concepts"] or [],
                        )
                    )

            # Cache result
            self._set_cached(cache_key, [e.model_dump() for e in emerging])

            logger.info(f"Emerging concepts: found {len(emerging)} concepts")
            return emerging

        except Exception as e:
            logger.error(f"Emerging concepts query failed: {e}")
            return []

    # ========================================================================
    # CROSS-MODULE OVERLAP
    # ========================================================================

    async def get_cross_module_overlap(
        self,
        module_ids: List[str],
    ) -> CrossModuleAnalysis:
        """
        Analyze concept overlap between multiple modules.

        Identifies shared concepts, unique concepts per module,
        and calculates Jaccard similarity matrix.

        Args:
            module_ids: List of module IDs to analyze (2-10 modules)

        Returns:
            CrossModuleAnalysis with overlap metrics
        """
        if len(module_ids) < 2:
            logger.warning("Cross-module overlap requires at least 2 modules")
            return CrossModuleAnalysis(
                modules=module_ids,
                shared_concepts=[],
                unique_concepts={},
                overlap_matrix=[],
                bridging_concepts=[],
            )

        # Limit modules for performance
        module_ids = module_ids[:MAX_MODULES_FOR_OVERLAP]

        logger.info(f"Analyzing cross-module overlap: {module_ids}")

        # Check cache
        cache_key = self._generate_cache_key(
            CACHE_PREFIX_OVERLAP,
            ",".join(sorted(module_ids)),
        )
        cached = await self._get_cached(cache_key)
        if cached:
            return CrossModuleAnalysis(**cached)

        driver = self._get_driver()
        if driver is None:
            logger.warning("Neo4j driver not available for cross-module overlap")
            return CrossModuleAnalysis(
                modules=module_ids,
                shared_concepts=[],
                unique_concepts={},
                overlap_matrix=[],
                bridging_concepts=[],
            )

        try:
            # Get concepts per module
            concepts_by_module: Dict[str, set] = {m: set() for m in module_ids}
            concept_details: Dict[str, Dict[str, Any]] = {}

            cypher_concepts = """
            MATCH (e)
            WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            AND e.module_id IN $module_ids
            RETURN e.name as name, labels(e)[0] as type,
                   e.module_id as module_id, e.definition as definition
            """

            with driver.session() as session:
                result = session.run(cypher_concepts, {"module_ids": module_ids})
                for record in result:
                    name = record["name"]
                    module_id = record["module_id"]
                    if module_id in concepts_by_module:
                        concepts_by_module[module_id].add(name)
                        if name not in concept_details:
                            concept_details[name] = {
                                "name": name,
                                "type": record["type"],
                                "definitions": {},
                                "modules": [],
                            }
                        concept_details[name]["modules"].append(module_id)
                        if record["definition"]:
                            concept_details[name]["definitions"][module_id] = record[
                                "definition"
                            ]

            # Calculate shared vs unique concepts
            all_concepts = set()
            for concepts in concepts_by_module.values():
                all_concepts.update(concepts)

            shared_concepts = []
            unique_concepts: Dict[str, List[str]] = {m: [] for m in module_ids}
            bridging_concepts = []

            for name in all_concepts:
                modules_with_concept = [
                    m for m in module_ids if name in concepts_by_module[m]
                ]
                if len(modules_with_concept) > 1:
                    detail = concept_details.get(name, {})
                    shared_concepts.append(
                        {
                            "name": name,
                            "type": detail.get("type", "Unknown"),
                            "modules": modules_with_concept,
                            "definitions": detail.get("definitions", {}),
                        }
                    )
                    if len(modules_with_concept) >= len(module_ids) // 2:
                        bridging_concepts.append(name)
                elif len(modules_with_concept) == 1:
                    unique_concepts[modules_with_concept[0]].append(name)

            # Calculate Jaccard similarity matrix
            overlap_matrix = []
            for i, mod_a in enumerate(module_ids):
                row = []
                for j, mod_b in enumerate(module_ids):
                    if i == j:
                        row.append(1.0)
                    else:
                        set_a = concepts_by_module[mod_a]
                        set_b = concepts_by_module[mod_b]
                        intersection = len(set_a & set_b)
                        union = len(set_a | set_b)
                        similarity = intersection / union if union > 0 else 0.0
                        row.append(round(similarity, 4))
                overlap_matrix.append(row)

            analysis = CrossModuleAnalysis(
                modules=module_ids,
                shared_concepts=shared_concepts,
                unique_concepts=unique_concepts,
                overlap_matrix=overlap_matrix,
                bridging_concepts=bridging_concepts,
            )

            # Cache result
            self._set_cached(cache_key, analysis.model_dump())

            logger.info(
                f"Cross-module overlap: {len(shared_concepts)} shared, "
                f"{len(bridging_concepts)} bridging concepts"
            )
            return analysis

        except Exception as e:
            logger.error(f"Cross-module overlap query failed: {e}")
            return CrossModuleAnalysis(
                modules=module_ids,
                shared_concepts=[],
                unique_concepts={},
                overlap_matrix=[],
                bridging_concepts=[],
            )

    # ========================================================================
    # CONCEPT EVOLUTION
    # ========================================================================

    async def get_concept_evolution(
        self,
        concept_name: str,
        time_range: Optional[TimeRange] = None,
    ) -> ConceptEvolution:
        """
        Track how a concept evolved over time.

        Analyzes concept frequency, module appearances, and definition
        changes across time periods.

        Args:
            concept_name: Name of the concept to track
            time_range: Optional time range (defaults to last 12 months)

        Returns:
            ConceptEvolution with timeline and change data
        """
        logger.info(f"Getting concept evolution for: {concept_name}")

        # Default time range: last 12 months
        if time_range is None:
            time_range = TimeRange(
                start=datetime.utcnow() - timedelta(days=365),
                end=datetime.utcnow(),
                granularity="month",
            )

        # Check cache
        cache_key = self._generate_cache_key(
            CACHE_PREFIX_EVOLUTION,
            concept_name,
            time_range.start.isoformat(),
            time_range.end.isoformat(),
            time_range.granularity,
        )
        cached = await self._get_cached(cache_key)
        if cached:
            return ConceptEvolution(**cached)

        driver = self._get_driver()
        if driver is None:
            logger.warning("Neo4j driver not available for concept evolution")
            return ConceptEvolution(
                concept_name=concept_name,
                timeline=[],
                related_concept_changes=[],
                definition_changes=[],
            )

        try:
            # Get concept occurrences over time
            cypher_timeline = """
            MATCH (e)
            WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            AND toLower(e.name) = toLower($concept_name)
            AND e.created_at >= $start AND e.created_at < $end
            RETURN e.created_at as created_at, e.module_id as module_id,
                   e.definition as definition, e.document_id as document_id
            ORDER BY e.created_at
            """

            params = {
                "concept_name": concept_name,
                "start": time_range.start.isoformat(),
                "end": time_range.end.isoformat(),
            }

            timeline: List[Dict[str, Any]] = []
            definitions_seen: Dict[str, datetime] = {}

            with driver.session() as session:
                result = session.run(cypher_timeline, params)
                occurrences = list(result)

                # Group by time period based on granularity
                period_data: Dict[str, Dict[str, Any]] = {}
                for record in occurrences:
                    created_at = record["created_at"]
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)

                    # Determine period key based on granularity
                    if time_range.granularity == "day":
                        period_key = created_at.strftime("%Y-%m-%d")
                    elif time_range.granularity == "week":
                        week_start = created_at - timedelta(days=created_at.weekday())
                        period_key = week_start.strftime("%Y-%m-%d")
                    elif time_range.granularity == "semester":
                        semester = "H1" if created_at.month <= 6 else "H2"
                        period_key = f"{created_at.year}-{semester}"
                    else:  # month
                        period_key = created_at.strftime("%Y-%m")

                    if period_key not in period_data:
                        period_data[period_key] = {
                            "date": period_key,
                            "frequency": 0,
                            "modules": set(),
                            "contexts": [],
                        }

                    period_data[period_key]["frequency"] += 1
                    if record["module_id"]:
                        period_data[period_key]["modules"].add(record["module_id"])

                    # Track definition changes
                    definition = record.get("definition")
                    if definition and definition not in definitions_seen:
                        definitions_seen[definition] = created_at

                # Convert to list
                for period_key in sorted(period_data.keys()):
                    data = period_data[period_key]
                    timeline.append(
                        {
                            "date": data["date"],
                            "frequency": data["frequency"],
                            "modules": list(data["modules"]),
                            "contexts": data["contexts"][:3],
                        }
                    )

            # Build definition changes list
            definition_changes = []
            for definition, first_seen in sorted(
                definitions_seen.items(), key=lambda x: x[1]
            ):
                definition_changes.append(
                    {
                        "definition": definition[:200],
                        "first_seen": first_seen.isoformat(),
                    }
                )

            # Get related concept changes (simplified)
            related_concept_changes: List[Dict[str, Any]] = []

            evolution = ConceptEvolution(
                concept_name=concept_name,
                timeline=timeline,
                related_concept_changes=related_concept_changes,
                definition_changes=definition_changes,
            )

            # Cache result
            self._set_cached(cache_key, evolution.model_dump())

            logger.info(
                f"Concept evolution: {len(timeline)} periods, "
                f"{len(definition_changes)} definition changes"
            )
            return evolution

        except Exception as e:
            logger.error(f"Concept evolution query failed: {e}")
            return ConceptEvolution(
                concept_name=concept_name,
                timeline=[],
                related_concept_changes=[],
                definition_changes=[],
            )

    # ========================================================================
    # MODULE COMPARISON
    # ========================================================================

    async def get_module_comparison(
        self,
        module_id_a: str,
        module_id_b: str,
    ) -> ModuleComparison:
        """
        Compare concepts between two modules.

        Identifies shared and unique concepts, calculates similarity,
        and highlights concept definition differences.

        Args:
            module_id_a: First module ID
            module_id_b: Second module ID

        Returns:
            ModuleComparison with comparison metrics
        """
        logger.info(f"Comparing modules: {module_id_a} vs {module_id_b}")

        # Check cache
        cache_key = self._generate_cache_key(
            CACHE_PREFIX_COMPARISON,
            module_id_a,
            module_id_b,
        )
        cached = await self._get_cached(cache_key)
        if cached:
            return ModuleComparison(**cached)

        driver = self._get_driver()
        if driver is None:
            logger.warning("Neo4j driver not available for module comparison")
            return ModuleComparison(
                module_a=module_id_a,
                module_b=module_id_b,
                shared_concepts=[],
                unique_to_a=[],
                unique_to_b=[],
                similarity_score=0.0,
                concept_alignment=[],
            )

        try:
            # Get concepts and definitions for each module
            cypher = """
            MATCH (e)
            WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            AND e.module_id IN [$module_a, $module_b]
            RETURN e.name as name, e.module_id as module_id,
                   e.definition as definition, labels(e)[0] as type
            """

            concepts_a: Dict[str, str] = {}  # name -> definition
            concepts_b: Dict[str, str] = {}

            with driver.session() as session:
                result = session.run(
                    cypher,
                    {"module_a": module_id_a, "module_b": module_id_b},
                )
                for record in result:
                    name = record["name"]
                    module_id = record["module_id"]
                    definition = record.get("definition") or ""

                    if module_id == module_id_a:
                        concepts_a[name] = definition
                    elif module_id == module_id_b:
                        concepts_b[name] = definition

            # Calculate shared and unique
            set_a = set(concepts_a.keys())
            set_b = set(concepts_b.keys())

            shared = list(set_a & set_b)
            unique_to_a = list(set_a - set_b)
            unique_to_b = list(set_b - set_a)

            # Jaccard similarity
            union = set_a | set_b
            similarity = len(set_a & set_b) / len(union) if union else 0.0

            # Find concept alignment (same name, different definitions)
            concept_alignment = []
            for name in shared:
                def_a = concepts_a.get(name, "")
                def_b = concepts_b.get(name, "")
                if def_a and def_b and def_a != def_b:
                    concept_alignment.append(
                        {
                            "name": name,
                            "definition_a": def_a[:200],
                            "definition_b": def_b[:200],
                        }
                    )

            comparison = ModuleComparison(
                module_a=module_id_a,
                module_b=module_id_b,
                shared_concepts=shared,
                unique_to_a=unique_to_a,
                unique_to_b=unique_to_b,
                similarity_score=round(similarity, 4),
                concept_alignment=concept_alignment,
            )

            # Cache result
            self._set_cached(cache_key, comparison.model_dump())

            logger.info(
                f"Module comparison: {len(shared)} shared, similarity={similarity:.2%}"
            )
            return comparison

        except Exception as e:
            logger.error(f"Module comparison query failed: {e}")
            return ModuleComparison(
                module_a=module_id_a,
                module_b=module_id_b,
                shared_concepts=[],
                unique_to_a=[],
                unique_to_b=[],
                similarity_score=0.0,
                concept_alignment=[],
            )


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_trend_analyzer(
    neo4j_driver=None,
    cache_client=None,
) -> TrendAnalyzer:
    """
    Factory function to create TrendAnalyzer.

    Args:
        neo4j_driver: Optional Neo4j driver (auto-imports if None)
        cache_client: Optional Redis cache client (auto-imports if None)

    Returns:
        Configured TrendAnalyzer instance
    """
    return TrendAnalyzer(
        neo4j_driver=neo4j_driver,
        cache_client=cache_client,
    )

# trends.py
# FastAPI router for trend analysis endpoints

# Provides REST API endpoints for concept trend analysis including frequency
# distribution, trending concepts, emerging concepts, cross-module overlap,
# concept evolution, and module comparison. Uses TrendAnalyzer service with
# Redis caching for performance.

# @see: services/trend_analyzer.py - TrendAnalyzer for trend analysis logic
# @see: api/routers/summaries.py - Pattern reference for router structure
# @see: api/cache.py - Redis caching for computed results
# @note: Computation-heavy endpoints may take time on first request

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.trend_analyzer import (
    ConceptEvolution,
    ConceptFrequency,
    CrossModuleAnalysis,
    EmergingConcept,
    ModuleComparison,
    TimeRange,
    TrendAnalyzer,
    TrendingConcept,
)


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/v1/trends", tags=["Trends"])


# ============================================================================
# SCHEMAS
# ============================================================================


class ModuleOverlapRequest(BaseModel):
    """Request body for cross-module overlap analysis."""

    module_ids: List[str] = Field(
        ...,
        min_length=2,
        max_length=10,
        description="List of module IDs to analyze (2-10 modules)",
    )


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_trend_analyzer() -> TrendAnalyzer:
    """
    Dependency to get TrendAnalyzer instance.

    Creates a new TrendAnalyzer with the global Neo4j driver.

    Returns:
        TrendAnalyzer: Configured trend analyzer instance.
    """
    try:
        from api.neo4j_config import neo4j_driver
    except ImportError:
        try:
            from neo4j_config import neo4j_driver
        except ImportError:
            neo4j_driver = None

    try:
        from api.cache import redis_client
    except ImportError:
        try:
            from cache import redis_client
        except ImportError:
            redis_client = None

    return TrendAnalyzer(neo4j_driver=neo4j_driver, cache_client=redis_client)


# ============================================================================
# CONCEPT FREQUENCY ENDPOINTS
# ============================================================================


@router.get("/concepts/frequency", response_model=ConceptFrequency)
async def get_concept_frequency(
    module_ids: Optional[List[str]] = Query(
        None,
        description="Optional list of module IDs to filter by",
    ),
    entity_types: Optional[List[str]] = Query(
        None,
        description="Optional list of entity types (Topic, Concept, Methodology, Finding)",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum number of concepts to return",
    ),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer),
) -> ConceptFrequency:
    """
    Get concept frequency distribution.

    Returns concept frequency counts aggregated by type and module.
    Useful for understanding which concepts are most prevalent.

    Args:
        module_ids: Optional filter by module IDs.
        entity_types: Optional filter by entity types.
        limit: Maximum concepts to return (default: 100).
        trend_analyzer: Injected TrendAnalyzer instance.

    Returns:
        ConceptFrequency with concepts, counts, and distributions.

    Raises:
        HTTPException: 500 for processing errors.
    """
    logger.info(
        f"GET /concepts/frequency: modules={module_ids}, "
        f"types={entity_types}, limit={limit}"
    )

    try:
        result = await trend_analyzer.get_concept_frequency(
            module_ids=module_ids,
            entity_types=entity_types,
            limit=limit,
        )
        return result

    except Exception as e:
        logger.error(f"Concept frequency failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get concept frequency: {str(e)}",
        )


# ============================================================================
# TRENDING CONCEPTS ENDPOINTS
# ============================================================================


@router.get("/concepts/trending", response_model=List[TrendingConcept])
async def get_trending_concepts(
    start_date: datetime = Query(
        ...,
        description="Start date of the period to analyze",
    ),
    end_date: datetime = Query(
        ...,
        description="End date of the period to analyze",
    ),
    min_growth_rate: float = Query(
        0.2,
        ge=0.0,
        le=10.0,
        description="Minimum growth rate to include (0.2 = 20% growth)",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum trending concepts to return",
    ),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer),
) -> List[TrendingConcept]:
    """
    Get concepts with increasing frequency over time.

    Compares concept frequency between the specified period and
    the equivalent previous period to calculate growth rate.

    Args:
        start_date: Start of current period.
        end_date: End of current period.
        min_growth_rate: Minimum growth rate threshold (default: 0.2).
        limit: Maximum concepts to return (default: 20).
        trend_analyzer: Injected TrendAnalyzer instance.

    Returns:
        List of TrendingConcept objects sorted by growth rate.

    Raises:
        HTTPException: 400 for invalid date range, 500 for processing errors.
    """
    logger.info(
        f"GET /concepts/trending: {start_date} to {end_date}, "
        f"min_growth={min_growth_rate}"
    )

    # Validate date range
    if end_date <= start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be after start_date",
        )

    try:
        time_range = TimeRange(
            start=start_date,
            end=end_date,
            granularity="month",
        )

        result = await trend_analyzer.get_trending_concepts(
            time_range=time_range,
            min_growth_rate=min_growth_rate,
            limit=limit,
        )
        return result

    except Exception as e:
        logger.error(f"Trending concepts failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trending concepts: {str(e)}",
        )


# ============================================================================
# EMERGING CONCEPTS ENDPOINTS
# ============================================================================


@router.get("/concepts/emerging", response_model=List[EmergingConcept])
async def get_emerging_concepts(
    since: datetime = Query(
        ...,
        description="Find concepts that first appeared after this date",
    ),
    module_ids: Optional[List[str]] = Query(
        None,
        description="Optional list of module IDs to filter by",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum emerging concepts to return",
    ),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer),
) -> List[EmergingConcept]:
    """
    Get newly appearing concepts.

    Finds concepts that first appeared in the knowledge graph after
    the specified date, indicating new topics being introduced.

    Args:
        since: Date to look for new concepts from.
        module_ids: Optional filter by module IDs.
        limit: Maximum concepts to return (default: 20).
        trend_analyzer: Injected TrendAnalyzer instance.

    Returns:
        List of EmergingConcept objects sorted by first_seen date.

    Raises:
        HTTPException: 500 for processing errors.
    """
    logger.info(f"GET /concepts/emerging: since={since}, modules={module_ids}")

    try:
        result = await trend_analyzer.get_emerging_concepts(
            since=since,
            module_ids=module_ids,
            limit=limit,
        )
        return result

    except Exception as e:
        logger.error(f"Emerging concepts failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get emerging concepts: {str(e)}",
        )


# ============================================================================
# CROSS-MODULE OVERLAP ENDPOINTS
# ============================================================================


@router.post("/modules/overlap", response_model=CrossModuleAnalysis)
async def analyze_module_overlap(
    request: ModuleOverlapRequest = Body(...),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer),
) -> CrossModuleAnalysis:
    """
    Analyze concept overlap between modules.

    Calculates shared concepts, unique concepts per module,
    Jaccard similarity matrix, and identifies bridging concepts.

    Args:
        request: ModuleOverlapRequest with list of module IDs.
        trend_analyzer: Injected TrendAnalyzer instance.

    Returns:
        CrossModuleAnalysis with overlap metrics.

    Raises:
        HTTPException: 400 for invalid request, 500 for processing errors.
    """
    logger.info(f"POST /modules/overlap: modules={request.module_ids}")

    if len(request.module_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 module IDs are required",
        )

    try:
        result = await trend_analyzer.get_cross_module_overlap(
            module_ids=request.module_ids,
        )
        return result

    except Exception as e:
        logger.error(f"Module overlap analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze module overlap: {str(e)}",
        )


# ============================================================================
# CONCEPT EVOLUTION ENDPOINTS
# ============================================================================


@router.get("/concepts/{concept_name}/evolution", response_model=ConceptEvolution)
async def get_concept_evolution(
    concept_name: str,
    start_date: Optional[datetime] = Query(
        None,
        description="Start of time range (defaults to 12 months ago)",
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End of time range (defaults to now)",
    ),
    granularity: Literal["day", "week", "month", "semester"] = Query(
        "month",
        description="Time granularity for aggregation",
    ),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer),
) -> ConceptEvolution:
    """
    Track how a concept evolved over time.

    Returns a timeline of concept frequency, module appearances,
    and definition changes over the specified period.

    Args:
        concept_name: Name of the concept to track.
        start_date: Optional start of time range.
        end_date: Optional end of time range.
        granularity: Time aggregation granularity (day/week/month/semester).
        trend_analyzer: Injected TrendAnalyzer instance.

    Returns:
        ConceptEvolution with timeline and change data.

    Raises:
        HTTPException: 404 if concept not found, 500 for processing errors.
    """
    logger.info(
        f"GET /concepts/{concept_name}/evolution: "
        f"{start_date} to {end_date}, granularity={granularity}"
    )

    try:
        # Build time range if dates provided
        time_range = None
        if start_date or end_date:
            from datetime import timedelta

            now = datetime.utcnow()
            time_range = TimeRange(
                start=start_date or (now - timedelta(days=365)),
                end=end_date or now,
                granularity=granularity,
            )

        result = await trend_analyzer.get_concept_evolution(
            concept_name=concept_name,
            time_range=time_range,
        )

        if not result.timeline:
            raise HTTPException(
                status_code=404,
                detail=f"No evolution data found for concept '{concept_name}'",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Concept evolution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get concept evolution: {str(e)}",
        )


# ============================================================================
# MODULE COMPARISON ENDPOINTS
# ============================================================================


@router.get("/modules/compare", response_model=ModuleComparison)
async def compare_modules(
    module_a: str = Query(
        ...,
        description="First module ID to compare",
    ),
    module_b: str = Query(
        ...,
        description="Second module ID to compare",
    ),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer),
) -> ModuleComparison:
    """
    Compare concepts between two modules.

    Identifies shared and unique concepts, calculates Jaccard similarity,
    and highlights concepts with different definitions across modules.

    Args:
        module_a: First module ID.
        module_b: Second module ID.
        trend_analyzer: Injected TrendAnalyzer instance.

    Returns:
        ModuleComparison with comparison metrics.

    Raises:
        HTTPException: 400 for same module IDs, 500 for processing errors.
    """
    logger.info(f"GET /modules/compare: {module_a} vs {module_b}")

    if module_a == module_b:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a module with itself",
        )

    try:
        result = await trend_analyzer.get_module_comparison(
            module_id_a=module_a,
            module_id_b=module_b,
        )
        return result

    except Exception as e:
        logger.error(f"Module comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare modules: {str(e)}",
        )

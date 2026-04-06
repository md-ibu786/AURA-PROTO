"""
============================================================================
FILE: test_audio_processing_job_store.py
LOCATION: api/tests/test_audio_processing_job_store.py
============================================================================

PURPOSE:
    Unit tests for bounded job_status_store retention behavior in audio_processing.py.
    Tests TTL-based pruning, max-entry eviction, and active job preservation.

ROLE IN PROJECT:
    Regression tests for T-08-04 (Denial of Service mitigation). Ensures that
    terminal audio jobs expire/evict instead of accumulating indefinitely in
    process memory across long-running sessions.

KEY COMPONENTS:
    - test_terminal_jobs_pruned_after_ttl: TTL-based pruning of old terminal jobs
    - test_oldest_terminal_jobs_evicted_on_max_entries: Max-entry cap eviction
    - test_active_jobs_are_not_evicted: Active jobs preserved during cleanup
    - test_pipeline_status_returns_404_for_expired_jobs: Not-found for evicted jobs

DEPENDENCIES:
    - External: pytest, time, unittest.mock
    - Internal: api.audio_processing

USAGE:
    pytest api/tests/test_audio_processing_job_store.py -v
============================================================================
"""

import pytest
import time
import sys
import os
from unittest.mock import patch, MagicMock

# Import audio_processing module directly (same pattern as test_audio_processing.py)
_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

import audio_processing as ap_module


class TestJobStatusStoreTTL:
    """Tests for TTL-based pruning of terminal jobs."""

    def test_terminal_jobs_pruned_after_ttl(self):
        """Test that terminal jobs older than TTL are pruned before new writes."""
        # Get the TTL constant if it exists, otherwise use a default
        ttl_seconds = getattr(ap_module, "JOB_STATUS_TTL_SECONDS", 300)

        # Seed store with an old terminal job
        old_job_id = "old-terminal-job"
        ap_module.job_status_store[old_job_id] = {
            "status": "complete",
            "progress": 100,
            "message": "Done",
            "updated_at": time.time() - (ttl_seconds + 10),
        }

        # Seed store with a recent job
        recent_job_id = "recent-job"
        ap_module.job_status_store[recent_job_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Starting",
            "updated_at": time.time(),
        }

        initial_count = len(ap_module.job_status_store)

        # Trigger cleanup by calling the cleanup function before insert
        if hasattr(ap_module, "_cleanup_job_store"):
            ap_module._cleanup_job_store()

        # Old terminal job should be pruned
        assert old_job_id not in ap_module.job_status_store, (
            "Old terminal job should be pruned after TTL"
        )
        # Recent job should remain
        assert recent_job_id in ap_module.job_status_store, (
            "Recent job should not be pruned"
        )

    def test_active_jobs_not_pruned_by_ttl(self):
        """Test that active jobs are retained even if old."""
        ttl_seconds = getattr(ap_module, "JOB_STATUS_TTL_SECONDS", 300)

        # Seed store with old but active jobs
        active_job_id = "old-active-job"
        ap_module.job_status_store[active_job_id] = {
            "status": "transcribing",
            "progress": 50,
            "message": "Transcribing",
            "updated_at": time.time() - (ttl_seconds + 10),
        }

        # Seed store with a recent terminal job
        terminal_job_id = "recent-terminal"
        ap_module.job_status_store[terminal_job_id] = {
            "status": "complete",
            "progress": 100,
            "message": "Done",
            "updated_at": time.time(),
        }

        # Trigger cleanup
        if hasattr(ap_module, "_cleanup_job_store"):
            ap_module._cleanup_job_store()

        # Active job should be preserved
        assert active_job_id in ap_module.job_status_store, (
            "Active in-flight job should not be pruned even if old"
        )
        # Terminal job should also be present (it's recent)
        assert terminal_job_id in ap_module.job_status_store


class TestJobStatusStoreMaxEntries:
    """Tests for max-entry eviction behavior."""

    def test_oldest_terminal_jobs_evicted_on_max_entries(self):
        """Test that oldest terminal jobs are evicted when store exceeds max cap."""
        max_entries = getattr(ap_module, "JOB_STATUS_MAX_ENTRIES", 100)

        # Seed store with many terminal jobs
        terminal_job_ids = []
        for i in range(max_entries + 10):
            job_id = f"terminal-job-{i}"
            terminal_job_ids.append(job_id)
            ap_module.job_status_store[job_id] = {
                "status": "complete",
                "progress": 100,
                "message": f"Done {i}",
                "updated_at": time.time() - i,
            }

        initial_count = len(ap_module.job_status_store)

        # Trigger cleanup
        if hasattr(ap_module, "_cleanup_job_store"):
            ap_module._cleanup_job_store()

        # Store should be bounded
        assert len(ap_module.job_status_store) <= max_entries, (
            f"Store should not exceed max_entries ({max_entries})"
        )

        # Oldest terminal jobs should be evicted first
        for i in range(10):
            evicted_job_id = f"terminal-job-{i}"
            assert evicted_job_id not in ap_module.job_status_store, (
                f"Oldest terminal job {evicted_job_id} should be evicted"
            )

        # Most recent terminal jobs should remain
        for i in range(max_entries - 1, max_entries - 6, -1):
            remaining_job_id = f"terminal-job-{i}"
            assert remaining_job_id in ap_module.job_status_store, (
                f"Recent terminal job {remaining_job_id} should remain"
            )

    def test_active_jobs_not_evicted_for_max_entries(self):
        """Test that active jobs are preserved when evicting for max cap."""
        max_entries = getattr(ap_module, "JOB_STATUS_MAX_ENTRIES", 100)

        # Clear and seed with active jobs
        ap_module.job_status_store.clear()

        # Add some active jobs
        for i in range(5):
            job_id = f"active-job-{i}"
            ap_module.job_status_store[job_id] = {
                "status": "transcribing",
                "progress": 50,
                "message": f"Transcribing {i}",
                "updated_at": time.time(),
            }

        # Fill rest with old terminal jobs
        for i in range(max_entries + 5):
            job_id = f"old-terminal-{i}"
            ap_module.job_status_store[job_id] = {
                "status": "complete",
                "progress": 100,
                "message": f"Done {i}",
                "updated_at": time.time() - 1000 - i,
            }

        # Trigger cleanup
        if hasattr(ap_module, "_cleanup_job_store"):
            ap_module._cleanup_job_store()

        # Active jobs should all be preserved
        for i in range(5):
            job_id = f"active-job-{i}"
            assert job_id in ap_module.job_status_store, (
                f"Active job {job_id} should not be evicted"
            )


class TestPipelineStatusExpiredJobs:
    """Tests for pipeline-status endpoint behavior with expired/evicted jobs."""

    @pytest.mark.asyncio
    async def test_pipeline_status_returns_404_for_expired_jobs(self):
        """Test that GET pipeline-status returns 404 for legitimately expired jobs."""
        # This test verifies the not-found behavior for evicted/expired jobs

        # Create and then manually remove a job (simulating eviction)
        expired_job_id = "expired-job-123"
        ap_module.job_status_store[expired_job_id] = {
            "status": "complete",
            "progress": 100,
            "message": "Done",
            "updated_at": time.time() - 10000,
        }

        # Simulate the cleanup removing this job
        if hasattr(ap_module, "_cleanup_job_store"):
            ap_module._cleanup_job_store()

        # Job should be evicted
        assert expired_job_id not in ap_module.job_status_store

        # Calling get_pipeline_status should raise 404
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            # Simulate calling get_pipeline_status (async function)
            await ap_module.get_pipeline_status(expired_job_id)

        assert exc_info.value.status_code == 404, (
            "Should return 404 for evicted/expired job"
        )

    @pytest.mark.asyncio
    async def test_pipeline_status_returns_404_for_nonexistent_jobs(self):
        """Test that pipeline-status returns 404 for jobs that never existed."""
        nonexistent_job_id = "nonexistent-job-456"

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await ap_module.get_pipeline_status(nonexistent_job_id)

        assert exc_info.value.status_code == 404


class TestJobStatusStoreConstants:
    """Tests that retention constants are defined."""

    def test_ttl_constant_defined(self):
        """Test that JOB_STATUS_TTL_SECONDS constant exists."""
        assert hasattr(ap_module, "JOB_STATUS_TTL_SECONDS"), (
            "JOB_STATUS_TTL_SECONDS should be defined"
        )
        assert isinstance(ap_module.JOB_STATUS_TTL_SECONDS, (int, float))
        assert ap_module.JOB_STATUS_TTL_SECONDS > 0

    def test_max_entries_constant_defined(self):
        """Test that JOB_STATUS_MAX_ENTRIES constant exists."""
        assert hasattr(ap_module, "JOB_STATUS_MAX_ENTRIES"), (
            "JOB_STATUS_MAX_ENTRIES should be defined"
        )
        assert isinstance(ap_module.JOB_STATUS_MAX_ENTRIES, int)
        assert ap_module.JOB_STATUS_MAX_ENTRIES > 0

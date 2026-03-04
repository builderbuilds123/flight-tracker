"""Health-check probe timeout configuration."""
from __future__ import annotations


# Individual probe timeouts in seconds.
DB_PROBE_TIMEOUT: float = 3.0
REDIS_PROBE_TIMEOUT: float = 2.0
CELERY_PROBE_TIMEOUT: float = 5.0

# Overall readiness budget – if any single probe exceeds this the
# endpoint still returns within a bounded wall-clock time.
READINESS_TIMEOUT: float = 8.0

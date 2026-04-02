# utils/metrics.py
"""
Performance monitoring and metrics collection for the application.
Tracks query latency, cache hit rates, and database performance.
"""

import time
import threading
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class MetricPoint:
    """Single performance metric data point"""
    timestamp: float
    duration_ms: float
    success: bool
    details: Optional[Dict] = None


class PerformanceMetrics:
    """
    Thread-safe performance metrics collector.
    Tracks latencies, success rates, and cache statistics.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # Query latencies
        self._query_latencies: List[float] = []
        
        # Cache statistics
        self._cache_stats = defaultdict(lambda: {"hits": 0, "misses": 0})
        
        # Endpoint statistics
        self._endpoint_stats = defaultdict(lambda: {
            "count": 0,
            "total_time_ms": 0,
            "errors": 0,
            "latencies": []
        })
        
        # Database query statistics
        self._db_query_stats = {
            "count": 0,
            "total_time_ms": 0,
            "latencies": []
        }
        
        # Vector search statistics
        self._vector_search_stats = {
            "count": 0,
            "total_time_ms": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Start time
        self._start_time = time.time()
    
    def record_query(self, endpoint: str, duration_ms: float, success: bool = True):
        """Record a query execution"""
        with self._lock:
            self._query_latencies.append(duration_ms)
            
            stats = self._endpoint_stats[endpoint]
            stats["count"] += 1
            stats["total_time_ms"] += duration_ms
            stats["latencies"].append(duration_ms)
            
            if not success:
                stats["errors"] += 1
            
            # Keep only last 1000 latencies per endpoint
            if len(stats["latencies"]) > 1000:
                stats["latencies"] = stats["latencies"][-1000:]
    
    def record_cache_hit(self, cache_name: str):
        """Record a cache hit"""
        with self._lock:
            self._cache_stats[cache_name]["hits"] += 1
    
    def record_cache_miss(self, cache_name: str):
        """Record a cache miss"""
        with self._lock:
            self._cache_stats[cache_name]["misses"] += 1
    
    def record_db_query(self, duration_ms: float):
        """Record a database query"""
        with self._lock:
            self._db_query_stats["count"] += 1
            self._db_query_stats["total_time_ms"] += duration_ms
            self._db_query_stats["latencies"].append(duration_ms)
            
            # Keep only last 1000 latencies
            if len(self._db_query_stats["latencies"]) > 1000:
                self._db_query_stats["latencies"] = self._db_query_stats["latencies"][-1000:]
    
    def record_vector_search(self, duration_ms: float, cache_hit: bool):
        """Record a vector search operation"""
        with self._lock:
            self._vector_search_stats["count"] += 1
            self._vector_search_stats["total_time_ms"] += duration_ms
            
            if cache_hit:
                self._vector_search_stats["cache_hits"] += 1
            else:
                self._vector_search_stats["cache_misses"] += 1
    
    def get_cache_hit_rate(self, cache_name: str) -> float:
        """Calculate cache hit rate for a specific cache"""
        with self._lock:
            stats = self._cache_stats[cache_name]
            total = stats["hits"] + stats["misses"]
            if total == 0:
                return 0.0
            return (stats["hits"] / total) * 100
    
    def get_average_latency(self, endpoint: Optional[str] = None) -> float:
        """Get average latency (in ms)"""
        with self._lock:
            if endpoint:
                stats = self._endpoint_stats[endpoint]
                if stats["count"] == 0:
                    return 0.0
                return stats["total_time_ms"] / stats["count"]
            else:
                if not self._query_latencies:
                    return 0.0
                return sum(self._query_latencies) / len(self._query_latencies)
    
    def get_percentile(self, percentile: float, endpoint: Optional[str] = None) -> float:
        """Get latency percentile (e.g., p50, p95, p99)"""
        with self._lock:
            if endpoint:
                latencies = self._endpoint_stats[endpoint]["latencies"]
            else:
                latencies = self._query_latencies
            
            if not latencies:
                return 0.0
            
            sorted_latencies = sorted(latencies)
            index = int(len(sorted_latencies) * (percentile / 100))
            return sorted_latencies[min(index, len(sorted_latencies) - 1)]
    
    def get_summary(self) -> Dict:
        """Get comprehensive metrics summary"""
        with self._lock:
            uptime_seconds = time.time() - self._start_time
            
            # Calculate overall statistics
            total_queries = len(self._query_latencies)
            avg_latency = self.get_average_latency()
            p50_latency = self.get_percentile(50)
            p95_latency = self.get_percentile(95)
            p99_latency = self.get_percentile(99)
            
            # Cache statistics
            cache_summary = {}
            for cache_name, stats in self._cache_stats.items():
                total = stats["hits"] + stats["misses"]
                hit_rate = (stats["hits"] / total * 100) if total > 0 else 0
                cache_summary[cache_name] = {
                    "hits": stats["hits"],
                    "misses": stats["misses"],
                    "hit_rate_percent": round(hit_rate, 2)
                }
            
            # Endpoint statistics
            endpoint_summary = {}
            for endpoint, stats in self._endpoint_stats.items():
                endpoint_summary[endpoint] = {
                    "count": stats["count"],
                    "avg_latency_ms": round(stats["total_time_ms"] / stats["count"], 2) if stats["count"] > 0 else 0,
                    "errors": stats["errors"],
                    "error_rate_percent": round((stats["errors"] / stats["count"] * 100) if stats["count"] > 0 else 0, 2)
                }
            
            # Vector search statistics
            vector_total = self._vector_search_stats["cache_hits"] + self._vector_search_stats["cache_misses"]
            vector_hit_rate = (self._vector_search_stats["cache_hits"] / vector_total * 100) if vector_total > 0 else 0
            
            return {
                "uptime_seconds": round(uptime_seconds, 2),
                "uptime_human": self._format_uptime(uptime_seconds),
                "total_queries": total_queries,
                "overall_latency": {
                    "average_ms": round(avg_latency, 2),
                    "p50_ms": round(p50_latency, 2),
                    "p95_ms": round(p95_latency, 2),
                    "p99_ms": round(p99_latency, 2)
                },
                "cache_statistics": cache_summary,
                "endpoint_statistics": endpoint_summary,
                "vector_search": {
                    "total_searches": self._vector_search_stats["count"],
                    "cache_hit_rate_percent": round(vector_hit_rate, 2),
                    "avg_latency_ms": round(
                        self._vector_search_stats["total_time_ms"] / self._vector_search_stats["count"], 2
                    ) if self._vector_search_stats["count"] > 0 else 0
                },
                "database": {
                    "total_queries": self._db_query_stats["count"],
                    "avg_latency_ms": round(
                        self._db_query_stats["total_time_ms"] / self._db_query_stats["count"], 2
                    ) if self._db_query_stats["count"] > 0 else 0
                }
            }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        
        return " ".join(parts)
    
    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self._query_latencies.clear()
            self._cache_stats.clear()
            self._endpoint_stats.clear()
            self._db_query_stats = {"count": 0, "total_time_ms": 0, "latencies": []}
            self._vector_search_stats = {
                "count": 0,
                "total_time_ms": 0,
                "cache_hits": 0,
                "cache_misses": 0
            }
            self._start_time = time.time()


# Global metrics instance
_global_metrics = None


def get_metrics() -> PerformanceMetrics:
    """Get the global metrics instance"""
    global _global_metrics
    
    if _global_metrics is None:
        _global_metrics = PerformanceMetrics()
    
    return _global_metrics


# Context manager for timing operations
class timer:
    """Context manager for timing code blocks"""
    
    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time = None
        self.duration_ms = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.time() - self.start_time) * 1000
        return False

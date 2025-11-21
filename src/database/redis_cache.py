"""Redis cache manager for health data and fast operations."""

import os
import json
import redis
from datetime import timedelta
from typing import Optional, Any, List, Dict


class RedisCache:
    """Redis cache manager for health data caching and fast lookups."""

    def __init__(self, url: Optional[str] = None):
        """
        Initialize Redis connection.

        Args:
            url: Redis connection URL. Defaults to REDIS_URL env var.
        """
        redis_url = url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.default_ttl = timedelta(hours=24)  # 24-hour default cache

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live. Defaults to 24 hours.

        Returns:
            True if successful
        """
        try:
            ttl = ttl or self.default_ttl
            self.redis.setex(
                key,
                ttl,
                json.dumps(value, default=str)  # default=str handles datetime objects
            )
            return True
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted
        """
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "health:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis INVALIDATE error: {e}")
            return 0

    # Health Data Specific Methods

    def get_recent_activities(self, limit: int = 10) -> Optional[List[Dict]]:
        """
        Get recent activities from cache.

        Args:
            limit: Number of activities to retrieve

        Returns:
            List of recent activities or None if not cached
        """
        return self.get(f"health:activities:recent:{limit}")

    def set_recent_activities(self, activities: List[Dict], limit: int = 10) -> bool:
        """
        Cache recent activities.

        Args:
            activities: List of activity dictionaries
            limit: Number of activities (for cache key)

        Returns:
            True if successful
        """
        return self.set(f"health:activities:recent:{limit}", activities)

    def get_sleep_data(self, days: int = 7) -> Optional[List[Dict]]:
        """
        Get recent sleep data from cache.

        Args:
            days: Number of days of sleep data

        Returns:
            List of sleep sessions or None if not cached
        """
        return self.get(f"health:sleep:recent:{days}")

    def set_sleep_data(self, sleep_sessions: List[Dict], days: int = 7) -> bool:
        """
        Cache sleep data.

        Args:
            sleep_sessions: List of sleep session dictionaries
            days: Number of days (for cache key)

        Returns:
            True if successful
        """
        return self.set(f"health:sleep:recent:{days}", sleep_sessions)

    def get_resting_hr_trend(self, days: int = 7) -> Optional[List[Dict]]:
        """
        Get resting heart rate trend from cache.

        Args:
            days: Number of days of data

        Returns:
            List of RHR readings or None if not cached
        """
        return self.get(f"health:rhr:trend:{days}")

    def set_resting_hr_trend(self, readings: List[Dict], days: int = 7) -> bool:
        """
        Cache resting heart rate trend.

        Args:
            readings: List of RHR reading dictionaries
            days: Number of days (for cache key)

        Returns:
            True if successful
        """
        return self.set(f"health:rhr:trend:{days}", readings)

    def invalidate_health_cache(self) -> int:
        """
        Invalidate all health-related cache entries.

        Returns:
            Number of keys deleted
        """
        return self.invalidate_pattern("health:*")

    # Workout Library Caching

    def get_workout(self, workout_id: str) -> Optional[Dict]:
        """
        Get workout from cache.

        Args:
            workout_id: Workout ID

        Returns:
            Workout dictionary or None if not cached
        """
        return self.get(f"workout:{workout_id}")

    def set_workout(self, workout_id: str, workout: Dict) -> bool:
        """
        Cache workout.

        Args:
            workout_id: Workout ID
            workout: Workout dictionary

        Returns:
            True if successful
        """
        # Longer TTL for workouts (7 days)
        return self.set(f"workout:{workout_id}", workout, ttl=timedelta(days=7))

    def invalidate_workout_cache(self) -> int:
        """
        Invalidate all workout cache entries.

        Returns:
            Number of keys deleted
        """
        return self.invalidate_pattern("workout:*")

    # Background Job Queue Support

    def enqueue_job(self, queue_name: str, job_data: Dict) -> bool:
        """
        Add a job to a queue.

        Args:
            queue_name: Name of the queue
            job_data: Job data dictionary

        Returns:
            True if successful
        """
        try:
            self.redis.rpush(queue_name, json.dumps(job_data, default=str))
            return True
        except Exception as e:
            print(f"Redis ENQUEUE error: {e}")
            return False

    def dequeue_job(self, queue_name: str, timeout: int = 0) -> Optional[Dict]:
        """
        Get a job from a queue (blocking).

        Args:
            queue_name: Name of the queue
            timeout: Timeout in seconds (0 = non-blocking)

        Returns:
            Job data dictionary or None if queue is empty
        """
        try:
            if timeout > 0:
                result = self.redis.blpop(queue_name, timeout=timeout)
                if result:
                    _, job_data = result
                    return json.loads(job_data)
            else:
                job_data = self.redis.lpop(queue_name)
                if job_data:
                    return json.loads(job_data)
            return None
        except Exception as e:
            print(f"Redis DEQUEUE error: {e}")
            return None

    def get_queue_length(self, queue_name: str) -> int:
        """
        Get the number of jobs in a queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Queue length
        """
        try:
            return self.redis.llen(queue_name)
        except Exception as e:
            print(f"Redis LLEN error: {e}")
            return 0

    def ping(self) -> bool:
        """
        Check if Redis is responsive.

        Returns:
            True if Redis is available
        """
        try:
            return self.redis.ping()
        except Exception:
            return False


# Global cache instance
_cache_instance = None


def get_cache() -> RedisCache:
    """
    Get the global Redis cache instance.

    Returns:
        RedisCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance

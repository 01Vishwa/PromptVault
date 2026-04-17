from collections import OrderedDict
from typing import Optional
from ...domain.entities.judge_result import JudgeResult

class JudgeCache:
    """In-memory LRU cache keyed by str(task_id + trajectory_hash)."""
    def __init__(self, maxsize: int = 500):
        self.maxsize = maxsize
        self.cache: OrderedDict[str, JudgeResult] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, task_id: str, trajectory_hash: str) -> Optional[JudgeResult]:
        key = f"{task_id}_{trajectory_hash}"
        if key in self.cache:
            self.cache.move_to_end(key)
            self.hits += 1
            result = self.cache[key]
            result.cached = True
            return result
        self.misses += 1
        return None

    def set(self, task_id: str, trajectory_hash: str, result: JudgeResult) -> None:
        key = f"{task_id}_{trajectory_hash}"
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = result
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def stats(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self.cache),
            "maxsize": self.maxsize
        }

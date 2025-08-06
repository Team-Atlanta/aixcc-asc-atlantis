import threading
import time


class LLMManager:
    def __init__(self, budget):
        self.rate_limited_models = set()
        self.model_expiration_times = {}
        self.lock = threading.Lock()
        self.cost = 0
        self.budget = budget

    def is_rate_limited(self, model):
        with self.lock:
            if model in self.rate_limited_models:
                if (
                    self.model_expiration_times.get(model)
                    and time.time() >= self.model_expiration_times[model]
                ):
                    self.rate_limited_models.remove(model)
                    return False
                else:
                    return True
            return False

    def has_cost_exceeded_limit(self):
        with self.lock:
            if self.cost >= self.budget:
                return False
            return True

    def rate_limit(self, model):
        with self.lock:
            self.rate_limited_models.add(model)
            self.model_expiration_times[model] = time.time() + 10

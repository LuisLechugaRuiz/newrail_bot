class Metric(object):
    def __init__(self, metrics: dict[str, int]):
        self.metrics = metrics

    def add_metric(self, metric: str, score: int):
        """Add a metric"""

        self.metrics[metric] = score

    def get_metrics(self) -> dict[str, int]:
        """Get metrics"""

        return self.metrics

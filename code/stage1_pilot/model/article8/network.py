"""Simple undirected modular graph and exact descriptive statistics."""
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from .config import Config
from .randomness import stream


@dataclass(frozen=True)
class Network:
    community: tuple[int, ...]
    neighbors: tuple[frozenset[int], ...]

    def edges(self) -> tuple[tuple[int, int], ...]:
        return tuple((i, j) for i, adj in enumerate(self.neighbors) for j in sorted(adj) if i < j)

    def validate(self) -> None:
        n = len(self.community)
        if len(self.neighbors) != n or n == 0:
            raise ValueError("Invalid network dimensions")
        for i, adj in enumerate(self.neighbors):
            if i in adj or any(type(j) is not int or not 0 <= j < n for j in adj):
                raise ValueError("Invalid neighbor or self-link")
            if any(i not in self.neighbors[j] for j in adj):
                raise ValueError("Asymmetric undirected edge")

    def fingerprint(self) -> str:
        payload = json.dumps([self.community, self.edges()], separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def metrics(self) -> dict:
        self.validate()
        n = len(self.community)
        edges = self.edges()
        m = len(edges)
        degrees = [len(x) for x in self.neighbors]
        local_clustering = []
        for i, adj in enumerate(self.neighbors):
            k = len(adj)
            # Each edge among i's neighbors is encountered twice.
            closed_ordered_pairs = sum(len(adj & self.neighbors[j]) for j in adj)
            local_clustering.append(closed_ordered_pairs / (k * (k - 1)) if k >= 2 else 0.0)
        unseen = set(range(n))
        sizes = []
        while unseen:
            root = min(unseen)
            unseen.remove(root)
            stack, size = [root], 0
            while stack:
                i = stack.pop()
                size += 1
                for j in sorted(self.neighbors[i]):
                    if j in unseen:
                        unseen.remove(j)
                        stack.append(j)
            sizes.append(size)
        internal = Counter(self.community[i] for i, j in edges if self.community[i] == self.community[j])
        degree_by_group = Counter()
        for c, degree in zip(self.community, degrees):
            degree_by_group[c] += degree
        modularity = None if m == 0 else sum(
            internal[c] / m - (degree_by_group[c] / (2 * m)) ** 2
            for c in sorted(set(self.community)))
        between = sum(self.community[i] != self.community[j] for i, j in edges)
        return {
            "nodes": n, "edges": m, "mean_degree": sum(degrees) / n,
            "minimum_degree": min(degrees), "maximum_degree": max(degrees),
            "degree_histogram": dict(sorted(Counter(degrees).items())),
            "mean_clustering_including_isolates": sum(local_clustering) / n,
            "assigned_community_modularity": modularity,
            "component_count": len(sizes), "component_sizes": sorted(sizes, reverse=True),
            "largest_component_fraction": max(sizes) / n,
            "community_sizes": dict(sorted(Counter(self.community).items())),
            "between_community_edges": between, "within_community_edges": m - between,
            "network_sha256": self.fingerprint(),
        }


def make_network(config: Config) -> Network:
    config.validate()
    rng = stream(config.seed, "network")
    labels = tuple(i // (config.n // config.communities) for i in range(config.n))
    neighbors = [set() for _ in range(config.n)]
    for i in range(config.n):
        for j in range(i + 1, config.n):
            p = config.p_within if labels[i] == labels[j] else config.p_between
            # Consume one draw even when p is 0 or 1: paired topology experiments.
            if rng.random() < p:
                neighbors[i].add(j)
                neighbors[j].add(i)
    network = Network(labels, tuple(frozenset(x) for x in neighbors))
    network.validate()
    return network

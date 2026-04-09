"""
Clustering pipeline: UMAP dimensionality reduction → HDBSCAN clustering.
Returns cluster labels and 2D UMAP coordinates for graph layout.
"""
import numpy as np
import umap
import hdbscan


def run(
    embeddings: list[list[float]],
    min_cluster_size: int = 5,
) -> dict:
    """
    Args:
        embeddings: List of embedding vectors (all same dimension)
        min_cluster_size: Minimum number of points to form a cluster

    Returns:
        {
            "labels": list[int],     # cluster label per embedding (-1 = noise)
            "umap_x": list[float],   # 2D x position for graph layout
            "umap_y": list[float],   # 2D y position for graph layout
        }
    """
    matrix = np.array(embeddings, dtype=np.float32)
    n_samples = len(matrix)

    if n_samples < 2:
        raise ValueError("Need at least 2 embedded fragments to run clustering.")

    # n_neighbors must be < n_samples; clamp to a safe value
    n_neighbors = min(15, max(2, n_samples - 1))

    # UMAP: reduce to 2D for graph layout AND to min(10, n_samples-1)D for HDBSCAN
    # (HDBSCAN works better in lower-dim space than raw 384-dim)
    reducer_2d = umap.UMAP(
        n_components=2, n_neighbors=n_neighbors, random_state=42, min_dist=0.1
    )
    coords_2d = reducer_2d.fit_transform(matrix)

    cluster_dims = min(10, max(2, n_samples - 1))
    reducer_cluster = umap.UMAP(
        n_components=cluster_dims, n_neighbors=n_neighbors, random_state=42, min_dist=0.0
    )
    coords_cluster = reducer_cluster.fit_transform(matrix)

    # min_samples=1 means every point can be a core point — much less noise on small datasets
    effective_min_samples = min(1, min_cluster_size - 1) if n_samples < 100 else None
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=effective_min_samples,
        metric="euclidean",
        prediction_data=True,
    )
    labels = clusterer.fit_predict(coords_cluster)

    return {
        "labels": labels.tolist(),
        "umap_x": coords_2d[:, 0].tolist(),
        "umap_y": coords_2d[:, 1].tolist(),
    }

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.metrics.pairwise import cosine_similarity


def compute_clusters(articles, embeddings, min_cluster_size=2, min_samples=1):
    if not embeddings or len(embeddings) < 2:
        return [{"cluster_id": -1} for _ in articles]

    matrix = np.array(embeddings)
    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="eom",
        copy=True,
    )
    labels = clusterer.fit_predict(matrix)

    result = []
    for i, a in enumerate(articles):
        a["cluster_id"] = int(labels[i])
        result.append(a)

    clusters = {}
    for a in result:
        cid = a["cluster_id"]
        if cid == -1:
            continue
        if cid not in clusters:
            clusters[cid] = {"articles": [], "size": 0}
        clusters[cid]["articles"].append(a)
        clusters[cid]["size"] += 1

    return result, clusters


def find_similar_articles(articles, embeddings, threshold=0.75):
    if not embeddings or len(embeddings) < 2:
        return []

    matrix = np.array(embeddings)
    sim_matrix = cosine_similarity(matrix)

    groups = []
    assigned = set()

    for i in range(len(articles)):
        if i in assigned:
            continue
        group = [i]
        for j in range(i + 1, len(articles)):
            if j not in assigned and sim_matrix[i][j] >= threshold:
                group.append(j)
                assigned.add(j)
        if len(group) > 1:
            assigned.add(i)
            groups.append(group)

    return groups

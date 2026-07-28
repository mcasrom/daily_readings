import numpy as np
from collections import Counter
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


STOPWORDS_MULTI = set('el la los las un una en de del para por con sin sobre entre a ante bajo cabe contra desde hasta según tras durante mediante versus via y e o u al lo le su sus tu mi tu nuestro vuestro que es se no les was were the in of for to and a an with from at by on as into through during about between after before above below up down out off over under again further then once here there when where why how all each both few more most other some such only own same so than too very just because also much'.split())


def _cluster_keywords(cluster_articles, max_words=5):
    word_counts = Counter()
    for a in cluster_articles:
        title = a.get("title", "")
        for w in title.lower().split():
            w = w.strip(".,!?;:()[]{}«»\"'")
            if len(w) > 3 and w not in STOPWORDS_MULTI and not w.isdigit():
                word_counts[w] += 1
    return set(w for w, _ in word_counts.most_common(max_words))


def merge_clusters_by_keywords(clustered, min_keyword_overlap=2):
    cid_to_articles = {}
    for a in clustered:
        cid = a.get("cluster_id", -1)
        if cid != -1:
            if cid not in cid_to_articles:
                cid_to_articles[cid] = []
            cid_to_articles[cid].append(a)

    cluster_keywords = {}
    for cid, arts in cid_to_articles.items():
        cluster_keywords[cid] = _cluster_keywords(arts)

    merge_map = {}
    cids = sorted(cid_to_articles.keys())
    for i in range(len(cids)):
        for j in range(i + 1, len(cids)):
            c1, c2 = cids[i], cids[j]
            if c2 in merge_map or c1 in merge_map:
                continue
            overlap = len(cluster_keywords[c1] & cluster_keywords[c2])
            if overlap >= min_keyword_overlap:
                merge_map[c2] = c1

    if not merge_map:
        return clustered, None

    print(f'  [MERGE-KW] Fusionando {len(merge_map)} clusters por keywords...')
    for a in clustered:
        cid = a.get("cluster_id", -1)
        if cid in merge_map:
            a["cluster_id"] = merge_map[cid]

    merged = {}
    for a in clustered:
        cid = a["cluster_id"]
        if cid == -1:
            continue
        if cid not in merged:
            merged[cid] = {"articles": [], "size": 0}
        merged[cid]["articles"].append(a)
        merged[cid]["size"] += 1

    print(f'  [MERGE-KW] Clusters tras fusión: {len(merged)}')
    return clustered, merged


def merge_clusters_by_sync(clustered, sync_events):
    article_to_cluster = {}
    for a in clustered:
        cid = a.get("cluster_id", -1)
        if cid != -1:
            article_to_cluster[a["id"]] = cid

    cluster_merge_map = {}
    for se in sync_events:
        article_ids = se.get("article_ids", [])
        involved_clusters = set()
        for aid in article_ids:
            cid = article_to_cluster.get(aid)
            if cid is not None and cid != -1:
                involved_clusters.add(cid)
        if len(involved_clusters) >= 2:
            sorted_clusters = sorted(involved_clusters)
            target = sorted_clusters[0]
            for cid in sorted_clusters[1:]:
                cluster_merge_map[cid] = target

    if not cluster_merge_map:
        print('  [MERGE] No hay clusters para fusionar')
        return clustered, None

    print(f'  [MERGE] Fusionando {len(cluster_merge_map)} clusters por sync events...')
    for a in clustered:
        cid = a.get("cluster_id", -1)
        if cid in cluster_merge_map:
            a["cluster_id"] = cluster_merge_map[cid]

    merged_clusters = {}
    for a in clustered:
        cid = a["cluster_id"]
        if cid == -1:
            continue
        if cid not in merged_clusters:
            merged_clusters[cid] = {"articles": [], "size": 0}
        merged_clusters[cid]["articles"].append(a)
        merged_clusters[cid]["size"] += 1

    print(f'  [MERGE] Clusters tras fusión: {len(merged_clusters)}')
    return clustered, merged_clusters


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

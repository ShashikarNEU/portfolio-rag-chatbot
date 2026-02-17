from concurrent.futures import ThreadPoolExecutor

from pinecone import Pinecone

from app.config import settings
from app.services.llm_service import LLMService

RRF_K = 60
SEARCH_TOP_K = 5
PRIORITY_BOOST: dict[str, float] = {"high": 2.0, "medium": 1.0, "low": 0.5}


class Retriever:
    """Searches Pinecone with multiple queries and fuses results via RRF."""

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index = pc.Index(settings.pinecone_index_name)
        self.top_k = settings.top_k_retrieval

    def _search(self, vector: list[float]) -> list[dict]:
        """Query Pinecone with a single vector."""
        results = self.index.query(
            vector=vector, top_k=SEARCH_TOP_K, include_metadata=True,
        )
        return results.matches

    def search_queries(self, queries: list[str]) -> list[list[dict]]:
        """Embed all queries in one batch, then search Pinecone in parallel.

        ThreadPool here because each Pinecone query is a network call (~100ms).
        Running them in parallel instead of one-by-one saves real time.
        """
        if not queries:
            return []
        embeddings = self.llm.embed_batch(queries)
        with ThreadPoolExecutor(max_workers=len(queries)) as pool:
            return list(pool.map(self._search, embeddings))

    def fuse_and_rank(self, match_lists: list[list[dict]]) -> list[dict]:
        """Combine results from multiple queries using RRF + priority boost.

        RRF (Reciprocal Rank Fusion): chunks that appear in multiple query
        results get higher scores. PRIORITY_BOOST multiplies the score so
        flagship projects / skills / experience rank higher.
        """
        rrf_scores: dict[str, float] = {}
        chunk_data: dict[str, dict] = {}

        for matches in match_lists:
            for rank, match in enumerate(matches):
                chunk_id = match.id
                rrf_scores[chunk_id] = (
                    rrf_scores.get(chunk_id, 0) + 1 / (rank + RRF_K)
                )
                if chunk_id not in chunk_data:
                    chunk_data[chunk_id] = {
                        "id": chunk_id,
                        "text": match.metadata.get("text", ""),
                        "source": match.metadata.get("source", ""),
                        "priority": match.metadata.get("priority", "medium"),
                        "similarity_score": match.score,
                    }

        results: list[dict] = []
        for chunk_id, rrf_score in rrf_scores.items():
            boost = PRIORITY_BOOST.get(chunk_data[chunk_id]["priority"], 1.0)
            results.append({
                **chunk_data[chunk_id],
                "rrf_score": rrf_score * boost,
            })

        results.sort(key=lambda c: c["rrf_score"], reverse=True)
        return results[: self.top_k]

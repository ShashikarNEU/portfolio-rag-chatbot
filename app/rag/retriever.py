from concurrent.futures import ThreadPoolExecutor

from pinecone import Pinecone

from app.config import settings
from app.services.llm_service import LLMService

RRF_K = 60
SEARCH_TOP_K = 10  # Pinecone results per query (wide net for diversity)
PRIORITY_BOOST: dict[str, float] = {"high": 2.0, "medium": 1.0, "low": 0.5}


class Retriever:
    """Searches Pinecone with multiple queries and fuses results via RRF."""

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index = pc.Index(settings.pinecone_index_name)
        self.top_k = settings.top_k_retrieval  # fusion output size

    def _search_with_vector(self, vector: list[float]) -> list[dict]:
        """Query Pinecone with a pre-computed vector."""
        results = self.index.query(
            vector=vector,
            top_k=SEARCH_TOP_K,
            include_metadata=True,
        )
        return results.matches

    def embed_and_search_one(self, query: str) -> list[dict]:
        """Embed a single query and search Pinecone."""
        embedding = self.llm.embed(query)
        return self._search_with_vector(embedding)

    def embed_and_search_batch(self, queries: list[str]) -> list[list[dict]]:
        """Batch-embed queries and search Pinecone in parallel."""
        if not queries:
            return []
        embeddings = self.llm.embed_batch(queries)
        with ThreadPoolExecutor(max_workers=len(queries)) as pool:
            return list(pool.map(self._search_with_vector, embeddings))

    def fuse_and_rank(self, match_lists: list[list[dict]]) -> list[dict]:
        """Apply RRF fusion + priority boost, return top_k."""
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

    def retrieve(self, query: str, expanded_queries: list[str]) -> list[dict]:
        """Search with original + expanded queries, fuse with RRF, return top_k."""
        all_queries = [query] + expanded_queries
        match_lists = self.embed_and_search_batch(all_queries)
        return self.fuse_and_rank(match_lists)

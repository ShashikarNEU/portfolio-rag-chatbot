"""Integration tests for the RAG pipeline — real OpenAI + Pinecone.

Run: uv run pytest tests/test_rag.py -v
"""

import pytest

from app.rag.query_expansion import QueryExpander
from app.rag.reranker import Reranker
from app.rag.retriever import Retriever
from app.services.llm_service import LLMService


@pytest.fixture(scope="module")
def llm() -> LLMService:
    return LLMService()


@pytest.fixture(scope="module")
def expander(llm: LLMService) -> QueryExpander:
    return QueryExpander(llm)


@pytest.fixture(scope="module")
def retriever(llm: LLMService) -> Retriever:
    return Retriever(llm)


@pytest.fixture(scope="module")
def reranker(llm: LLMService) -> Reranker:
    return Reranker(llm)


class TestQueryExpansion:
    def test_expand_returns_variants(self, expander: QueryExpander) -> None:
        expanded = expander.expand("What projects has Shashikar built?")
        assert isinstance(expanded, list)
        assert len(expanded) >= 1
        for q in expanded:
            assert isinstance(q, str)
            assert len(q) > 0


class TestRetrieval:
    def test_retrieve_returns_chunks(self, retriever: Retriever) -> None:
        match_lists = retriever.search_queries(["What are Shashikar's skills?"])
        assert len(match_lists) == 1
        results = match_lists[0]
        assert len(results) > 0
        for match in results:
            assert hasattr(match, "metadata")
            assert "text" in match.metadata
            assert "source" in match.metadata

    def test_rrf_fusion_ranks_results(self, retriever: Retriever) -> None:
        matches = retriever.search_queries(["Shashikar's experience"])
        ranked = retriever.fuse_and_rank(matches)
        assert len(ranked) > 0
        scores = [c["rrf_score"] for c in ranked]
        assert scores == sorted(scores, reverse=True)


class TestReranker:
    def test_rerank_scores_chunks(
        self, reranker: Reranker, retriever: Retriever,
    ) -> None:
        matches = retriever.search_queries(["What projects has Shashikar built?"])
        chunks = retriever.fuse_and_rank(matches)
        reranked = reranker.rerank("What projects has Shashikar built?", chunks)
        assert len(reranked) > 0
        for chunk in reranked:
            assert "relevance_score" in chunk
            assert "relevance_reason" in chunk


class TestFullPipeline:
    def test_end_to_end_search(self) -> None:
        """Full pipeline: retrieve → fuse → returns context and sources."""
        from app.graph.tools import RAGPipeline

        RAGPipeline._instance = None
        pipeline = RAGPipeline.get_instance()

        context, sources = pipeline.search("What are Shashikar's skills?")

        assert isinstance(context, str)
        assert len(context) > 0
        assert isinstance(sources, list)
        assert len(sources) > 0
        for source in sources:
            assert "document" in source
            assert "chunk" in source
            assert "relevance_score" in source

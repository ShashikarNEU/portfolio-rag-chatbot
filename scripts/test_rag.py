"""
Test the full RAG pipeline: expand -> retrieve with RRF -> rerank.

Run: uv run python scripts/test_rag.py
"""

from dotenv import load_dotenv

load_dotenv()

from app.rag.query_expansion import QueryExpander
from app.rag.reranker import Reranker
from app.rag.retriever import Retriever
from app.services.llm_service import LLMService


def main() -> None:
    query = "What projects has Shashikar built?"

    print("\n=== RAG Pipeline Test ===\n")

    llm = LLMService()
    expander = QueryExpander(llm)
    retriever = Retriever(llm)
    reranker = Reranker(llm)

    # Step 1: Query Expansion
    print("Step 1: Query Expansion")
    print(f"  Original: {query}")
    expanded = expander.expand(query)
    for i, eq in enumerate(expanded, 1):
        print(f"  Variant {i}: {eq}")

    # Step 2: Retrieve with RRF
    print(f"\nStep 2: Retrieval + RRF (top {retriever.top_k})")
    chunks = retriever.retrieve(query, expanded)
    for i, chunk in enumerate(chunks, 1):
        print(f"\n  [{i}] Source: {chunk['source']} | RRF: {chunk['rrf_score']:.4f}")
        print(f"      {chunk['text'][:150]}...")

    # Step 3: Rerank
    print(f"\nStep 3: LLM Reranking (top {reranker.top_k})")
    reranked = reranker.rerank(query, chunks)
    for i, chunk in enumerate(reranked, 1):
        print(f"\n  [{i}] Source: {chunk['source']} | Relevance: {chunk['relevance_score']}/10")
        print(f"      Reason: {chunk['relevance_reason']}")
        print(f"      {chunk['text']}...")

    print("\n=== Done ===\n")


if __name__ == "__main__":
    main()

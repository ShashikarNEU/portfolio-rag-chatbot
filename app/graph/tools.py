from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command

from app.rag.query_expansion import QueryExpander
from app.rag.reranker import Reranker
from app.rag.retriever import Retriever
from app.services.llm_service import LLMService


class RAGPipeline:
    """Singleton that orchestrates query expansion, retrieval, and reranking."""

    _instance: "RAGPipeline | None" = None

    def __init__(self) -> None:
        self._llm = LLMService()
        self._expander = QueryExpander(self._llm)
        self._retriever = Retriever(self._llm)
        self._reranker = Reranker(self._llm)

    @classmethod
    def get_instance(cls) -> "RAGPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def search(self, query: str) -> tuple[str, list[dict]]:
        """Run full RAG pipeline: expand -> retrieve -> rerank.

        Returns (formatted_context, sources).
        """
        # Step 1: while the LLM generates expanded queries (~1s),
        # simultaneously embed+search the original query in Pinecone.
        with ThreadPoolExecutor(max_workers=2) as pool:
            expand_future = pool.submit(self._expander.expand, query)
            original_future = pool.submit(
                self._retriever.search_queries, [query],
            )

        original_matches = original_future.result()
        expanded = expand_future.result()

        # Step 2: embed+search expanded queries
        exp_matches = self._retriever.search_queries(expanded)

        # Step 3: fuse all results via RRF + priority boost
        candidates = self._retriever.fuse_and_rank(
            original_matches + exp_matches,
        )

        # Step 4: LLM rerank
        top_chunks = self._reranker.rerank(query, candidates)

        context_parts: list[str] = []
        sources: list[dict] = []
        for chunk in top_chunks:
            score = chunk["relevance_score"] / 10
            context_parts.append(
                f"[Source: {chunk['source']} | Relevance: {score:.2f}]\n"
                f"{chunk['text']}"
            )
            sources.append({
                "document": chunk["source"],
                "chunk": chunk["text"],
                "relevance_score": score,
            })

        return "\n\n".join(context_parts), sources


@tool
def search_portfolio(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Search Shashikar Anthoni Raj's portfolio for information about his
    skills, projects, experience, and education. Use this for any question
    about Shashikar."""
    pipeline = RAGPipeline.get_instance()
    context, sources = pipeline.search(query)
    return Command(update={
        "sources": sources,
        "messages": [ToolMessage(
            content=context,
            tool_call_id=tool_call_id,
            name="search_portfolio",
        )],
    })


@tool
def send_email(
    name: str,
    email: str,
    inquiry: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Send a contact email to Shashikar with the visitor's details.
    Only call this when you have all three: name, email, and inquiry."""
    from app.services.email_service import EmailService

    service = EmailService.get_instance()
    success = service.send_contact_email(name, email, inquiry)

    if success:
        return Command(update={
            "email_sent": True,
            "messages": [ToolMessage(
                content=f"Email sent successfully from {name} ({email})",
                tool_call_id=tool_call_id,
                name="send_email",
            )],
        })
    return Command(update={
        "email_sent": False,
        "messages": [ToolMessage(
            content="Failed to send email. Please try again later.",
            tool_call_id=tool_call_id,
            name="send_email",
        )],
    })


tools = [search_portfolio, send_email]

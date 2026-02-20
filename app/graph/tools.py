# from concurrent.futures import ThreadPoolExecutor  # re-enable with query expansion
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
        """Run full RAG pipeline: retrieve -> rerank.

        Returns (formatted_context, sources).
        """
        # Query expansion disabled to stay under 30s timeout on broad queries.
        # To re-enable, uncomment the block below and change Step 3 back to
        # fuse_and_rank(original_matches + exp_matches).

        # # Step 1: while the LLM generates expanded queries (~1s),
        # # simultaneously embed+search the original query in Pinecone.
        # with ThreadPoolExecutor(max_workers=2) as pool:
        #     expand_future = pool.submit(self._expander.expand, query)
        #     original_future = pool.submit(
        #         self._retriever.search_queries, [query],
        #     )
        # original_matches = original_future.result()
        # expanded = expand_future.result()
        # # Step 2: embed+search expanded queries
        # exp_matches = self._retriever.search_queries(expanded)

        # Step 1: embed+search the original query
        original_matches = self._retriever.search_queries([query])

        # Step 2: fuse results via RRF + priority boost
        top_chunks = self._retriever.fuse_and_rank(original_matches)

        # Step 3: LLM rerank — disabled, adds ~15s per query (exceeds 30s timeout)
        # top_chunks = self._reranker.rerank(query, top_chunks)

        context_parts: list[str] = []
        sources: list[dict] = []
        for chunk in top_chunks:
            score = chunk["rrf_score"] 
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
    try:
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
    except Exception:
        return Command(update={
            "sources": [],
            "messages": [ToolMessage(
                content="I'm having trouble searching right now. Please try again in a moment.",
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
    try:
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
                content="Couldn't send email, please try again.",
                tool_call_id=tool_call_id,
                name="send_email",
            )],
        })
    except Exception:
        return Command(update={
            "email_sent": False,
            "messages": [ToolMessage(
                content="Couldn't send email, please try again.",
                tool_call_id=tool_call_id,
                name="send_email",
            )],
        })


@tool
def explore_github(
    action: str,
    repo_name: str = "",
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Explore Shashikar's GitHub profile and repositories.
    Actions: 'list_repos' (all repos), 'repo_details' (one repo),
    'activity' (recent commits/events). Provide repo_name for
    repo_details and activity on a specific repo."""
    try:
        from app.services.github_service import GitHubService

        service = GitHubService.get_instance()

        if action == "list_repos":
            content = service.list_repos()
        elif action == "repo_details":
            if not repo_name:
                content = "Please specify which repository you'd like details about."
            else:
                content = service.get_repo_details(repo_name)
        elif action == "activity":
            content = service.get_activity(repo_name)
        else:
            content = (
                f"Unknown action '{action}'. "
                "Use 'list_repos', 'repo_details', or 'activity'."
            )

        return Command(update={
            "messages": [ToolMessage(
                content=content,
                tool_call_id=tool_call_id,
                name="explore_github",
            )],
        })
    except Exception:
        return Command(update={
            "messages": [ToolMessage(
                content="I'm having trouble reaching GitHub right now. Please try again in a moment.",
                tool_call_id=tool_call_id,
                name="explore_github",
            )],
        })


@tool
def read_github_file(
    repo_name: str,
    file_path: str,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Read the source code of a specific file from one of Shashikar's
    GitHub repositories. Provide the repo name and the file path
    (e.g., 'app/main.py')."""
    try:
        from app.services.github_service import GitHubService

        service = GitHubService.get_instance()
        content = service.read_file(repo_name, file_path)

        return Command(update={
            "messages": [ToolMessage(
                content=content,
                tool_call_id=tool_call_id,
                name="read_github_file",
            )],
        })
    except Exception:
        return Command(update={
            "messages": [ToolMessage(
                content="I'm having trouble reading that file right now. Please try again in a moment.",
                tool_call_id=tool_call_id,
                name="read_github_file",
            )],
        })


tools = [search_portfolio, send_email, explore_github, read_github_file]

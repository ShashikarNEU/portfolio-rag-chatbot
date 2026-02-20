import logging

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage
from openai import BadRequestError

from app.config import settings
from app.graph.tools import tools
from app.models.state import State
from app.utils.prompts import WORKER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Worker:
    """LLM worker node with bound tools for portfolio Q&A and email."""

    def __init__(self) -> None:
        model = init_chat_model(
            settings.llm_model,
            model_provider="openai",
            temperature=0,
            api_key=settings.openai_api_key,
        )
        self.model = model.bind_tools(tools)

    async def __call__(self, state: State) -> dict:
        if state.get("thread_corrupted"):
            return {"messages": []}

        system = [{"role": "system", "content": WORKER_SYSTEM_PROMPT}]
        messages = system + state["messages"]
        try:
            response = await self.model.ainvoke(messages)
        except BadRequestError as exc:
            if "tool_call_ids" not in str(exc):
                raise
            # Corrupted history — don't waste an LLM call.
            # Return a synthetic AIMessage (no tool_calls → routes to END).
            # The SSE layer will send a thread_reset event and wipe the checkpoint.
            logger.warning("Corrupted thread history detected (thread will be reset)")
            return {
                "messages": [AIMessage(content="")],
                "thread_corrupted": True,
            }
        return {"messages": [response]}

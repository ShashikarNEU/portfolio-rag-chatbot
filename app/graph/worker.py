from langchain.chat_models import init_chat_model

from app.config import settings
from app.graph.tools import tools
from app.models.state import State
from app.utils.prompts import WORKER_SYSTEM_PROMPT


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

    def __call__(self, state: State) -> dict:
        messages = (
            [{"role": "system", "content": WORKER_SYSTEM_PROMPT}]
            + state["messages"]
        )
        response = self.model.invoke(messages)
        return {"messages": [response]}

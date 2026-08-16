import sqlite3
from typing import Annotated, TypedDict

from app import openai_api_key, openai_model
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from shared_tools.utiles import Color, print_color

llm = AzureChatOpenAI(
    azure_endpoint="https://ai-foundry-cv-pilot.openai.azure.com/",
    api_key=openai_api_key,
    azure_deployment=openai_model,
    api_version="2024-10-21",
)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


@tool
def get_weather(city: str):
    """Get the weather for a city."""

    return f"The weather in {city} is sunny."


def approval_node(state: AgentState):
    decision = interrupt({"Do you approve it?"})
    return {
        "messages": [{"role": "assistant", "content": f"Approval result: {decision}"}]
    }


tools = [get_weather]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)


def llm_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])

    return {"messages": [response]}


def should_continue(state: AgentState):
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END


builder = StateGraph(AgentState)
builder.add_node("llm", llm_node)
builder.add_node("tools", tool_node)

builder.add_edge(START, "llm")
builder.add_conditional_edges("llm", should_continue)

builder.add_edge("tools", "llm")

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

connection = sqlite3.connect("checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=connection)

graph = builder.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "project12-test-1"}}


print()
try:
    print_color("thinking......", Color.BLUE)

    response = graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "what is my favorite language?",
                }
            ]
        },
        config=config,
    )

    print(response["messages"][-1].content)

    # response = graph.invoke(
    #     {"messages": [{"role": "user", "content": "What was my name?"}]},
    #     config=config,
    # )

    # print(response["messages"][-1].content)


except Exception as e:
    print(type(e).__name__)
    print(e)

print()

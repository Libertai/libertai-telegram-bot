from libertai_agents.agents import ChatAgent
from libertai_agents.models import get_model

agent = ChatAgent(
    model=get_model("NousResearch/Hermes-3-Llama-3.1-8B"),
    system_prompt="You are a helpful assistant",
    tools=[],
)

app = agent.app


@app.get("/")
async def root():
    return {"message": "Hello from your LibertAI Agent!"}

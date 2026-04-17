from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from .react_agent import TOOL_REGISTRY

class AgentConfig(BaseModel):
    model: str = "claude-haiku-4-5-20251001"
    temperature: float = 0.0
    max_iterations: int = 15
    enabled_tools: list[str] = ["calculator", "get_weather", "search_web", "write_file"]
    system_prompt_suffix: str = ""

class AgentFactory:
    """Factory pattern — creates agents from config. Never instantiates directly."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    def create(self, config: AgentConfig = None) -> AgentExecutor:
        """Returns a fresh AgentExecutor with harness-ready callbacks=[]."""
        if config is None:
            config = AgentConfig()
        
        tools = self._build_tools(config.enabled_tools)
        llm = self._build_llm(config)

        template = """Answer the following questions as best you can. You have access to the following tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

{system_prompt_suffix}

Question: {input}
Thought:{agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template).partial(
            system_prompt_suffix=config.system_prompt_suffix
        )
        agent = create_react_agent(llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, max_iterations=config.max_iterations, callbacks=[])

    def _build_tools(self, enabled: list[str]) -> list:
        return [TOOL_REGISTRY[name] for name in enabled if name in TOOL_REGISTRY]

    def _build_llm(self, config: AgentConfig) -> ChatAnthropic:
        return ChatAnthropic(
            model_name=config.model,
            temperature=config.temperature,
            anthropic_api_key=self.api_key
        )

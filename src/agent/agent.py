
import json
import os
from json import JSONDecoder
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from src.core.gemini_provider import GeminiProvider
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


# ============================================================
# Data Models
# ============================================================

class Action(BaseModel):
    tool: str
    arguments: Dict[str, Any]


class ReActStep(BaseModel):
    thought: str
    action: Optional[Action] = None
    final_answer: Optional[str] = None


# ============================================================
# Agent
# ============================================================

class ReActAgent:

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 5,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    def get_system_prompt(self) -> str:

        tool_descriptions = "\n".join(
            [
                f"- {tool['name']}: {tool['description']}"
                for tool in self.tools
            ]
        )

        return f"""
You are a ReAct (Reasoning + Acting) Agent.

AVAILABLE TOOLS

{tool_descriptions}

RULES

1. Think step by step.
2. Use tools whenever external information is needed.
3. Never fabricate tool results.
4. Never simulate tool execution.
5. Never invent observations.
6. Only perform ONE reasoning step at a time.

IMPORTANT

If a tool is needed:

- Return ONE JSON object containing an action.
- Stop immediately.
- Do NOT generate a final answer.

The environment will execute the tool and provide
the observation later.

If enough information is available:

- Return ONE JSON object containing final_answer.
- Do NOT generate an action.

OUTPUT FORMAT

Tool call:

{{
  "thought": "<reasoning>",
  "action": {{
    "tool": "<tool_name>",
    "arguments": {{
      "<arg_name>": "<arg_value>"
    }}
  }},
  "final_answer": null
}}

Final answer:

{{
  "thought": "<reasoning>",
  "action": null,
  "final_answer": "<answer>"
}}

CRITICAL

Return EXACTLY ONE JSON object.

Do not return:
- multiple JSON objects
- markdown
- code fences
- explanations
- additional text
"""

    # --------------------------------------------------------
    # Parsing Helpers
    # --------------------------------------------------------

    def _clean_response(self, text: str) -> str:

        text = text.strip()

        if text.startswith("```json"):
            text = text[7:]

        if text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        return text.strip()

    def _extract_first_json(self, text: str) -> Dict[str, Any]:
        """
        Extract first valid JSON object from model output.
        Handles cases where the model returns:
            {}{}
            {} some text
            ```json ... ```
        """

        text = self._clean_response(text)

        decoder = JSONDecoder()

        obj, _ = decoder.raw_decode(text)

        return obj

    # --------------------------------------------------------
    # Tool Execution
    # --------------------------------------------------------

    def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ):

        tool_map = {
            tool["name"]: tool["function"]
            for tool in self.tools
        }

        if tool_name not in tool_map:
            raise ValueError(
                f"Tool '{tool_name}' not found."
            )

        return tool_map[tool_name](**arguments)

    # --------------------------------------------------------
    # Main Loop
    # --------------------------------------------------------

    def run(self, user_input: str) -> str:

        logger.log_event(
            "AGENT_START",
            {
                "input": user_input,
                "model": self.llm.model_name,
            },
        )

        current_prompt = user_input

        for step_idx in range(self.max_steps):

            try:

                raw_response = self.llm.generate(
                    current_prompt,
                    system_prompt=self.get_system_prompt(),
                )

                logger.log_event(
                    "LLM_RESPONSE",
                    {
                        "step": step_idx,
                        "response": raw_response,
                    },
                )

                llm_text = raw_response["content"]

                parsed_json = self._extract_first_json(
                    llm_text
                )

                react_step = ReActStep.model_validate(
                    parsed_json
                )

            except ValidationError as e:

                logger.log_event(
                    "OUTPUT_VALIDATION_ERROR",
                    {
                        "step": step_idx,
                        "error": str(e),
                    },
                )

                return (
                    "Model returned invalid structured output."
                )

            except Exception as e:

                logger.log_event(
                    "LLM_ERROR",
                    {
                        "step": step_idx,
                        "error": str(e),
                    },
                )

                return f"LLM error: {e}"

            logger.log_event(
                "THOUGHT",
                {
                    "step": step_idx,
                    "thought": react_step.thought,
                },
            )

            # ------------------------------------------------
            # Final Answer
            # ------------------------------------------------

            if react_step.final_answer is not None:

                logger.log_event(
                    "AGENT_END",
                    {
                        "status": "success",
                        "steps": step_idx + 1,
                    },
                )

                return react_step.final_answer

            # ------------------------------------------------
            # Missing Action
            # ------------------------------------------------

            if react_step.action is None:

                logger.log_event(
                    "INVALID_STATE",
                    {
                        "step": step_idx,
                        "reason": (
                            "action and final_answer "
                            "are both null"
                        ),
                    },
                )

                return (
                    "Invalid agent state."
                )

            # ------------------------------------------------
            # Tool Call
            # ------------------------------------------------

            tool_name = react_step.action.tool
            tool_args = react_step.action.arguments

            logger.log_event(
                "TOOL_CALL",
                {
                    "step": step_idx,
                    "tool": tool_name,
                    "arguments": tool_args,
                },
            )

            try:

                observation = self._execute_tool(
                    tool_name,
                    tool_args,
                )

            except Exception as e:

                observation = {
                    "error": str(e)
                }

                logger.log_event(
                    "TOOL_ERROR",
                    {
                        "step": step_idx,
                        "tool": tool_name,
                        "error": str(e),
                    },
                )

            logger.log_event(
                "OBSERVATION",
                {
                    "step": step_idx,
                    "observation": observation,
                },
            )

            current_prompt += f"""

Previous reasoning step:

{json.dumps(parsed_json, indent=2)}

Observation:

{observation}

Based on the observation,
perform the next reasoning step.
"""

        logger.log_event(
            "AGENT_END",
            {
                "status": "max_steps_exceeded",
                "steps": self.max_steps,
            },
        )

        return (
            "Maximum reasoning steps reached."
        )


# ============================================================
# Demo Tool
# ============================================================

def dummy_tool(message: str) -> str:
    return f"Echo: {message}"


# ============================================================
# Main
# ============================================================

def main():

    load_dotenv()

    agent = ReActAgent(
        llm=GeminiProvider(
            model_name="gemini-2.5-flash-lite",
            api_key=os.getenv("GEMINI_API_KEY"),
        ),
        tools=[
            {
                "name": "dummy_tool",
                "description": (
                    "Echo a message. "
                    "Arguments: message (string)"
                ),
                "function": dummy_tool,
            }
        ],
    )

    response = agent.run(
        "Please use the dummy tool to echo 'Hello, World!'"
    )

    print("Agent Response:", response)


if __name__ == "__main__":
    main()

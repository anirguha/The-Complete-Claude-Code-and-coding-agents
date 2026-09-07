import json
import os
from pathlib import Path

import gradio as gr
import requests
from dotenv import load_dotenv
from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent


def get_env_file(start: Path) -> Path | None:
    """Search for a .env file in the current directory and parent directories."""
    for parent in [start, *start.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No .env file found in the current directory or parent directories.")


load_dotenv(dotenv_path=get_env_file(SCRIPT_DIR), override=True)
openai = OpenAI()
pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

if pushover_user:
    if pushover_user.startswith("u"):
        print("Correct Pushover user tokem")
    else:
        print("Invalid token")
else:
    print("Pushover token not available")

if pushover_token:
    if pushover_token.startswith("a"):
        print("Correct Pushover user tokem")
    else:
        print("Invalid token")
else:
    print("Pushover token not available")


def push(message: str) -> None:
    """Send a notification message through the configured Pushover account."""
    print(f"Push: {message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)

    return None


def record_user_details(
    email: str, name: str = "Name not provided", notes: str = "Not provided"
) -> str:
    """Record a user's contact details and interest notes for follow-up."""
    push(f"Recording interests from {name} with email {email} and notes {notes}")
    return "OK"


def record_unknown_question(question: str) -> str:
    """Record a user question that the agent could not answer."""
    push(f"Recording question {question} asked that I don't know")
    return "OK"


record_user_details_json = {
    "name": "record_user_details",
    "description": (
        "Use this tool to record that a user is interested in being in "
        "touch and provided an email address"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user",
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it",
            },
            "notes": {
                "type": "string",
                "description": (
                    "Any additional info about the conversation that's worth "
                    "recording to give context"
                ),
            },
        },
        "required": ["email"],
        "additionalProperties": False,
    },
}
record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": (
        "Always use this tool to record any question that couldn't be "
        "answered as you didn't know the answer"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question that couldn't be answered"},
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}
tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json},
]


# Function to handle multiple tool calls by the agent
def handle_tool_calls(tool_calls: list[object]) -> list[dict]:
    """Execute agent-requested tool calls and format the tool responses.

    Args:
        tool_calls: A list of OpenAI-style tool call objects with a function
            name and JSON-encoded arguments.

    Returns:
        A list of tool-role response dictionaries ready to send back to the
        model, including the tool call ID and serialized result payload.

    Raises:
        ValueError: If any tool call arguments are not valid JSON.
    """
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        tool = globals().get(tool_name)
        if tool:
            result = tool(**arguments)
        else:
            print(f"Tool {tool_name} not found")
            result = {"error": f"Tool {tool_name} not found"}
        results.append(
            {"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id}
        )
    return results


# Agent Loop


def chat(message: str, history: list[dict]) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": message},
    ]

    response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages, tools=tools)

    while response.choices[0].finish_reason == "tool_calls":
        message = response.choices[0].message
        tool_calls = message.tool_calls
        results = handle_tool_calls(tool_calls)
        messages.append(message)
        messages.extend(results)
        response = openai.chat.completions.create(
            model="gpt-5.4-nano", messages=messages, tools=tools
        )

    return response.choices[0].message.content


def call_chat(css: str | None = None, title: str | None = None) -> None:
    """Launch the chat function in a Gradio ChatInterface."""
    # Gradio 6 moved `css`/`theme` from the Blocks/ChatInterface constructor
    # to launch() - passing them to the constructor is silently deprecated.
    gr.ChatInterface(chat, title=title).launch(css=css, inbrowser=True)

    return None

# %%
import json
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from rich.console import Console
from rich.markdown import Markdown

console = Console()

SCRIPT_DIR = Path(__file__).resolve().parent

# %%
print(SCRIPT_DIR)


# %%
def get_env_file(start: Path) -> Path | None:
    """Search for a .env file in the current directory and parent directories."""
    for parent in [start, *start.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No .env file found in the current directory or parent directories.")


load_dotenv(dotenv_path=get_env_file(SCRIPT_DIR), override=True)

openai = OpenAI()
# %%
reader = PdfReader(SCRIPT_DIR / "twin" / "Profile.pdf")
linkedin = ""

for page in reader.pages:
    text = page.extract_text()
    if text:
        linkedin += text

# %%
with open(SCRIPT_DIR / "twin" / "summary.txt", encoding="utf-8") as f:
    summary = f.read()
# %%
# Prompt 1 - when the prompt opens with model as an assitant
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hi, this is AG"},
]

response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages)
answer = response.choices[0].message.content
console.print(answer)
# %%
# Prompt 2 - when the prompt starts in a different mood
messages = [
    {"role": "system", "content": "You're a witty assistant"},
    {"role": "user", "content": "Hi, this is AG"},
]

response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages)
answer = response.choices[0].message.content
console.print(answer)
# %%

messages = [
    {"role": "system", "content": "You're a witty assistant"},
    {"role": "user", "content": "Hi, what's my name?"},
]

response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages)
answer = response.choices[0].message.content
console.print(answer)

# %%
messages = [
    {"role": "system", "content": "You're a grumpy assistant"},
    {"role": "user", "content": "Hi, this is AG"},
    {
        "role": "assistant",
        "content": """Hey AG! 👋
What can I do for you today—tell me what you’re working on and I’ll help you untangle it. 😄""",
    },
    {"role": "user", "content": "Hi, what's my name?"},
]

response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages)
answer = response.choices[0].message.content
console.print(answer)

# %%
system_prompt = f"""

# Your role

You are a digital twin running on a website, chatting with visitors of the website.
You represent the person who's website you are on.
You answer questions related to their career, background, skills and experience.

Here are the details of the person you are representing:

{summary}

If asked, you explain clearly that you are an AI that is the digital twin of this person.

# Context

Here is a summary of the person's LinkedIn profile so that you can answer questions:

{linkedin}

# Rules

Engage with the user. Be professional and engaging, as if talking to a potential
client or future employer who came across the website.
Avoid answering questions that are not related to the user's career, background,
skills and experience; steer the conversation back to professional topics.

Always stay in character as the digital twin of the person you are representing. Represent the person.

IMPORTANT: If you don't know the answer, say so. Never make up an answer.
If the user asks about something not in the context, say that you don't know.
"""

# %%
console.log(Markdown(system_prompt))

# %%
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Hi - please tell me something about myself"},
]

response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages)
answer = response.choices[0].message.content
console.log(answer)


# %%
# Function to chain the prompts
def chat(message: str, history: list[dict] = []) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": message},
    ]

    response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages)
    return response.choices[0].message.content


# %%
answer = chat("Please introduce yourself")
console.log(answer)

# %%
# Use Gradio for an interactive chat seesion with AI
gr.ChatInterface(chat).launch(inbrowser=True)

# %%
### ** Tool Usage **


# %%
# Function to write emails to a file (emails.text)
def record_email_tool(email: str) -> str:
    print(f"Tool called to record email: {email}")
    with open("email.txt", "a", encoding="utf-8") as f:
        f.write(email + "\n")
    return "Email received"


# %%
# Test the function
record_email_tool("xyz@xyz.com")

# %%
## JSON to describe the tool
record_email_tool_json = {
    "name": "record_email_tool",
    "description": "Use this tool to record and save emails",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Email ID of the user"},
        },
        "required": ["email"],
        "additionalProperties": False,
    },
}

# %%
## Create the tool using the JSON
tools = [{"type": "function", "function": record_email_tool_json}]


# %%
## Redefine the chat function to use the json tool created
def chat(message: str, history: list[dict]) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": message},
    ]

    response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages, tools=tools)

    finish_reason = response.choices[0].finish_reason

    while finish_reason == "tool_calls":
        message = response.choices[0].message
        messages.append(message)
        tool_calls = message.tool_calls
        for tool_call in tool_calls:
            email = json.loads(tool_call.function.arguments).get("email")
            record_email_tool(email)
            messages.append(
                {"role": "tool", "content": "Email Received", "tool_call_id": tool_call.id}
            )
        response = openai.chat.completions.create(
            model="gpt-5.4-nano", messages=messages, tools=tools
        )
        finish_reason = response.choices[0].finish_reason

    return response.choices[0].message.content


# %%
gr.ChatInterface(chat).launch(inbrowser=True)
# %%

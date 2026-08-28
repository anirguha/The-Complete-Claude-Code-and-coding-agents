# %%
import os
from pathlib import Path
import json

import requests
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown


def get_env(*names, default=None):
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def get_env_file(start: Path) -> Path | None:
    """Search for a .env file in the current directory and parent directories."""
    for parent in [start, *start.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No .env file found in the current directory or parent directories.")


load_dotenv(dotenv_path=get_env_file(Path.cwd()), override=True)

# %%
open_ai_api_key = get_env("OPENAI_API_KEY")
if not open_ai_api_key:
    raise RuntimeError("OPENAI_API_KEY is not set. Add it to the environment or a .env file.")

google_api_key = get_env("GOOGLE_API_KEY", "GEMINI_API_KEY")
if not google_api_key:
    raise RuntimeError(
        "GOOGLE_API_KEY or GEMINI_API_KEY is not set. Add it to the environment or a .env file."
    )

anthropic_api_key = get_env("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to the environment or a .env file.")

deepseek_api_key = get_env("DEEPSEEK_API_KEY")
if not deepseek_api_key:
    raise RuntimeError("DEEPSEEK_API_KEY is not set. Add it to the environment or a .env file.")

openrouter_api_key = get_env("OPENROUTER_API_KEY")
if not openrouter_api_key:
    raise RuntimeError("OPENROUTER_API_KEY is not set. Add it to the environment or a .env file.")

# %%

request = (
    "Please come up with a challenging, nuanced question with a succinct answer,\n"
    "that I can ask a number of LLMs to evaluate their intelligence.\n"
    "Not a mathematical puzzle, but more of a thought-provoking question that\n"
    "requires intelligent insight.\n"
    "Include in your question that the answer must be short.\n"
)
request += "Please respond only with the question, and do not include any additional text."

message = [{"role": "user", "content": request}]

openai = OpenAI(api_key=open_ai_api_key)


response = openai.chat.completions.create(
    model="gpt-5.6-luna",
    messages=message,
    max_completion_tokens=300,
    reasoning_effort="none",
)
question = response.choices[0].message.content
# display(question)
console = Console()
console.print(Markdown(f"**Question:** {question}"))

# %%

# OpenAI-compatible clients for each provider
anthropic = OpenAI(api_key=anthropic_api_key, base_url=get_env("ANTHROPIC_BASE_URL"))
deepseek = OpenAI(api_key=deepseek_api_key, base_url=get_env("DEEPSEEK_BASE_URL"))
google = OpenAI(api_key=google_api_key, base_url=get_env("GOOGLE_BASE_URL", "GEMINI_BASE_URL"))
openrouter = OpenAI(api_key=openrouter_api_key, base_url=get_env("OPENROUTER_BASE_URL"))
ollama = OpenAI(
    api_key="ollama",
    base_url=get_env("OLLAMA_BASE_URL", default="http://localhost:11434/v1"),
)

# %%
# Use well-known-or-current model IDs and continue when a provider is unavailable.
competitors = [
    ("OpenAI", openai, "gpt-5.6-luna", {"reasoning_effort": "none"}),
    ("Anthropic", anthropic, "claude-haiku-4-5-20251001", {}),
    ("Google", google, "gemini-3.1-flash-lite", {}),
    (
        "OpenRouter",
        openrouter,
        "openai/gpt-5-nano",
        {"reasoning_effort": "low", "max_completion_tokens": 500},
    ),
    ("Ollama", ollama, "llama3.2:latest", {}),
]

answers = []
# %%
question = [{"role": "user", "content": question}]
# %%

for name, client, model_name, extra_kwargs in competitors:
    request_kwargs = {
        "model": model_name,
        "messages": question,
        "max_completion_tokens": 300,
    }
    request_kwargs.update(extra_kwargs)

    try:
        response = client.chat.completions.create(**request_kwargs)
        answer = response.choices[0].message.content
        answers.append((name, answer))
        console.print(f"[green]{name}[/green]: success with [bold]{model_name}[/bold]")
    except Exception as exc:
        console.print(f"[yellow]{name}[/yellow]: failed with [bold]{model_name}[/bold] -> {exc}")
        continue

if not answers:
    raise RuntimeError(
        "No provider successfully returned a response. Check your API keys and model names."
    )

console.print("\n[bold]Successful answers[/bold]")
for name, answer in answers:
    console.print(f"\n[cyan]{name}[/cyan]\n{answer}")

# %%
models = requests.get("http://localhost:11434/v1/models").json()
for model in models["data"]:
    console.print(f"[white]{model['id']}[/white]")
# %%
console.print(f"[cyan]Question Asked: [/cyan] [white]{question[0]['content']}[/white]")
for model, answer in zip(competitors, answers):
    console.print(f"{model[0]}:\n {answer[1]}\n")
# %%
all_answers = [answer[1] for answer in answers]
all_answers
# %%
judge = f"""You are judging a competition between {len(competitors)} competitors.
Each model has been given this question:

{question[0]["content"]}

Your job is to evaluate each response for clarity and strength of argument, and rank them in order of best to worst.
Respond with JSON, and only JSON, with the following format:
{{"results": ["best competitor number", "second best competitor number", "third best competitor number", ...]}}

Here are the responses from each competitor:

{all_answers}

Now respond with the JSON with the ranked order of the competitors, nothing else. Do not include markdown formatting or code blocks."""

# %%
console.print(judge)
# %%
judge_messages = [{"role": "user", "content": judge}]

# %%
grok = OpenAI(api_key=get_env("GROK_API_KEY"), base_url=get_env("GROK_BASE_URL"))


# %%
model_name = "grok-4.6"
response = grok.responses.create(
    model=model_name,
    input=judge,
    # messages=judge_messages,
    max_output_tokens=4000,
    reasoning={"effort": "low"},
)
# results = response.choices[0].message.content
results = response.output_text
console.print(results)
#
# %%
results_dict = json.loads(results)
ranks = results_dict["results"]
for index, result in enumerate(ranks):
    competitor = competitors[int(result) - 1]
    console.print(f"Rank {index + 1}| API: {competitor[0]} | Model: {competitor[2]}")

# %%

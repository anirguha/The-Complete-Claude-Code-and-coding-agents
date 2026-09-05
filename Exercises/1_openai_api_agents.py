import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(override=True)

openai_api_key = os.getenv("OPENAI_API_KEY")

# if openai_api_key:
#     print(f"OpenAI API Key exists and starts with {openai_api_key[:8]}")
# else:
#     print("OpenAI API Key does not exist")

openai = OpenAI()

# Create a list of messages in the familiar OpenAI format
prompt = (
    "Please suggest a hard challenging question to test someone's IQ. Respond only with question"
)
messages = [{"role": "user", "content": prompt}]

model = "gpt-5-nano"

response_list = openai.chat.completions.create(
    model=model,
    messages=messages,
    max_completion_tokens=300,
    reasoning_effort="minimal",
)
response = response_list.choices[0].message.content
print(response)

messages = [{"role": "user", "content": response}]

response_list = openai.chat.completions.create(
    model=model,
    messages=messages,
    max_completion_tokens=300,
    reasoning_effort="minimal",
)
response = response_list.choices[0].message.content
print(response)


def get_response(prompt: str, model: str = "gpt-5-nano") -> str:
    """
    Get a response from the OpenAI API for a given prompt.

    Args:
        prompt (str): The prompt to send to the OpenAI API.
        model (str): The model to use for the completion. Default is "gpt-5-nano".

    Returns:
        str: The response from the OpenAI API.
    """
    messages = [{"role": "user", "content": prompt}]
    response_list = openai.chat.completions.create(
        model=model,
        messages=messages,
        max_completion_tokens=300,
        reasoning_effort="minimal",
    )
    return response_list.choices[0].message.content


def run_prompt_chain(prompt_templates):
    responses = []

    for i, template in enumerate(prompt_templates):
        if i == 0:
            response = get_response(template)
        else:
            response = get_response(template.format(*responses))
        responses.append(response)

    return responses


results = run_prompt_chain(
    [
        "Please propose a business area that might be worth exploring for an agentic AI "
        "opportunity. Respond only with the business area.",
        "Please provide pain areas in the business area of {0}. Respond only with the pain areas.",
        "Please provide a list of potential solutions to these pain areas in the business area "
        "of {0}: {1}. Respond only with the potential solutions.",
    ]
)

business_area = results[0]
pain_areas = results[1]
solutions = results[2]

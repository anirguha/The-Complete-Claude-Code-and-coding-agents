import context
import tools
from style import CUSTOM_CSS

# `chat()` in tools.py reads `system_prompt` as a module-level global,
# so it must be set before Gradio ever calls it.
tools.system_prompt = context.TWIN_SYSTEM_PROMPT

if __name__ == "__main__":
    tools.call_chat(css=CUSTOM_CSS, title="Digital Twin")

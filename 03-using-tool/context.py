import app as lib
from input import TEST_CASES

lib.print_color("Starting Agentic AI Tool Calling Test", lib.Color.YELLOW)

history_messages = []
for prompt in TEST_CASES:
    response = lib.run_agent_loop(prompt, history_messages)

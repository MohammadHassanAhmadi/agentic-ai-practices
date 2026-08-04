# Agent Loop by Tool Calling

This project demonstrates a simple agent loop that uses tool calling with an OpenAI-compatible API. It exposes two Python functions as tools:

- `count_words`: counts the number of words in a provided text
- `to_uppercase`: converts text to uppercase

The script sends sample prompts through an LLM loop, and when the model decides it needs a tool, the corresponding Python function is executed and its result is returned to the model.

## Features

- Tool-calling agent loop
- Basic prompt examples for single-tool and chained-tool requests
- Logging of user inputs, tool calls, and final answers to `output.txt`

## Requirements

- Python 3.9+
- An Azure OpenAI deployment with the following environment variables configured

## Environment Variables

Create a `.env` file in the project root with:

```env
AZURE_OPENAI_MODEL=your-model-name
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
```

## Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the script:

```bash
python app.py
```

The program will execute several predefined test cases and print the agent interaction flow to the terminal. It will also append the output to `output.txt`.

## Project Files

- `app.py`: main agent loop and tool definitions
- `requirements.txt`: Python dependencies
- `output.txt`: generated log of the agent run

import os

from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

load_dotenv(override=True)
console = Console()
def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def read_file(filename: str) -> str:
    content =""
    try:
        file_path = Path(filename)
        content = file_path.read_text("utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"system prompt file can not be found!")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"the file is not in utf-8") from error      
    return content

client = OpenAI(
    api_key=get_env("AZURE_OPENAI_API_KEY"),
    base_url=get_env("AZURE_OPENAI_ENDPOINT")
)
system_prompt = read_file("systemPrompt.md")

console.print(
    Panel(
        "[bold cyan]Summarization Agent[/bold cyan]\n"
        "Enter some text to summarize.\n"
        "Type [bold yellow]end[/bold yellow] to exit.",
        border_style="cyan",
    )
)

def display_assistant_message(text: str) -> None:
    console.print(
        Panel(
            Markdown(text),
            title="[bold green]Assistant[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

model= get_env("AZURE_OPENAI_MODEL")
while True:
   
    try:
        user_input = Prompt.ask("\n[bold blue]You[/bold blue]").strip()
        if not user_input:
            continue
        if user_input.lower() in {"end", "exit", "quit"}:
            console.print("\n[bold yellow]Goodbye![/bold yellow]")
            break
        
        user_input = {"role": "user", "content":user_input}
        with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
            response = client.responses.create(model=model, instructions = system_prompt, input=user_input)
        display_assistant_message(response.output_text)
        
    
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Goodbye![/bold yellow]")
        break
    
    except Exception as error:
        console.print(
            Panel(
                str(error),
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )

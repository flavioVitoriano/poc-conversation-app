from langchain.tools import tool

@tool("generate_mermaid_diagram")
def generate_mermaid_diagram(mermaid_code: str) -> str:
    """Based on the given mermaid_code, return a url containing an image of the diagram."""
    # TODO: Implement this function
    return "https://corporate-assets.lucid.co/chart/0c1d0622-7089-4745-ac5e-f7ffe2c3014b.svg?v=1707819450630"

@tool("sum_numbers")
def sum_numbers(num1: int, num2: int) -> int:
    """Sum two numbers and return the result."""
    return str(num1 + num2)


available_tools = [generate_mermaid_diagram, sum_numbers]
tools_store = {tool.name: tool for tool in available_tools}
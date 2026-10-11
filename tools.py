from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import Tool
from datetime import datetime


def save_to_txt(data: str, filename: str = "research_output.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"

    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)

    return f"Data successfully saved to {filename}"


save_tool = Tool(
    name="save_text_to_file",
    func=save_to_txt,
    description="Saves structured research data to a text file",
)


def search_web(query: str) -> str:
    """Search the web and return results or a readable error."""
    try:
        search = DuckDuckGoSearchRun(backend="bing")
        result = search.run(query)

        if not result or not result.strip():
            return "Search returned no results. Try a different query."

        return result

    except Exception as e:
        return (
            "Web search failed. "
            f"Error type: {type(e).__name__}. "
            f"Details: {str(e)[:500]}"
        )


search_tool = Tool(
    name="search_web",
    func=search_web,
    description=(
        "Search the web for current products, prices, sales and discounts. "
        "Use targeted queries for Norwegian fashion retailers, including "
        "Ferner Jacobsen and Follestad. Return product names, prices and URLs."
    ),
)

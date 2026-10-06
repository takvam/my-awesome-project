import requests
from bs4 import BeautifulSoup
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
    """Search the web using Bing."""

    url = "https://www.bing.com/search"
    params = {"q": query}
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, params=params, headers=headers, timeout=30)

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for result in soup.select("li.b_algo")[:8]:
        title = result.select_one("h2")
        link = result.select_one("h2 a")
        description = result.select_one(".b_caption p")

        if title and link:
            results.append(
                f"{title.get_text(strip=True)}\n"
                f"{link.get('href')}\n"
                f"{description.get_text(strip=True) if description else ''}"
            )

    if not results:
        return "No search results found."

    return "\n\n".join(results)


search_tool = Tool(
    name="search_web",
    func=search_web,
    description="Search the web using Bing and return relevant web results.",
)

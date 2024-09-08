from duckduckgo_search import DDGS

def search(keywords: str) -> list:
    with DDGS() as ddgs:
        results = ddgs.text( keywords, max_results=3)
        return results

def serpResult2md(results:list) -> str:
    markdown_output = ""
    for result in results:
        title = result.get("title")
        link = result.get("href")
        body = result.get("body")
        if title and link:
            markdown_output += f"- [{title}]({link})\n{body}\n\n"
    return markdown_output

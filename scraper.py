import requests


def get_wikipedia_links(title):
    # The base URL for the Wikipedia API
    url = "https://en.wikipedia.org/w/api.php"

    # The parameters tell Wikipedia exactly what data we want
    params = {
        "action": "query",
        "prop": "links",
        "titles": title,
        "format": "json",
        "pllimit": "max"  # Asks for the maximum number of links allowed per request (500)
    }

    # Send the request and convert the response to a Python dictionary
    response = requests.get(url, params=params)
    data = response.json()

    # Wikipedia's data structure is nested, so we have to dig down to find the links
    pages = data["query"]["pages"]

    for page_id, page_info in pages.items():
        if "links" in page_info:
            # Extract just the title from each link object
            links = [link["title"] for link in page_info["links"]]
            return links

    return []


# Test the function with a seed article
seed = "Graph theory"
print(f"Fetching links for '{seed}'...")

links = get_wikipedia_links(seed)

print(f"Found {len(links)} links. Here are the first 10:")
print(links[:10])
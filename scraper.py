import os
import requests
from collections import deque
import time
import concurrent.futures
from database import get_connection


class WikiScraper:
    def __init__(self, contact=None, max_workers=5, db_name='wiki_graph.db'):
        self.conn = get_connection(db_name)
        # Wikimedia asks API clients to include contact info in the User-Agent.
        # Read it from the environment so no personal address lives in the code.
        contact = contact or os.environ.get("WIKI_GRAPH_CONTACT", "https://github.com/Raisa4/wiki_graph")
        self.headers = {"User-Agent": f"WikiGraphProject/1.0 ({contact})"}
        self.max_workers = max_workers

        self.pages_processed = 0
        self.links_found = 0
        self.start_time = 0

    def fetch_links(self, title):
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "prop": "links",
            "titles": title,
            "format": "json",
            "pllimit": "max",
            "redirects": 1
        }

        for attempt in range(3):
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=10)
                if response.status_code == 429:
                    time.sleep(int(response.headers.get("Retry-After", 5)))
                    continue

                response.raise_for_status()
                pages = response.json()["query"]["pages"]

                for page_id, page_info in pages.items():
                    if "links" in page_info:
                        return [link["title"] for link in page_info["links"]]
                return []
            except requests.exceptions.RequestException:
                time.sleep(2)
        return []

    def run(self, seed, max_pages):
        self.start_time = time.time()
        cursor = self.conn.cursor()
        queue = deque([seed])

        cursor.execute('INSERT OR IGNORE INTO articles (title, visited) VALUES (?, 0)', (seed,))
        self.conn.commit()

        print(f"Starting crawl from '{seed}' (Target: {max_pages} pages)")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while queue and self.pages_processed < max_pages:
                batch = []

                while queue and len(batch) < self.max_workers and (self.pages_processed + len(batch)) < max_pages:
                    title = queue.popleft()
                    cursor.execute('SELECT visited FROM articles WHERE title = ?', (title,))
                    result = cursor.fetchone()

                    if result and result[0] == 1:
                        continue
                    batch.append(title)

                if not batch:
                    break

                results = list(executor.map(self.fetch_links, batch))

                for current_title, links in zip(batch, results):
                    self.links_found += len(links)
                    for link in links:
                        cursor.execute('INSERT OR IGNORE INTO edges (source_title, target_title) VALUES (?, ?)',
                                       (current_title, link))
                        cursor.execute('INSERT OR IGNORE INTO articles (title, visited) VALUES (?, 0)', (link,))
                        queue.append(link)

                    cursor.execute('UPDATE articles SET visited = 1 WHERE title = ?', (current_title,))
                    self.pages_processed += 1

                self.conn.commit()
                time.sleep(0.5)

        self.print_statistics()

    def print_statistics(self):
        elapsed = time.time() - self.start_time
        rate = self.pages_processed / elapsed if elapsed > 0 else 0

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_nodes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM edges")
        total_edges = cursor.fetchone()[0]

        print("\n" + "=" * 30)
        print(" SCRAPE COMPLETE - STATISTICS")
        print("=" * 30)
        print(f"Total Time:      {elapsed:.2f} seconds")
        print(f"Pages Processed: {self.pages_processed}")
        print(f"Speed:           {rate:.2f} pages/sec")
        print("-" * 30)
        print(f"Total Nodes:     {total_nodes}")
        print(f"Total Edges:     {total_edges}")
        print("=" * 30 + "\n")


if __name__ == "__main__":
    scraper = WikiScraper(max_workers=5)
    # You can leave this at a small number since you already built your dataset
    scraper.run(seed="Graph theory", max_pages=5)
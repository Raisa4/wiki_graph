import logging
import os
import requests
from collections import deque
import time
import concurrent.futures
from database import get_connection

logger = logging.getLogger(__name__)


class WikiScraper:
    def __init__(self, contact=None, max_workers=5, db_name='wiki_graph.db'):
        self.conn = get_connection(db_name)
        # Wikimedia asks API clients to include contact info in the User-Agent.
        # Read it from the environment so no personal address lives in the code.
        contact = contact or os.environ.get("WIKI_GRAPH_CONTACT", "https://github.com/Raisa4/wiki_graph")
        self.headers = {"User-Agent": f"WikiGraphProject/1.0 ({contact})"}
        self.max_workers = max_workers

        self.pages_processed = 0
        self.pages_failed = 0
        self.links_found = 0
        self.start_time = 0

    API_URL = "https://en.wikipedia.org/w/api.php"

    def _get_json(self, params):
        """GET the API with retries. Returns the parsed JSON, or None after 3 failed attempts."""
        for attempt in range(3):
            try:
                response = requests.get(self.API_URL, params=params, headers=self.headers, timeout=10)
                if response.status_code == 429:
                    wait = int(response.headers.get("Retry-After", 5))
                    logger.warning("Rate limited (429), waiting %ds before retrying", wait)
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()
            except (requests.exceptions.RequestException, ValueError) as exc:
                logger.warning("Request failed (attempt %d/3): %s", attempt + 1, exc)
                time.sleep(2)
        return None

    def fetch_links(self, title):
        """Return every article (namespace 0) linked from `title`, or None if the fetch failed."""
        params = {
            "action": "query",
            "prop": "links",
            "titles": title,
            "format": "json",
            "pllimit": "max",
            "plnamespace": 0,  # only real articles, not Talk:, Category:, Template:, ...
            "redirects": 1
        }

        links = []
        while True:
            data = self._get_json(params)
            if data is None:
                # None (not []) so the caller can tell "fetch failed" from "page has no links"
                return None

            try:
                pages = data["query"]["pages"]
            except KeyError:
                return None

            for page_info in pages.values():
                links.extend(link["title"] for link in page_info.get("links", []))

            # pllimit=max returns at most 500 links per call; follow the continuation token.
            if "continue" not in data:
                return links
            params = {**params, **data["continue"]}

    def _load_queue(self, seed):
        """Rebuild the BFS queue from the database so an interrupted crawl can resume.

        Unvisited articles are loaded in insertion order (rowid), which matches the
        order they were discovered. The seed is only added if it has never been seen.
        """
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO articles (title, visited) VALUES (?, 0)', (seed,))
        self.conn.commit()

        cursor.execute('SELECT title FROM articles WHERE visited = 0 ORDER BY rowid')
        return deque(row[0] for row in cursor.fetchall())

    def run(self, seed, max_pages):
        self.start_time = time.time()
        cursor = self.conn.cursor()
        queue = self._load_queue(seed)

        logger.info("Starting crawl from '%s' (target: %d pages, %d queued)", seed, max_pages, len(queue))

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
                    if links is None:
                        # Leave visited = 0 so a later run retries this page.
                        self.pages_failed += 1
                        logger.error("Failed to fetch '%s', will retry on next run", current_title)
                        continue

                    self.links_found += len(links)
                    for link in links:
                        cursor.execute('INSERT OR IGNORE INTO edges (source_title, target_title) VALUES (?, ?)',
                                       (current_title, link))
                        cursor.execute('INSERT OR IGNORE INTO articles (title, visited) VALUES (?, 0)', (link,))
                        # The articles table doubles as the "seen" set: only brand-new titles get queued.
                        if cursor.rowcount == 1:
                            queue.append(link)

                    cursor.execute('UPDATE articles SET visited = 1 WHERE title = ?', (current_title,))
                    self.pages_processed += 1

                self.conn.commit()
                logger.debug("Processed %d/%d pages, queue size %d", self.pages_processed, max_pages, len(queue))
                time.sleep(0.5)

        self.log_statistics()

    def log_statistics(self):
        elapsed = time.time() - self.start_time
        rate = self.pages_processed / elapsed if elapsed > 0 else 0

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_nodes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM edges")
        total_edges = cursor.fetchone()[0]

        logger.info(
            "Crawl complete: %d pages in %.2fs (%.2f pages/sec), %d failed. "
            "Database now has %d nodes and %d edges.",
            self.pages_processed, elapsed, rate, self.pages_failed, total_nodes, total_edges)

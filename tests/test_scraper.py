from unittest.mock import MagicMock

import pytest
import requests

import scraper as scraper_module
from scraper import WikiScraper


def make_response(status=200, json_data=None, headers=None):
    response = MagicMock()
    response.status_code = status
    response.headers = headers or {}
    response.json.return_value = json_data
    if status >= 400 and status != 429:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(str(status))
    return response


def links_payload(titles, cont=None):
    data = {"query": {"pages": {"123": {"title": "X", "links": [{"ns": 0, "title": t} for t in titles]}}}}
    if cont:
        data["continue"] = cont
    return data


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # Retries and the crawl loop call time.sleep; make tests instant.
    monkeypatch.setattr(scraper_module.time, "sleep", lambda s: None)


@pytest.fixture
def scraper():
    s = WikiScraper(db_name=":memory:", contact="test@example.com")
    yield s
    s.conn.close()


def test_429_then_200_retries_and_succeeds(scraper, monkeypatch):
    mock_get = MagicMock(side_effect=[
        make_response(429, headers={"Retry-After": "1"}),
        make_response(200, links_payload(["Alpha", "Beta"])),
    ])
    monkeypatch.setattr(scraper_module.requests, "get", mock_get)

    assert scraper.fetch_links("Graph theory") == ["Alpha", "Beta"]
    assert mock_get.call_count == 2


def test_results_across_continuation_pages_are_merged(scraper, monkeypatch):
    mock_get = MagicMock(side_effect=[
        make_response(200, links_payload(["A", "B"], cont={"plcontinue": "123|0|C", "continue": "||"})),
        make_response(200, links_payload(["C", "D"])),
    ])
    monkeypatch.setattr(scraper_module.requests, "get", mock_get)

    assert scraper.fetch_links("Big article") == ["A", "B", "C", "D"]

    first_params = mock_get.call_args_list[0].kwargs["params"]
    second_params = mock_get.call_args_list[1].kwargs["params"]
    assert "plcontinue" not in first_params
    assert second_params["plcontinue"] == "123|0|C"
    assert second_params["plnamespace"] == 0


def test_request_uses_timeout(scraper, monkeypatch):
    mock_get = MagicMock(return_value=make_response(200, links_payload([])))
    monkeypatch.setattr(scraper_module.requests, "get", mock_get)

    scraper.fetch_links("Anything")
    assert mock_get.call_args.kwargs["timeout"] == 10


def test_failure_returns_none(scraper, monkeypatch):
    mock_get = MagicMock(side_effect=requests.exceptions.ConnectionError("down"))
    monkeypatch.setattr(scraper_module.requests, "get", mock_get)

    assert scraper.fetch_links("Graph theory") is None
    assert mock_get.call_count == 3


def test_page_without_links_returns_empty_list(scraper, monkeypatch):
    payload = {"query": {"pages": {"1": {"title": "Stub"}}}}
    monkeypatch.setattr(scraper_module.requests, "get", MagicMock(return_value=make_response(200, payload)))

    assert scraper.fetch_links("Stub") == []


def visited(scraper, title):
    row = scraper.conn.execute("SELECT visited FROM articles WHERE title = ?", (title,)).fetchone()
    return row[0] if row else None


def test_crawl_does_not_mark_failed_pages_visited(scraper, monkeypatch):
    fake_links = {"Seed": ["Good", "Bad"], "Good": [], "Bad": None}
    monkeypatch.setattr(scraper, "fetch_links", lambda title: fake_links[title])

    scraper.run(seed="Seed", max_pages=10)

    assert visited(scraper, "Seed") == 1
    assert visited(scraper, "Good") == 1
    assert visited(scraper, "Bad") == 0
    assert scraper.pages_failed == 1


def test_crawl_queues_each_title_once(scraper, monkeypatch):
    # Both A and B link to C; C must only be fetched once.
    fake_links = {"Seed": ["A", "B"], "A": ["C"], "B": ["C"], "C": ["A"]}
    fetched = []

    def fake_fetch(title):
        fetched.append(title)
        return fake_links[title]

    monkeypatch.setattr(scraper, "fetch_links", fake_fetch)
    scraper.max_workers = 1  # deterministic order

    scraper.run(seed="Seed", max_pages=10)

    assert sorted(fetched) == ["A", "B", "C", "Seed"]


def test_crawl_resumes_from_unvisited_articles(scraper, monkeypatch):
    # Simulate a previous run that visited Seed and discovered A and B.
    scraper.conn.executemany("INSERT INTO articles (title, visited) VALUES (?, ?)",
                             [("Seed", 1), ("A", 0), ("B", 0)])
    scraper.conn.commit()

    fetched = []
    monkeypatch.setattr(scraper, "fetch_links", lambda title: fetched.append(title) or [])

    scraper.run(seed="Seed", max_pages=10)

    assert sorted(fetched) == ["A", "B"]

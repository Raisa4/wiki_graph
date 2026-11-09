"""Command-line entry point.

    python main.py crawl --seed "Graph theory" --max-pages 500
    python main.py analyze --top 300
"""
import argparse


def build_parser():
    parser = argparse.ArgumentParser(description="Crawl Wikipedia links and visualize the resulting graph.")
    parser.add_argument("--db", default="wiki_graph.db", help="SQLite database file (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    crawl = sub.add_parser("crawl", help="Breadth-first crawl of Wikipedia links into the database")
    crawl.add_argument("--seed", default="Graph theory", help="Article to start from (default: %(default)s)")
    crawl.add_argument("--max-pages", type=int, default=500, help="Pages to fetch this run (default: %(default)s)")
    crawl.add_argument("--workers", type=int, default=5, help="Parallel fetch threads (default: %(default)s)")
    crawl.add_argument("--contact", help="Contact info for the User-Agent (default: $WIKI_GRAPH_CONTACT)")

    analyze = sub.add_parser("analyze", help="Rank articles, lay out the top ones and open the viewer")
    analyze.add_argument("--top", type=int, default=300, help="Number of hottest nodes to draw (default: %(default)s)")
    analyze.add_argument("--iterations", type=int, default=50, help="Layout iterations (default: %(default)s)")
    analyze.add_argument("--width", type=int, default=800)
    analyze.add_argument("--height", type=int, default=600)
    analyze.add_argument("--screenshot", metavar="PATH", help="Save the first frame as an image and exit")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    # Imported lazily so `crawl` doesn't need pygame and `analyze` doesn't need requests.
    if args.command == "crawl":
        from scraper import WikiScraper
        WikiScraper(contact=args.contact, max_workers=args.workers, db_name=args.db).run(
            seed=args.seed, max_pages=args.max_pages)
    elif args.command == "analyze":
        from analyzer import analyze
        analyze(db_name=args.db, top=args.top, iterations=args.iterations,
                width=args.width, height=args.height, screenshot=args.screenshot)


if __name__ == "__main__":
    main()

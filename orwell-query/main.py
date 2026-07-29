import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path

FUSEKI_URL = "http://localhost:3030/ds/sparql"
QUERY_DIR = Path(__file__).parent / "query"
DEFAULT_TIMEOUT = 60


@dataclass
class QueryResult:
    name: str
    rows: list[dict] = field(default_factory=list)
    error: str | None = None
    elapsed: float = 0.0

    @property
    def ok(self) -> bool:
        return self.error is None


def load_queries(query_dir: Path) -> dict[str, str]:
    if not query_dir.is_dir():
        raise FileNotFoundError(f"Query directory not found: {query_dir}")
    queries = {f.stem: f.read_text().strip() for f in sorted(query_dir.glob("*.rq"))}
    if not queries:
        raise ValueError(f"No .rq files found in {query_dir}")
    return queries


def run_query(sparql_query: str, url: str = FUSEKI_URL, timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    data = urllib.parse.urlencode({"query": sparql_query}).encode()
    req = urllib.request.Request(url, data=data, headers={"Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        results = json.loads(resp.read())
    return [
        {k: v["value"] for k, v in binding.items()}
        for binding in results.get("results", {}).get("bindings", [])
    ]


def execute(name: str, sparql_query: str, url: str = FUSEKI_URL) -> QueryResult:
    start = time.perf_counter()
    try:
        rows = run_query(sparql_query, url=url)
        return QueryResult(name=name, rows=rows, elapsed=time.perf_counter() - start)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            msg = json.loads(body).get("message", body)
        except json.JSONDecodeError:
            msg = body
        return QueryResult(name=name, error=f"HTTP {e.code} {e.reason}: {msg}", elapsed=time.perf_counter() - start)
    except Exception as e:
        return QueryResult(name=name, error=str(e), elapsed=time.perf_counter() - start)


def print_table(rows: list[dict]) -> None:
    if not rows:
        print("  (no rows)")
        return

    columns = list(rows[0].keys())
    widths = {col: max(len(col), max(len(str(row.get(col, ""))) for row in rows)) for col in columns}

    def fmt_row(values: list[str]) -> str:
        return "  " + " │ ".join(str(v).ljust(widths[col]) for col, v in zip(columns, values))

    separator = "  " + "─┼─".join("─" * widths[col] for col in columns)

    print(fmt_row(columns))
    print(separator)
    for row in rows:
        print(fmt_row([row.get(col, "") for col in columns]))


def print_result(result: QueryResult) -> None:
    print(f"{'═' * 60}")
    print(f"  Query:   {result.name}")
    print(f"  Elapsed: {result.elapsed:.2f}s")
    print(f"{'═' * 60}\n")
    if result.ok:
        print_table(result.rows)
        print(f"\n  {len(result.rows)} rows\n")
    else:
        print(f"  ERROR: {result.error}\n")


def main() -> int:
    url = FUSEKI_URL

    try:
        queries = load_queries(QUERY_DIR)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    names = sys.argv[1:]
    selected = {}
    for name in (names or queries):
        if name not in queries:
            print(f"Unknown query: {name}", file=sys.stderr)
        else:
            selected[name] = queries[name]

    results = [execute(name, query, url=url) for name, query in selected.items()]
    for result in results:
        print_result(result)

    total = sum(r.elapsed for r in results)
    failures = [r for r in results if not r.ok]
    print(f"{'─' * 60}")
    print(f"  {len(results)} queries in {total:.2f}s — {len(failures)} failed")
    print(f"{'─' * 60}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

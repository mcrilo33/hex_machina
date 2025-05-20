""" Analysis functions for the TTD pipeline. """
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
from datetime import datetime
from typing import List, Optional
from email.utils import parsedate_to_datetime, format_datetime

from ttd.ingestion.parser import extract_domain


EXTENDED_PASTELS = [
    "lightcoral", "skyblue", "plum", "khaki", "salmon", "lightsalmon", "palegoldenrod",
    "lightsteelblue", "thistle", "peachpuff", "mistyrose", "powderblue", "lavender", "wheat",
    "lightcyan", "lemonchiffon", "honeydew", "mintcream", "azure", "seashell",
    "pink", "lightblue", "moccasin", "navajowhite", "cornsilk", "oldlace", "beige",
    "blanchedalmond", "gainsboro", "aliceblue"
]  # ~30 soft pastel tones

def generate_status_color_map(statuses):
    """
    Map statuses to colors: "No Error" gets lightgreen, others get unique pastel colors.
    """
    color_map = {}
    for i, status in enumerate(statuses):
        if status == "No Error":
            color_map[status] = "lightgreen"
        else:
            color_map[status] = EXTENDED_PASTELS[i % len(EXTENDED_PASTELS)]
    return color_map

def get_oldest_and_latest_dates(articles: List[dict]) -> tuple[Optional[str], Optional[str]]:
    """Return the oldest and most recent published_date as RFC 1123 strings."""
    dates = []
    for article in articles:
        pub_date = article.get("published_date")
        try:
            dt = parsedate_to_datetime(pub_date)
            dates.append(dt)
        except Exception:
            continue

    if not dates:
        return None, None

    oldest = format_datetime(min(dates))
    latest = format_datetime(max(dates))
    return oldest, latest

def get_articles_with_no_error(articles):
    articles_with_no_error = []
    for article in articles:
        if not article.get("metadata", {}).get("error"):
            articles_with_no_error.append(article)

    return articles_with_no_error

def get_reference_domains(path: Path) -> set:
    with open(path) as f:
        return set(extract_domain(line.strip()) for line in f if line.strip())

def format_duration(seconds: float) -> str:
    """Convert duration in seconds into a human-readable string."""
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"

    mins, secs = divmod(seconds, 60)
    if mins < 60:
        return f"{mins}m {secs}s"

    hrs, mins = divmod(mins, 60)
    return f"{hrs}h {mins}m {secs}s"

def prepare_domain_counts(articles):
    return Counter(
        a["url_domain"] for a in articles if a.get("url_domain")
    )

def prepare_field_coverage(articles):
    """Returns a dict: field → (count, percent) over all articles."""
    total = len(articles)
    if total == 0:
        return {}

    field_counts = Counter()
    for article in articles:
        for field, value in article.items():
            if value not in (None, '', [], {}):
                field_counts[field] += 1

    return {
        field: (count, (count / total) * 100)
        for field, count in field_counts.items()
    }

def prepare_article_distribution_indexed_by_date(
    articles: list,
    date_parser=None,
    n_months: int = None
) -> pd.DataFrame:
    records = []

    for art in articles:
        pub_date = art.get("published_date")
        domain = art.get("url_domain", "Unknown")

        try:
            dt = (
                parsedate_to_datetime(pub_date)
                if date_parser is None
                else date_parser(pub_date)
            )
            records.append({"date": dt, "domain": domain})
        except Exception:
            continue

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], utc=True)
    if n_months is not None:
        cutoff = datetime.now(df["date"].dt.tz) - pd.DateOffset(months=n_months)
        df = df[df["date"] >= cutoff]
        if df.empty:
            return df

    df.set_index("date", inplace=True)
    grouped = df.groupby([pd.Grouper(freq="D"), "domain"]).size().unstack(fill_value=0)
    return grouped

def prepare_error_distribution_by_domain_and_status(articles):
    """Extract and group article error statuses by domain."""
    records = []
    for article in articles:
        metadata = article.get("metadata", {})
        error = metadata.get("error")
        status = error["status"] if error else "No Error"
        domain = article.get("url_domain", "Unknown")
        records.append({"domain": domain, "status": status})

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    grouped = df.groupby(["domain", "status"]).size().unstack(fill_value=0)
    return grouped

def plot_article_distribution_indexed_by_date(grouped_df: pd.DataFrame) -> plt.Figure:
    statuses = grouped_df.columns.tolist()
    color_map = generate_status_color_map(statuses)
    colors = [color_map[status] for status in statuses]

    fig, ax = plt.subplots(figsize=(12, 5))
    grouped_df.plot(kind="bar", stacked=True, ax=ax, color=colors)
    ax.set_title("Articles per Day by Domain")
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Articles")
    plt.xticks(rotation=45)
    ax.legend(
        loc='center left',
        bbox_to_anchor=(1.0, 0.5),
        borderaxespad=0.5,
        title="Domains",
        fontsize="xx-small"  # 👈 smallest readable font
    )
    plt.tight_layout()
    return fig

def plot_error_distribution_by_domain_and_status(grouped_df: pd.DataFrame) -> plt.Figure:
    """Create a stacked bar chart from grouped error data."""
    statuses = grouped_df.columns.tolist()
    color_map = generate_status_color_map(statuses)
    colors = [color_map[status] for status in statuses]

    fig, ax = plt.subplots(figsize=(12, 6))
    grouped_df.plot(kind="bar", stacked=True, ax=ax, color=colors)
    ax.set_title("Errors by Domain and Status")
    ax.set_xlabel("URL Domain")
    ax.set_ylabel("Number of Errors")
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def generate_domain_match_markdown(domain_counts, reference_domains, label):
    lines = [f"### 📋 Domain Match Check — {label}", ""]
    lines.append("| Match | Domain | Article Count |")
    lines.append("|-------|--------|----------------|")
    sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)

    for domain, count in sorted_domains:
        if domain in reference_domains:
            lines.append(f"| [✅] | `{domain}` | {count} |")
    for domain in reference_domains:
        if domain not in domain_counts:
            lines.append(f"| [❌] | `{domain}` | 0 |")
    return "\n".join(lines)

def generate_field_coverage_markdown(field_coverage, total):
    if not field_coverage:
        return "_No articles or no fields to report._"

    # Sort fields by descending coverage percentage
    sorted_fields = sorted(field_coverage.items(), key=lambda x: x[1][1], reverse=True)

    lines = [f"### 📊 Field Coverage Report ({total} articles)", ""]
    lines.append("| Field | Count | Coverage |")
    lines.append("|-------|--------|----------|")
    for field, (count, percent) in sorted_fields:
        if field in [
            'title', 'published_date', 'url_domain', 'html_content_artifact',
            'summary', 'author', 'tags'
        ]:
            lines.append(f"| `{field}` | {count} | {percent:.1f}% |")

    return "\n".join(lines)

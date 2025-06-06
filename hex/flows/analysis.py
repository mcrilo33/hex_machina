""" Analysis functions for the Hex pipeline. """
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
from datetime import datetime
from typing import List, Optional, Tuple
from email.utils import parsedate_to_datetime, format_datetime
import numpy as np
import os
import uuid

from hex.ingestion.parser import extract_domain


EXTENDED_PASTELS = [
    "lightcoral", "skyblue", "plum", "khaki", "salmon", "lightsalmon", "palegoldenrod",
    "lightsteelblue", "thistle", "peachpuff", "mistyrose", "powderblue", "lavender", "wheat",
    "lightcyan", "lemonchiffon", "honeydew", "mintcream", "azure", "seashell",
    "pink", "lightblue", "moccasin", "navajowhite", "cornsilk", "oldlace", "beige",
    "blanchedalmond", "gainsboro", "aliceblue"
]  # ~30 soft pastel tones

def save_plot(fig, title: str) -> str:
    plot_dir = "/tmp/metaflow_reports"
    os.makedirs(plot_dir, exist_ok=True)
    filename = os.path.join(plot_dir, f"{uuid.uuid4().hex}_{title}.png")
    fig.savefig(filename, bbox_inches='tight')
    plt.close(fig)
    return filename

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

def get_domain_table_data(articles: list) -> list:
    """
    Given a list of article dicts, return domain_table_data:
    [domain, ai_count, ai_rate, top_clusters_str]
    """
    df = pd.DataFrame(articles)
    domain_table_data = []

    required_cols = [
        "url_domain",
        "is_ai_added",
        "clusters_names_in_order_added"
    ]
    if not all(col in df.columns for col in required_cols):
        return domain_table_data

    for domain, group in df.groupby("url_domain"):
        total_articles = len(group)
        ai_count = group["is_ai_added"].astype(int).sum()
        ai_rate = ai_count / total_articles if total_articles > 0 else 0

        # count clusters
        cluster_counter = Counter()
        for cluster_list in group["clusters_names_in_order_added"]:
            if isinstance(cluster_list, list):
                cluster_counter.update(cluster_list)

        top_clusters = cluster_counter.most_common(5)
        top_clusters_str = ", ".join(
            f"{name}: {count / total_articles:.1%}"
            for name, count in top_clusters
        ) if top_clusters else "n/a"

        domain_table_data.append([
            domain,
            int(ai_count),
            f"{ai_rate:.1%}",
            top_clusters_str
        ])

    # sort table by ai count descending
    # Convert to DataFrame with proper column names
    df = pd.DataFrame(
        domain_table_data,
        columns=["domain", "ai count", "ai rate", "top 5 clusters with rate"]
    )
    # Sort by ai count descending
    df = df.sort_values("ai count", ascending=False)
    return df

def filter_articles_by_clusters(articles: list, filtered_clusters: list) -> list:
    """
    Filter articles to only include specified clusters in their cluster_names_in_order_added field.
    """
    filtered_articles = []
    
    for article in articles:
        if "clusters_names_in_order_added" not in article:
            filtered_articles.append(article)
            continue
            
        clusters = article["clusters_names_in_order_added"]
        if not isinstance(clusters, list):
            filtered_articles.append(article)
            continue
            
        filtered_clusters_list = [c for c in clusters if c not in filtered_clusters]
        
        filtered_article = article.copy()
        filtered_article["clusters_names_in_order_added"] = filtered_clusters_list
        filtered_articles.append(filtered_article)
        
    return filtered_articles

def plot_summary_distributions(articles: list) -> Optional[plt.Figure]:
    """
    Plot summary statistics distributions for a list of articles.
    Returns a matplotlib Figure or None if required data is missing.
    """
    if not articles:
        return None
    df = pd.DataFrame(articles)
    required_cols = [
        "dense_summary_length_added",
        "text_content_length",
        "core_line_summary_length_added",
        "title_vs_core_rouge_eval"
    ]
    if not all(col in df.columns for col in required_cols):
        return None

    # compute ratio
    ratio = df["dense_summary_length_added"] / df["text_content_length"]
    core_lengths = df["core_line_summary_length_added"]
    rouge_scores = df["title_vs_core_rouge_eval"]

    # clean up nans/infs
    ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()
    core_lengths = core_lengths.dropna()
    rouge_scores = rouge_scores.dropna()

    fig, axes = plt.subplots(1, 3, figsize=(12, 5))

    axes[0].hist(ratio, bins=20, color='skyblue', edgecolor='black')
    axes[0].set_title("dense Summary Length Ratio")
    axes[0].set_xlabel("dense_summary_length_added / text_content_length")
    axes[0].set_ylabel("Number of Articles")

    axes[1].hist(core_lengths, bins=20, color='lightgreen', edgecolor='black')
    axes[1].set_title("Core Line Summary Length")
    axes[1].set_xlabel("core_line_summary_length_added")
    axes[1].set_ylabel("Number of Articles")

    axes[2].hist(rouge_scores, bins=20, color='lightcoral', edgecolor='black')
    axes[2].set_title("Rouge Score for Title vs Core Line")
    axes[2].set_xlabel("title_vs_core_rouge_eval")
    axes[2].set_ylabel("Number of Articles")

    fig.tight_layout()
    return fig

def get_rouge_top_bottom(articles: list) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Given a list of articles, return (bottom5, top5) DataFrames sorted by 'title_vs_core_rouge_eval'.
    Returns empty DataFrames if required columns are missing.
    """
    if not articles:
        return pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(articles)
    required_cols = ["title", "core_line_summary_added", "title_vs_core_rouge_eval"]
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame(), pd.DataFrame()
    eval_df = df[required_cols].dropna()
    eval_df = df[required_cols].dropna()
    if eval_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    sorted_df = eval_df.sort_values("title_vs_core_rouge_eval")
    bottom5 = sorted_df.head(5)
    top5 = sorted_df.tail(5)
    return bottom5, top5

def generate_tag_cluster_summary_markdown(articles: list) -> tuple[str, dict]:
    """
    Given a list of article dicts, return (markdown, summary_dict) for tags/clusters summary.
    """
    import numpy as np
    import pandas as pd
    from collections import Counter

    df = pd.DataFrame(articles)
    required_cols = ["tags_pred_added", "clusters_names_in_order_added", "is_ai_added"]
    if not all(col in df.columns for col in required_cols):
        return (
            "_Missing `tags_pred_added` or `clusters_names_in_order_added` column to compute tags/clusters summary._",
            {},
        )

    tags_per_article = []
    clusters_per_article = []
    all_clusters = set()

    for _, row in df.iterrows():
        is_ai = row.get("is_ai_added", [])
        if is_ai is False:
            continue
        tags = row.get("tags_pred_added", [])
        clusters = row.get("clusters_names_in_order_added", [])

        # Clean and count
        if not isinstance(tags, list):
            tags = []
        if not isinstance(clusters, list):
            clusters = []

        tags = [t for t in tags if isinstance(t, str)]
        clusters = [c for c in clusters if isinstance(c, str)]

        tags_per_article.append(len(tags))
        clusters_per_article.append(len(set(clusters)))
        all_clusters.update(clusters)

    total_tags = sum(tags_per_article)
    total_clusters = len(all_clusters)
    avg_tags_per_article = float(np.mean(tags_per_article)) if tags_per_article else 0.0
    avg_clusters_per_article = float(np.mean(clusters_per_article)) if clusters_per_article else 0.0

    md = f"""
**Total Tags (across all articles)**: {total_tags}  
**Total Clusters (distinct)**: {total_clusters}  
**Avg Tags per Article**: {avg_tags_per_article:.2f}  
**Avg Clusters per Article**: {avg_clusters_per_article:.2f}
"""
    summary = {
        "total_tags": total_tags,
        "total_clusters": total_clusters,
        "avg_tags_per_article": avg_tags_per_article,
        "avg_clusters_per_article": avg_clusters_per_article,
    }
    return md, summary

def plot_tag_similarity_distribution(articles: list) -> Optional[plt.Figure]:
    """
    Plot the distribution of tag similarity scores for a list of articles.
    Returns a matplotlib Figure or None if required data is missing.
    """
    if not articles:
        return None
    df = pd.DataFrame(articles)
    if "tag_similarity_eval" not in df.columns:
        return None
    df["tag_similarity_eval"].dropna(inplace=True)
    df = df[df["tag_similarity_eval"]>0]
    similarity_scores = df["tag_similarity_eval"]
    if similarity_scores.empty:
        fig = None
    else:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(similarity_scores, bins=20, color='mediumpurple', edgecolor='black')
        ax.set_title("Distribution of tag_similarity_eval")
        ax.set_xlabel("tag_similarity_eval")
        ax.set_ylabel("Number of Articles")
        fig.tight_layout()

    def format_row(row):
        return [
            row.get("title", "N/A"),
            ", ".join(row.get("tags", [])) if isinstance(row.get("tags"), list) else "N/A",
            ", ".join(row.get("tags_pred_added", [])) if isinstance(row.get("tags_pred_added"), list) else "N/A",
            f"{row.get('tag_similarity_eval', 0):.3f}"
        ]
    sorted_df = df.dropna(subset=["tag_similarity_eval"]).sort_values("tag_similarity_eval")
    top_5 = sorted_df.tail(5)
    top_5 = pd.DataFrame(
        [format_row(row) for _, row in top_5.iterrows()],
        columns=["Title", "Tags", "Predicted Tags", "Similarity"]
    )
    bottom_5 = sorted_df.head(5)
    bottom_5 = pd.DataFrame(
        [format_row(row) for _, row in bottom_5.iterrows()],
        columns=["Title", "Tags", "Predicted Tags", "Similarity"]
    )

    return fig, top_5, bottom_5

def plot_top_clusters_histogram(articles: list, top_n: int = 20) -> Optional[plt.Figure]:
    """
    Plot a histogram of the top N clusters across all articles.
    Returns a matplotlib Figure or None if required data is missing.
    """
    if not articles:
        return None
    df = pd.DataFrame(articles)
    if "clusters_names_in_order_added" not in df.columns:
        return None
    # Flatten all cluster lists into one big list
    all_clusters = []
    for cluster_list in df["clusters_names_in_order_added"].dropna():
        if isinstance(cluster_list, list):
            all_clusters.extend(cluster_list)
    if not all_clusters:
        return None
    cluster_counts = Counter(all_clusters)
    top_n_clusters = cluster_counts.most_common(top_n)
    if not top_n_clusters:
        return None
    clusters, counts = zip(*top_n_clusters)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(clusters, counts, color='skyblue', edgecolor='black')
    ax.set_title(f"Top {top_n} Clusters in Articles")
    ax.set_ylabel("Count")
    ax.set_xticks(range(len(clusters)))
    ax.set_xticklabels(clusters, rotation=45, ha='right')
    fig.tight_layout()
    return fig
    
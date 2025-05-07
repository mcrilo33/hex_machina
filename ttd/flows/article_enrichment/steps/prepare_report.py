import logging
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from collections import Counter
from typing import Dict, List, Any, Optional
from metaflow.cards import Markdown, Table, Image
from metaflow import current, step, card
import os
import uuid
from PIL import Image as PILImage

def combine_images_horizontally(path1: str, path2: str) -> bytes:
    img1 = PILImage.open(path1)
    img2 = PILImage.open(path2)

    # Match height
    if img1.height != img2.height:
        new_height = max(img1.height, img2.height)
        img1 = img1.resize((img1.width, new_height))
        img2 = img2.resize((img2.width, new_height))

    combined = PILImage.new("RGB", (img1.width + img2.width, img1.height))
    combined.paste(img1, (0, 0))
    combined.paste(img2, (img1.width, 0))

    from io import BytesIO
    buf = BytesIO()
    combined.save(buf, format="PNG")
    return buf.getvalue()

def save_plot(fig, title: str) -> str:
    plot_dir = "/tmp/metaflow_reports"
    os.makedirs(plot_dir, exist_ok=True)
    filename = os.path.join(plot_dir, f"{uuid.uuid4().hex}_{title}.png")
    fig.savefig(filename, bbox_inches='tight')
    plt.close(fig)
    return filename

def load_image(path: str) -> Image:
    with open(path, "rb") as f:
        return Image(f.read())

logger = logging.getLogger(__name__)

@card(type='default')
@step
def execute(flow) -> None:
    """Generate a detailed report from replicated articles."""
    logger.info("📊 Generating report from replicated articles...")

    # Ensure we have data to work with
    if not hasattr(flow, 'replicated_articles') or not flow.replicated_articles:
        logger.warning("No replicated articles found to generate report")
        flow.report = {"error": "No replicated articles data available"}
        return

    df = pd.DataFrame(flow.replicated_articles)
    flow.report = {}

    # --- Article Enrichment Report ---
    total_articles = len(df)
    ai_articles = df['is_ai_added'].sum() if 'is_ai_added' in df.columns else 0

    summary_line = f"**Total Articles Processed**: {total_articles} | **AI Articles Found**: {ai_articles}"
    logger.info(summary_line)

    # Initialize report Markdown
    report_sections = [Markdown("# 🧠 Article Enrichment Report"), Markdown(summary_line)]

    # --- Step Overview Section ---
    metrics = flow.metrics
    step_start_times = metrics.get("step_start_times", {})
    step_durations = metrics.get("step_duration", {})
    models_io = metrics.get("models_io", {})
    models_spec_names = metrics.get("models_spec_names", {})

    overview_table_data = []

    # Combine all steps from either start_times or durations
    all_steps = set(step_start_times.keys()) | set(step_durations.keys())

    total_prompt_tokens = []
    total_completion_tokens = []
    total_total_tokens = []
    avg_prompt_tokens = []
    avg_completion_tokens = []
    avg_total_tokens = []

    for step in sorted(all_steps, key=lambda s: step_start_times.get(s, 0)):
        duration = step_durations.get(step, 0)
        start_time = step_start_times.get(step)
        start_time_str = datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S') if start_time else "N/A"

        # Try to get model key (if it’s a model-related step)
        model_key = models_spec_names.get(step)
        model_io = models_io.get(model_key, {}) if model_key else {}

        inputs = model_io.get("inputs", [])
        outputs = model_io.get("outputs", [])
        errors = model_io.get("errors", [])

        # Compute metrics
        num_inputs = len([i for i in inputs if i is not None])
        num_outputs = len([o for o in outputs if o is not None])
        num_errors = len(errors)
        completion_rate = num_outputs / num_inputs if num_inputs > 0 else 0
        time_per_item = [o["metadata"]["duration"] for o in outputs if o and "metadata" in o]

        prompt_tokens = [o["metadata"]["prompt_tokens"]
                         for o in outputs if o and "metadata" in o and "prompt_tokens" in o["metadata"]]
        completion_tokens = [o["metadata"]["completion_tokens"]
                             for o in outputs if o and "metadata" in o
                             and "completion_tokens" in o["metadata"]]
        total_tokens = [o["metadata"]["total_tokens"]
                        for o in outputs if o and "metadata" in o and "total_tokens" in o["metadata"]]

        def safe_avg(lst):
            return sum(lst) / len(lst) if lst else 0
        def safe_print(lst):
            return f"{lst:.1f}" if lst!=0 else "N/A"

        if step == "load_articles":
            num_inputs = len(flow.articles)
            completion_rate = 1.0
        if step == "replicate_articles":
            num_inputs = len(flow.replicated_articles)
            completion_rate = len(flow.replicated_articles) / len(flow.articles)
        row = [
            step,
            num_inputs,
            f"{completion_rate:.1%}",
            start_time_str,
            f"{duration:.2f}s",
            f"{safe_avg(time_per_item):.2f}s",
            safe_print(safe_avg(prompt_tokens)),
            safe_print(safe_avg(completion_tokens)),
            safe_print(safe_avg(total_tokens)),
            num_errors,
        ]
        overview_table_data.append(row)

        total_prompt_tokens.append(sum(prompt_tokens))
        total_completion_tokens.append(sum(completion_tokens))
        total_total_tokens.append(sum(total_tokens))
        avg_prompt_tokens.append(safe_avg(prompt_tokens))
        avg_completion_tokens.append(safe_avg(completion_tokens))
        avg_total_tokens.append(safe_avg(total_tokens))

    current.card.append(Markdown("## 🔁 Step Overview"))
    current.card.append(Table(
        headers=[
            "Step", "Items", "Completion", "Start Time", "Duration", "Avg Time/item",
            "Avg Prompt Tokens", "Avg Completion Tokens", "Avg Total Tokens", "Errors"
        ],
        data=overview_table_data
    ))

    flow.report["step_overview"] = overview_table_data

    # Extract data
    steps = [row[0] for row in overview_table_data]
    durations = [float(row[4][:-1]) for row in overview_table_data]
    avg_time_per_item = [float(row[5][:-1]) for row in overview_table_data]

    for row in overview_table_data:
        num_items = row[1]

    # Plot 1: Duration per Step
    fig, ax = plt.subplots()
    ax.bar(steps, durations)
    ax.set_title("Total Duration per Step")
    ax.set_ylabel("Seconds")
    ax.set_xticklabels(steps, rotation=45, ha='right')
    p1 = save_plot(fig, "duration")

    # Plot 2: Avg Time per Item
    fig, ax = plt.subplots()
    ax.bar(steps, avg_time_per_item, color='orange')
    ax.set_title("Avg Time per Item")
    ax.set_ylabel("Seconds")
    ax.set_xticklabels(steps, rotation=45, ha='right')
    p2 = save_plot(fig, "avg_time")

    # Combine Plot 1 & 2
    combined_bytes_1 = combine_images_horizontally(p1, p2)
    current.card.append(Image(combined_bytes_1))


    # Plot 3: Total Tokens
    fig, ax = plt.subplots()
    width = 0.25
    x = np.arange(len(steps))
    ax.bar(x - width, total_prompt_tokens, width=width, label='Prompt')
    ax.bar(x, total_completion_tokens, width=width, label='Completion')
    ax.bar(x + width, total_total_tokens, width=width, label='Total')
    ax.set_title("Total Tokens per Step")
    ax.set_ylabel("Tokens")
    ax.set_xticks(x)
    ax.set_xticklabels(steps, rotation=45, ha='right')
    ax.legend()
    p3 = save_plot(fig, "total_tokens")

    # Plot 4: Avg Tokens
    fig, ax = plt.subplots()
    ax.bar(x - width, avg_prompt_tokens, width=width, label='Prompt')
    ax.bar(x, avg_completion_tokens, width=width, label='Completion')
    ax.bar(x + width, avg_total_tokens, width=width, label='Total')
    ax.set_title("Avg Tokens per Step")
    ax.set_ylabel("Tokens")
    ax.set_xticks(x)
    ax.set_xticklabels(steps, rotation=45, ha='right')
    ax.legend()
    p4 = save_plot(fig, "avg_tokens")

    # Combine Plot 3 & 4
    combined_bytes_2 = combine_images_horizontally(p3, p4)
    current.card.append(Image(combined_bytes_2))

    current.card.append(Markdown("## 🌐 Domains Overview"))

    if all(col in df.columns for col in ["url_domain", "is_ai_added", "clusters_names_in_order_added"]):
        domain_table_data = []

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
                f"{name}: {count / total_articles:.1%}" for name, count in top_clusters
            ) if top_clusters else "n/a"

            domain_table_data.append([
                domain,
                str(ai_count),
                f"{ai_rate:.1%}",
                top_clusters_str
            ])

        # sort table by ai count descending
        domain_table_data.sort(key=lambda x: x[1], reverse=True)

        current.card.append(Table(
            headers=["domain", "ai count", "ai rate", "top 5 clusters with rate"],
            data=domain_table_data
        ))

        # optional: also add the scatter plot again
        domains = [row[0] for row in domain_table_data]
        ai_counts = [row[1] for row in domain_table_data]
        ai_rates = [float(row[2].strip('%')) / 100 for row in domain_table_data]

        fig, ax = plt.subplots(figsize=(10, 5))
        scatter = ax.scatter(domains, ai_counts, c=ai_rates, cmap='viridis', s=100, edgecolor='k')
        ax.set_title("ai article count vs ai rate per domain")
        ax.set_xlabel("domain")
        ax.set_ylabel("ai article count")
        ax.set_xticks(np.arange(len(domains)))
        ax.set_xticklabels(domains, rotation=45, ha='right')
        cbar = fig.colorbar(scatter, ax=ax)
        cbar.set_label("ai rate")

        domain_plot_path = save_plot(fig, "ai_domain_scatter_combined")
        current.card.append(load_image(domain_plot_path))

        # save to report
        flow.report["domain_analysis_table"] = domain_table_data

    else:
        current.card.append(markdown("_missing required columns: `url_domain`, `is_ai_added`, or `clusters_names_in_order_added`._"))

    current.card.append(Markdown("## Summaries Overview"))
    if "dense_summary_length_added" in df.columns and "text_content_length" in df.columns and "core_line_summary_length_added" in df.columns:
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

        summary_plot_path = save_plot(fig, "summary_distributions")
        current.card.append(load_image(summary_plot_path))

        # Add to report if needed
        flow.report["summary_distributions"] = {
            "dense_summary_ratio": ratio.describe().to_dict(),
            "core_line_summary_length": core_lengths.describe().to_dict(),
            "title_vs_core_rouge_eval": rouge_scores.describe().to_dict()
        }
    else:
        current.card.append(Markdown("_Missing required columns to compute summary distributions._"))

    if all(col in df.columns for col in ["title", "core_line_summary_added", "title_vs_core_rouge_eval"]):
        eval_df = df[["title", "core_line_summary_added", "title_vs_core_rouge_eval"]].dropna()

        # Sort by ROUGE
        sorted_df = eval_df.sort_values("title_vs_core_rouge_eval")

        # Get Bottom 5 and Top 5
        bottom5 = sorted_df.head(5)
        top5 = sorted_df.tail(5)

        def to_table_rows(subset):
            return [
                [
                    row["title"],
                    row["core_line_summary_added"],
                    f"{row['title_vs_core_rouge_eval']:.3f}"
                ]
                for _, row in subset.iterrows()
            ]

        current.card.append(Markdown("### 🔻 Bottom 5 ROUGE Scores"))
        current.card.append(Table(
            headers=["Title", "Core Summary", "ROUGE Score"],
            data=to_table_rows(bottom5)
        ))

        current.card.append(Markdown("### 🔺 Top 5 ROUGE Scores"))
        current.card.append(Table(
            headers=["Title", "Core Summary", "ROUGE Score"],
            data=to_table_rows(top5)
        ))

        flow.report["rouge_top_bottom"] = {
            "top_5": top5.to_dict(orient="records"),
            "bottom_5": bottom5.to_dict(orient="records")
        }
    else:
        current.card.append(Markdown("_Missing columns: `title`, `core_line_summary_added`, or `title_vs_core_rouge_eval` for summary scoring._"))

    # --- Tags/Clusters Section ---
    current.card.append(Markdown("## 🏷️ Tags / Clusters Summary"))

    if "tags_pred_added" in df.columns and "clusters_names_in_order_added" in df.columns:
        tags_per_article = []
        clusters_per_article = []
        all_clusters = set()

        for i, row in df.iterrows():
            is_ai = row.get("is_ai_added", [])
            if is_ai == False:
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
        avg_tags_per_article = np.mean(tags_per_article) if tags_per_article else 0
        avg_clusters_per_article = np.mean(clusters_per_article) if clusters_per_article else 0

        md = f"""
**Total Tags (across all articles)**: {total_tags}  
**Total Clusters (distinct)**: {total_clusters}  
**Avg Tags per Article**: {avg_tags_per_article:.2f}  
**Avg Clusters per Article**: {avg_clusters_per_article:.2f}
"""
        current.card.append(Markdown(md))

        flow.report["tag_cluster_summary"] = {
            "total_tags": total_tags,
            "total_clusters": total_clusters,
            "avg_tags_per_article": avg_tags_per_article,
            "avg_clusters_per_article": avg_clusters_per_article
        }
    else:
        current.card.append(Markdown("_Missing `tags_pred_added` or `clusters_names_in_order_added` column to compute tags/clusters summary._"))

    # --- Tag Similarity Evaluation Analysis ---
    current.card.append(Markdown("### 🧪 Tag Similarity Evaluation"))

    if "tag_similarity_eval" in df.columns:
        similarity_scores = df["tag_similarity_eval"].dropna()

        # Plot distribution
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(similarity_scores, bins=20, color='mediumpurple', edgecolor='black')
        ax.set_title("Distribution of tag_similarity_eval")
        ax.set_xlabel("tag_similarity_eval")
        ax.set_ylabel("Number of Articles")

        sim_plot_path = save_plot(fig, "tag_similarity_distribution")
        current.card.append(load_image(sim_plot_path))

        # Top 5 and Bottom 5
        sorted_df = df.dropna(subset=["tag_similarity_eval"]).sort_values("tag_similarity_eval", ascending=False)

        top_5 = sorted_df.head(5)
        bottom_5 = sorted_df.tail(5)

        def format_row(row):
            return [
                row.get("title", "N/A"),
                ", ".join(row.get("tags", [])) if isinstance(row.get("tags"), list) else "N/A",
                ", ".join(row.get("tags_pred_added", [])) if isinstance(row.get("tags_pred_added"), list) else "N/A",
                f"{row.get('tag_similarity_eval', 0):.3f}"
            ]

        current.card.append(Markdown("#### 🔝 Top 5 Articles by Tag Similarity"))
        current.card.append(Table(
            headers=["Title", "Tags", "Predicted Tags", "Similarity"],
            data=[format_row(row) for _, row in top_5.iterrows()]
        ))

        current.card.append(Markdown("#### 🔻 Bottom 5 Articles by Tag Similarity"))
        current.card.append(Table(
            headers=["Title", "Tags", "Predicted Tags", "Similarity"],
            data=[format_row(row) for _, row in bottom_5.iterrows()]
        ))

        # Optionally store to report
        flow.report["tag_similarity_eval_distribution"] = similarity_scores.describe().to_dict()
        flow.report["top_tag_similarity_articles"] = top_5.to_dict(orient="records")
        flow.report["bottom_tag_similarity_articles"] = bottom_5.to_dict(orient="records")
    else:
        current.card.append(Markdown("_No `tag_similarity_eval` column found for similarity evaluation analysis._"))

    if "clusters_names_in_order_added" in df.columns:
        current.card.append(Markdown("### 🧩 Top 20 Clusters Histogram"))

        # Flatten all cluster lists into one big list
        all_clusters = []
        for cluster_list in df["clusters_names_in_order_added"].dropna():
            if isinstance(cluster_list, list):
                all_clusters.extend(cluster_list)

        cluster_counts = Counter(all_clusters)
        top_20 = cluster_counts.most_common(20)

        if top_20:
            clusters, counts = zip(*top_20)

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(clusters, counts, color='skyblue', edgecolor='black')
            ax.set_title("Top 20 Clusters in Articles")
            ax.set_ylabel("Count")
            ax.set_xticks(range(len(clusters)))
            ax.set_xticklabels(clusters, rotation=45, ha='right')

            cluster_plot_path = save_plot(fig, "top_20_clusters")
            current.card.append(load_image(cluster_plot_path))

            # Optional: Save to flow report
            flow.report["top_20_clusters"] = dict(top_20)
        else:
            current.card.append(Markdown("_No cluster data found to display._"))

    else:
        current.card.append(Markdown("_Missing `clusters_names_in_order_added` column for cluster histogram._"))
    
    flow.replicated_articles_df = df
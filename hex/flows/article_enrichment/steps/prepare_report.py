import logging
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from metaflow import step, card, current
from metaflow.cards import Markdown, Table, Image
from PIL import Image as PILImage

from hex.flows.analysis import get_domain_table_data
from hex.flows.analysis import filter_articles_by_clusters
from hex.flows.analysis import plot_summary_distributions
from hex.flows.analysis import save_plot
from hex.flows.analysis import get_rouge_top_bottom
from hex.flows.analysis import generate_tag_cluster_summary_markdown
from hex.flows.analysis import plot_tag_similarity_distribution
from hex.flows.analysis import plot_top_clusters_histogram

def load_image(path: str) -> Image:
    with open(path, "rb") as f:
        return Image(f.read())

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

def compute_step_metrics(flow):

    def safe_avg(lst):
        return sum(lst) / len(lst) if lst else 0

    def safe_print(val):
        return f"{val:.1f}" if val != 0 else "N/A"

    metrics = flow.metrics
    step_start_times = metrics.get("step_start_times", {})
    step_durations = metrics.get("step_duration", {})
    models_io = metrics.get("models_io", {})
    models_spec_names = metrics.get("models_spec_names", {})

    all_steps = set(step_start_times) | set(step_durations)
    overview_table_data = []
    total_prompt_tokens = []
    total_completion_tokens = []
    total_total_tokens = []
    avg_prompt_tokens = []
    avg_completion_tokens = []
    avg_total_tokens = []

    for step_name in sorted(all_steps, key=lambda s: step_start_times.get(s, 0)):
        duration = step_durations.get(step_name, 0)
        start_time = step_start_times.get(step_name)
        start_time_str = (
            datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
            if start_time else "N/A"
        )

        model_key = models_spec_names.get(step_name)
        model_io = models_io.get(model_key, {}) if model_key else {}
        inputs = model_io.get("inputs", [])
        outputs = model_io.get("outputs", [])
        errors = model_io.get("errors", [])

        num_inputs = len([i for i in inputs if i is not None])
        num_outputs = len([o for o in outputs if o is not None])
        num_errors = len(errors)
        completion_rate = num_outputs / num_inputs if num_inputs > 0 else 0

        time_per_item = [o["metadata"]["duration"] for o in outputs if o and "metadata" in o]
        prompt_tokens = [
            o["metadata"].get("prompt_tokens", 0)
            for o in outputs if o and "metadata" in o
        ]
        completion_tokens = [
            o["metadata"].get("completion_tokens", 0)
            for o in outputs if o and "metadata" in o
        ]
        total_tokens = [
            o["metadata"].get("total_tokens", 0)
            for o in outputs if o and "metadata" in o
        ]

        if step_name == "load_articles":
            num_inputs = len(flow.articles)
            completion_rate = 1.0
        if step_name == "replicate_articles":
            num_inputs = len(flow.replicated_articles)
            if len(flow.articles) > 0:
                completion_rate = len(flow.replicated_articles) / len(flow.articles)
            else:
                completion_rate = 0.0

        row = [
            step_name,
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

    return (
        overview_table_data,
        total_prompt_tokens,
        total_completion_tokens,
        total_total_tokens,
        avg_prompt_tokens,
        avg_completion_tokens,
        avg_total_tokens,
    )

def render_step_overview(flow):

    (overview_table_data,
     total_prompt_tokens,
     total_completion_tokens,
     total_total_tokens,
     avg_prompt_tokens,
     avg_completion_tokens,
     avg_total_tokens) = compute_step_metrics(flow)

    current.card.append(Markdown("## 🔁 Step Overview"))
    current.card.append(Table(
        headers=[
            "Step", "Items", "Completion", "Start Time", "Duration", "Avg Time/item",
            "Avg Prompt Tokens", "Avg Completion Tokens", "Avg Total Tokens", "Errors"
        ],
        data=overview_table_data
    ))

    steps = [row[0] for row in overview_table_data]
    durations = [float(row[4][:-1]) for row in overview_table_data]
    avg_time_per_item = [float(row[5][:-1]) for row in overview_table_data]

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

    current.card.append(Image(combine_images_horizontally(p1, p2)))

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

    current.card.append(Image(combine_images_horizontally(p3, p4)))

def render_domain_overview(articles) -> None:
    """Render domain overview section with table and scatter plot."""

    domain_table_data = get_domain_table_data(articles)
    current.card.append(Table(
        headers=["domain", "ai count", "ai rate", "top 5 clusters with rate"],
        data=domain_table_data.values.tolist()
    ))

def extract_errors_dataframe(metrics: dict) -> pd.DataFrame:
    rows = []

    models_io = metrics.get("models_io", {})

    for model_key, model_data in models_io.items():
        errors = model_data.get("errors", [])
        for error in errors:
            if isinstance(error, dict):
                row = {"model_key": model_key}
                row.update(error)  # Flatten error dict into row
                rows.append(row)
            else:
                # Fallback in case error is a string or other structure
                rows.append({"model_key": model_key, "error": error})

    return pd.DataFrame(rows)

def render_core_summaries(bottom5, top5):
    current.card.append(Markdown("### 🔻 Bottom 5 ROUGE Scores"))

    def to_table_rows(subset):
        return [
            [
                row["title"],
                row["core_line_summary_added"],
                f"{row['title_vs_core_rouge_eval']:.3f}"
            ]
            for _, row in subset.iterrows()
        ]

    current.card.append(Table(
        headers=["Title", "Core Summary", "ROUGE Score"],
        data=to_table_rows(bottom5)
    ))
    current.card.append(Markdown("### 🔺 Top 5 ROUGE Scores"))
    current.card.append(Table(
        headers=["Title", "Core Summary", "ROUGE Score"],
        data=to_table_rows(top5)
    ))

def render_tag_cluster_summary_section(articles):
    md, summary = generate_tag_cluster_summary_markdown(articles)
    current.card.append(Markdown(md))

def render_tag_similarity_section(articles):
    current.card.append(Markdown("### 🧪 Tag Similarity Evaluation"))
    df = pd.DataFrame(articles)
    if "tag_similarity_eval" in df.columns:
        fig, top_5, bottom_5 = plot_tag_similarity_distribution(articles)
        if fig is not None:
            sim_plot_path = save_plot(fig, "tag_similarity_distribution")
            current.card.append(load_image(sim_plot_path))
        current.card.append(Markdown("#### 🔻 Bottom 5 Articles by Tag Similarity"))
        current.card.append(Table(
            headers=["Title", "Tags", "Predicted Tags", "Similarity"],
            data=bottom_5.values.tolist()
        ))
        current.card.append(Markdown("#### 🔺 Top 5 Articles by Tag Similarity"))
        current.card.append(Table(
            headers=["Title", "Tags", "Predicted Tags", "Similarity"],
            data=top_5.values.tolist()
        ))
    else:
        current.card.append(Markdown("_No `tag_similarity_eval` column found for similarity evaluation analysis._"))

def render_top_clusters_histogram_section(articles):
    current.card.append(Markdown("### 🧩 Top 50 Clusters Histogram"))
    fig = plot_top_clusters_histogram(articles, top_n=50)
    if fig is not None:
        cluster_plot_path = save_plot(fig, "top_20_clusters")
        current.card.append(load_image(cluster_plot_path))
    else:
        current.card.append(Markdown("_No cluster data found to display._"))

def render_model_errors_section(flow) -> None:
    """Render the model errors section to the current card."""
    current.card.append(Markdown("## ❌ Model Errors"))

    error_df = extract_errors_dataframe(flow.metrics)

    if not error_df.empty:
        # Add to card (full text in cells)
        current.card.append(Markdown("### 🔎 Full Error Log (per model)"))
        current.card.append(Table(
            headers=error_df.columns.tolist(),
            data=error_df.values.tolist()
        ))
        flow.report["model_errors"] = error_df.to_dict(orient="records")
    else:
        current.card.append(Markdown("_No model errors were recorded in this flow run._"))

logger = logging.getLogger(__name__)

@card(type='default')
@step
def execute(flow) -> None:
    """Generate a detailed report from replicated articles."""

    render_step_overview(flow)

    current.card.append(Markdown("## 🌐 Domains Overview"))

    articles = filter_articles_by_clusters(
        flow.replicated_articles, ["large language models", "India", "AI"]
    )
    render_domain_overview(articles)

    current.card.append(Markdown("## Summaries Overview"))
    fig = plot_summary_distributions(articles)
    if fig is not None:
        summary_plot_path = save_plot(fig, "summary_distributions")
        current.card.append(load_image(summary_plot_path))
    else:
        current.card.append(Markdown("_Missing required columns to compute summary distributions._"))

    bottom5, top5 = get_rouge_top_bottom(articles)
    if not bottom5.empty and not top5.empty:
        render_core_summaries(bottom5, top5)
    else:
        current.card.append(Markdown(
            "_Missing columns: `title`, `core_line_summary_added`, or `title_vs_core_rouge_eval` for summary scoring._"
        ))

    current.card.append(Markdown("## 🏷️ Tags / Clusters Summary"))
    render_tag_cluster_summary_section(articles)
    render_tag_similarity_section(articles)

    render_top_clusters_histogram_section(articles)

    render_model_errors_section(flow)

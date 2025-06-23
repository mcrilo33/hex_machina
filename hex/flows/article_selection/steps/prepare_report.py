import logging
from metaflow import step, card, current
from metaflow.cards import Markdown, Table

from hex.flows.article_selection.steps.generate_newsletter import generate_newsletter_markdown
from hex.storage.hex_storage import HexStorage

logger = logging.getLogger(__name__)

# ⏱️ Set this to control how many characters of the dense summary are shown
DENSE_SUMMARY_CHAR_LIMIT = 300

def render_score_dict(title, score_dict):
    current.card.append(Markdown(f"## 🔢 {title}"))
    if not score_dict:
        current.card.append(Markdown("_No data available._"))
        return
    sorted_items = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)
    current.card.append(Table(
        headers=["Cluster", "Score"],
        data=[[k, f"{v:.4f}"] for k, v in sorted_items]
    ))

# --- Helper: Display full article lists ---
def render_articles(title, articles):
    current.card.append(Markdown(f"## 📰 {title}"))
    if not articles:
        current.card.append(Markdown("_No articles found._"))
        return

    headers = [
        "title",
        "clusters_score",
        "tags_pred_added",
        "clusters_names_in_order_added",
        "dense_summary_added",
        "core_line_summary_added"
    ]

    rows = []
    for article in articles:
        dense_summary = article.get("dense_summary_added", "N/A")
        if isinstance(dense_summary, str):
            dense_summary = dense_summary[:DENSE_SUMMARY_CHAR_LIMIT]

        row = [
            article.get("title", "N/A"),
            f"{article.get('clusters_score', 0):.4f}",
            ", ".join(article.get("tags_pred_added", [])) if isinstance(article.get("tags_pred_added", []), list) else "N/A",
            ", ".join(article.get("clusters_names_in_order_added", [])) if isinstance(article.get("clusters_names_in_order_added", []), list) else "N/A",
            dense_summary,
            article.get("core_line_summary_added", "N/A")
        ]
        rows.append(row)

    current.card.append(Table(headers=headers, data=rows))

def render_newsletter_markdown(storage, selection, path_to_save: str = None):
    """
    Render the newsletter markdown using generate_newsletter_markdown and append it to the Metaflow card.
    """
    markdown_content = generate_newsletter_markdown(storage, selection, path_to_save=path_to_save)
    current.card.append(Markdown(f"## Newsletter"))
    current.card.append(
        Markdown(markdown_content)
    )

@card
@step
def execute(flow):
    """Prepare a comprehensive report of the article selection process."""
    current.card.append(Markdown("# 📋 Prepared Report Overview"))

    storage = HexStorage(flow.config.get("db_path"))
    selection_time = flow.selection.get("selection_time")
    current.card.append(Markdown(f"**Selection Time**: `{selection_time}`"))

    render_articles("Top {flow.articles_limit} Linearly Scored Articles selected with diversity", flow.selection.get("linearly_selected_articles_with_diversity", []))

    render_newsletter_markdown(
        storage,
        storage.lazy_load(flow.selection)[0],
        path_to_save=flow.newsletter_dir
    )

import logging
from metaflow import step, card, current
from metaflow.cards import Markdown, Table

logger = logging.getLogger(__name__)

# ⏱️ Set this to control how many characters of the dense summary are shown
DENSE_SUMMARY_CHAR_LIMIT = 300

@card
@step
def execute(flow):
    """Prepare a comprehensive report of the article selection process."""
    current.card.append(Markdown("# 📋 Prepared Report Overview"))

    # Print timestamp
    selection_time = flow.selection.get("selection_time")
    current.card.append(Markdown(f"**Selection Time**: `{selection_time}`"))

    # --- Helper: Display cluster scores ---
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

    render_articles("Top N Linearly Scored Articles selected with diversity", flow.selection.get("linearly_selected_articles_with_diversity", []))

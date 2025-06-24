import json
from pathlib import Path
import base64
from hex.models.loader import load_model_spec
from datetime import datetime
from wordcloud import WordCloud
from typing import Any, List, Dict, Union


def get_or_create_selection_dir(
    storage: Any,
    selection: dict,
    path_to_save: str = None
) -> Path:
    """
    Ensure the directory at storage.db_path.parent/selection["doc_id"] exists,
    creating it if necessary, and return the Path.
    Also ensures an 'images' directory exists inside it.

    Args:
        storage: An object with a db_path attribute (str or Path).
        selection: A dict containing a "doc_id" key.

    Returns:
        Path: The path to the created/existing directory.
    """
    db_path = Path(storage.db_path)
    doc_id = selection["doc_id"]
    if path_to_save:
        selection_dir = Path(path_to_save)
    else:
        selection_dir = db_path.parent / "selections" / str(doc_id)
    selection_dir.mkdir(parents=True, exist_ok=True)
    images_dir = selection_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return selection_dir


def format_cluster_scores(
    cluster_scores: Dict[str, Union[int, float]], n: int = None
) -> str:
    """
    Format cluster scores as a comma-separated string, e.g.:
    "agents (12.0), AI safety (10.0), ..."
    Sorted by score descending, with one decimal place.
    If n is provided, only the top n clusters are included.
    """
    sorted_items = sorted(cluster_scores.items(), key=lambda x: x[1], reverse=True)
    if n is not None:
        sorted_items = sorted_items[:n]
    parts = [f"{name} ({score:.1f})" for name, score in sorted_items]
    return ", ".join(parts)


def format_articles_for_report(articles: List[Dict]) -> str:
    """
    Format a list of articles into a numbered string with title and dense summary.
    Each article dict should have 'title' and 'dense_summary_added' keys.
    """
    lines = []
    for idx, article in enumerate(articles, 1):
        title = article.get("title", "N/A")

        dense_summary = article.get("dense_summary_added", "N/A").replace("\n", " ")
        lines.append(
            f'{idx}.  TITLE: "{title}"\n'
            f'    DENSE SUMMARY: "{dense_summary}"'
        )
    return "\n".join(lines)


def generate_newsletter_title_and_edito(
    cluster_scores: Dict[str, Union[int, float]],
    articles: List[Dict],
    n_clusters: int = 20,
    n_articles: int = 8
) -> tuple[str, str]:
    """
    Generate main_title and edito using the model spec, given cluster_scores
    and articles.
    """
    top_clusters = format_cluster_scores(cluster_scores, n=n_clusters)
    top_articles = format_articles_for_report(articles[:n_articles])
    model_spec_name = "newsletter_title_and_edito_spec"
    model_spec = load_model_spec(model_spec_name)
    input_data = {
        "top_clusters": top_clusters,
        "top_articles": top_articles,
    }
    validated_input = model_spec.extract_and_validate_input(input_data)
    pred = model_spec._loaded_model.predict(validated_input)
    preds = pred["output"].split("\n\n\n")
    main_title = preds[0].strip()
    subtitle = preds[1].strip()
    edito = preds[2].strip()
    return main_title, subtitle, edito


def generate_linkedin_twitter_post(
    header: str,
    subtitle: str,
    edito: str,
    result: str,
    selection_dir: Path
):
    """
    Generate a LinkedIn post from the newsletter report.
    """
    model_spec_name_linkedin = "newsletter_linkedin_post_spec"
    model_spec_linkedin = load_model_spec(model_spec_name_linkedin)
    model_spec_name_twitter = "newsletter_twitter_post_spec"
    model_spec_twitter = load_model_spec(model_spec_name_twitter)
    input_data = {
        "header": header,
        "subtitle": subtitle,
        "edito": edito,
        "result": result
    }
    validated_input_linkedin = model_spec_linkedin.extract_and_validate_input(input_data)
    pred_linkedin = model_spec_linkedin._loaded_model.predict(validated_input_linkedin)
    preds_linkedin = pred_linkedin["output"]
    validated_input_twitter = model_spec_twitter.extract_and_validate_input(input_data)
    pred_twitter = model_spec_twitter._loaded_model.predict(validated_input_twitter)
    preds_twitter = pred_twitter["output"]
    return preds_linkedin, preds_twitter


def generate_and_save_edito_image(
    title: str,
    selection_dir: Path,
    image_filename: str = "edito_image.png"
) -> Path:
    """
    Generate an image for the newsletter edito using the model spec and save it.

    Args:
        title (str): The newsletter title to use as input.
        selection_dir (Path): The base directory for the selection.
        image_filename (str): The filename for the saved image.

    Returns:
        Path: The path to the saved image.
    """
    # Ensure images directory exists
    images_dir = selection_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Load model spec and generate image
    model_spec_name = "edito_image_spec"
    model_spec = load_model_spec(model_spec_name)
    input_data = {"title": title}
    validated_input = model_spec.extract_and_validate_input(input_data)
    pred = model_spec._loaded_model.predict(validated_input)
    b64_image = pred["output"][0]

    # Decode and save image
    image_path = images_dir / image_filename
    with open(image_path, "wb") as f:
        f.write(base64.b64decode(b64_image))

    return image_path


def generate_hexmachina_wordcloud(word_freq, save_path):
    for word, freq in word_freq.items():
        if freq == 0:
            word_freq[word] = 0.1
    # Custom light color palette
    colors = [
        "#FFFFFF",   # Pure white
        "#F8FBFF",   # Almost-white, with the faintest blue tint
        "#EEF6FF",   # Ultra-pale cloud blue
        "#DDEEFF",   # Soft powdery blue
        "#C9E4FF",   # Light breeze blue
        "#B5DAFF"    # Faint tech blue
    ]

    # Map font size to color
    def hex_color_func(
        word, font_size, position, orientation, random_state=None, **kwargs
    ):
        if font_size > 80:
            return colors[0]
        elif font_size > 60:
            return colors[1]
        elif font_size > 40:
            return colors[2]
        elif font_size > 25:
            return colors[3]
        elif font_size > 15:
            return colors[4]
        else:
            return colors[5]

    # Path to Roboto Mono font
    current_file_path = Path(__file__).resolve().parent.parent.parent.parent
    font_path = (
        current_file_path / "utils/Roboto_Mono/static/RobotoMono-Regular.ttf"
    )

    # Create the word cloud
    wc = WordCloud(
        width=800,
        height=280,
        background_color="#4A77EA",  # Blue background
        mode='RGBA',
        font_path=font_path,
        color_func=hex_color_func,
        max_font_size=120,
        min_font_size=14,
        random_state=42
    ).generate_from_frequencies(word_freq)

    # Save to file
    wc.to_file(save_path)


def format_article_brief(article: Dict) -> dict:
    """
    Format an article dict into a dictionary with:
    title, core-line-summary, link, source, date, reading time, clusters.
    """
    title = article.get("title", "N/A")
    core_line = article.get("core_line_summary_added", "N/A")
    url = article.get("url", "N/A")
    source = article.get("url_domain", "N/A")
    date_str = article.get("published_date", "N/A")
    # Parse and format date
    try:
        date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        date_fmt = date_obj.strftime("%-d %b %Y")  # e.g., 4 Jun 2025
    except Exception:
        date_fmt = date_str
    # Estimate reading time: assume 200 words/minute
    text_length = article.get("text_content_length", 0)
    # Roughly 5 chars/word, 200 wpm
    if text_length:
        reading_time_min = max(5, int(text_length / 5 / 160))
    else:
        reading_time_min = "N/A"
    clusters = article.get("clusters_names_in_order_added", [])
    hashtags = [
        f"#{c.lower().replace(' ', '_')}" for c in clusters
    ] if clusters else []

    return {
        "title": title,
        "core_summary": core_line,
        "link": url,
        "source": source.replace(".com", "").upper(),
        "date": date_fmt,
        "reading_time_min": reading_time_min,
        "clusters": hashtags,
    }


def format_articles_for_newsletter(
    articles: List[Dict], max_articles: int = None
) -> str:
    """
    Format a list of articles for a newsletter report, with each article's
    title, core line summary, link, source, date, reading time, and clusters.
    If max_articles is provided, only the first `max_articles` are included.
    """
    lines = []
    articles_to_process = (
        articles[:max_articles] if max_articles is not None else articles
    )

    for idx, article in enumerate(articles_to_process, 1):
        formatted_brief = format_article_brief(article)
        title = formatted_brief["title"]
        core_summary = formatted_brief["core_summary"]
        link = formatted_brief["link"]
        source = formatted_brief["source"]
        date = formatted_brief["date"]
        reading_time_min = formatted_brief["reading_time_min"]
        hashtags = " ".join(formatted_brief["clusters"])

        lines.append(
            f'{idx}. {title} | '
            f'{core_summary} | {link} | '
            f'**{source} · {date} · ⏱ {reading_time_min} min · {hashtags}**'
        )
    return "\n".join(lines)


def generate_newsletter_header(selection: Dict, title: str) -> str:
    """
    Generates the newsletter header string.

    Args:
        selection (Dict): The selection dictionary containing doc_id.

    Returns:
        str: The formatted newsletter header.
    """
    doc_id = int(selection.get("doc_id", "N/A")) - 19
    return f"Hex Machina · Issue {doc_id} · {title}"


def generate_newsletter_markdown(storage, selection, path_to_save: str = None):
    if "clusters_scores_artifact" in selection:
        clusters_scores = json.loads(selection["clusters_scores"])
    else:
        clusters_scores = selection["clusters_scores"]
    if "linearly_selected_articles_with_diversity_artifact" in selection:
        articles = json.loads(
            selection["linearly_selected_articles_with_diversity"]
        )
    else:
        articles = selection["linearly_selected_articles_with_diversity"]
    ingestion_summary = selection.get("ingestion_summary", "")
    selection_dir = get_or_create_selection_dir(
        storage, selection, path_to_save=path_to_save
    )
    print(f"selection_dir: {selection_dir}")
    main_title, subtitle, edito = generate_newsletter_title_and_edito(
        clusters_scores, articles
    )
    header = generate_newsletter_header(selection, main_title)
    generate_hexmachina_wordcloud(
        clusters_scores, selection_dir / "images/hexmachina_wordcloud.png"
    )
    generate_and_save_edito_image(
        title=main_title + " : " + subtitle,
        selection_dir=selection_dir,
        image_filename="edito_image.png"
    )
    result = format_articles_for_newsletter(articles)

    linkedin_post, twitter_post = generate_linkedin_twitter_post(
        header=main_title,
        subtitle=subtitle,
        edito=edito,
        result=result,
        selection_dir=selection_dir
    )

    output_content = (
        f"# {header}\n\n"
        f"## {subtitle}\n\n"
        f"### Edito\n"
        f"{edito}\n\n"
        f"### Articles\n"
        f"{result}\n\n"
        f"### Ingestion Summary\n"
        f"{ingestion_summary}\n"
        f"# LinkedIn Post\n"
        f"{linkedin_post}\n"
        f"# Twitter Post\n"
        f"{twitter_post}\n"
    )

    output_file_path = selection_dir / "newsletter_report.txt"
    with open(output_file_path, "w") as f:
        f.write(output_content)
    return output_content

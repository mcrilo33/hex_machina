import logging
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter
from typing import Dict, List, Any, Optional
from metaflow.cards import Markdown, Table, Image, VegaChart
from metaflow import current, step, card

logger = logging.getLogger(__name__)

@card
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

    # Completion rate
    step_columns = [
        "is_ai_pred_added", "dense_summary_added", "core_line_summary_added",
        "tags_pred_added", "clusters_names_in_order_added"
    ]
    # Only use columns that actually exist in the DataFrame
    available_steps = [col for col in step_columns if col in df.columns]
    
    if available_steps:
        completion = {step: [
            df[step].notnull().mean(),
            df[step].notnull().sum()
        ] for step in available_steps}
        flow.report["completion_rate"] = completion
    
    # Execution time
    if "execution_time" in df.columns:
        flow.report["avg_execution_time"] = df["execution_time"].mean()
        flow.report["min_execution_time"] = df["execution_time"].min()
        flow.report["max_execution_time"] = df["execution_time"].max()

    # Html/Text content length anomaly
    if "html_content_length" in df.columns and "text_content_length" in df.columns:
        diff = abs(df["html_content_length"] - df["text_content_length"])
        df["content_length_anomaly"] = diff > diff.mean() + 2 * diff.std()
        flow.report["content_anomalies_count"] = df["content_length_anomaly"].sum()
        flow.report["content_anomalies_pct"] = df["content_length_anomaly"].mean()

    # Summary/text ratio outliers
    if "summary_text_ratio" in df.columns:
        ratio_mean = df["summary_text_ratio"].mean()
        ratio_std = df["summary_text_ratio"].std()
        df["summary_ratio_outlier"] = (df["summary_text_ratio"] > (ratio_mean + 2 * ratio_std)) | \
                                     (df["summary_text_ratio"] < (ratio_mean - 2 * ratio_std))
        flow.report["summary_ratio_outliers_count"] = df["summary_ratio_outlier"].sum()
        flow.report["summary_ratio_outliers_pct"] = df["summary_ratio_outlier"].mean()

    # Step-level timing and errors
    if hasattr(flow, "metrics") and isinstance(flow.metrics, dict):
        step_metrics = []
        for step_name in flow.metrics.get("processing_times", {}):
            step_data = {
                "step_name": step_name,
                "total_processing_time": flow.metrics["processing_times"].get(step_name, 0.0),
                "avg_prediction_time": flow.metrics["avg_prediction_times"].get(step_name, 0.0),
                "errors": len(flow.errors.get(step_name, [])) if hasattr(flow, "errors") else 0
            }
            step_metrics.append(step_data)
        flow.report["step_metrics"] = step_metrics

    # Capture token usage per step
    if hasattr(flow, "metrics") and isinstance(flow.metrics, dict):
        token_usage_details = []
        for step_name, usage in flow.metrics.get("avg_tokens_usage", {}).items():
            token_usage_details.append({
                "step_name": step_name,
                "avg_prompt_tokens": usage.get("avg_prompt_tokens", 0.0),
                "avg_completion_tokens": usage.get("avg_completion_tokens", 0.0),
                "avg_total_tokens": usage.get("avg_total_tokens", 0.0),
            })
        flow.report["token_usage_per_step"] = token_usage_details
    
    # Capture errors details per step
    if hasattr(flow, "errors") and isinstance(flow.errors, dict):
        error_details = {}
        for step_name, errors_list in flow.errors.items():
            if errors_list:
                error_details[step_name] = errors_list
        flow.report["errors_per_step"] = error_details

    # Top worst and best scoring metrics
    _gather_top_bottom(df, flow)

    # Cluster stats
    _gather_cluster_stats(df, flow)

    # Domain-level stats
    _gather_domain_stats(df, flow)

    logger.info(f"✅ Report metrics calculated for {len(df)} articles.")

    # Save the processed DataFrame for further analysis if needed
    flow.processed_df = df
    
    # Generate visualization card
    _generate_report_card(flow)


def _gather_top_bottom(df: pd.DataFrame, flow) -> None:
    """Gather top and bottom performing articles based on metrics."""
    if "dense_vs_core_rouge_eval" in df.columns and df["dense_vs_core_rouge_eval"].notna().any():
        flow.report["rouge_best"] = df.nlargest(5, "dense_vs_core_rouge_eval")[["title", "dense_vs_core_rouge_eval"]].to_dict(orient="records")
        flow.report["rouge_worst"] = df.nsmallest(5, "dense_vs_core_rouge_eval")[["title", "dense_vs_core_rouge_eval"]].to_dict(orient="records")

    if "bert_score_summary_vs_dense_eval" in df.columns and df["bert_score_summary_vs_dense_eval"].notna().any():
        flow.report["bert_best"] = df.nlargest(5, "bert_score_summary_vs_dense_eval")[["title", "bert_score_summary_vs_dense_eval"]].to_dict(orient="records")
        flow.report["bert_worst"] = df.nsmallest(5, "bert_score_summary_vs_dense_eval")[["title", "bert_score_summary_vs_dense_eval"]].to_dict(orient="records")
        print("YOOOOOOOOO")
        print(flow.report["bert_best"])
        print("YOOOOOOOOO")
        print(flow.report["bert_worst"])
        print("YOOOOOOOOO")

    if "tag_similarity_eval" in df.columns and df["tag_similarity_eval"].notna().any():
        flow.report["tag_similarity_best"] = df.nlargest(5, "tag_similarity_eval")[["title", "tag_similarity_eval"]].to_dict(orient="records")
        flow.report["tag_similarity_worst"] = df.nsmallest(5, "tag_similarity_eval")[["title", "tag_similarity_eval"]].to_dict(orient="records")


def _gather_cluster_stats(df: pd.DataFrame, flow) -> None:
    """Analyze and gather cluster statistics."""
    if "tags_pred_added" in df.columns:
        # Handle potential NaN values and ensure lists are properly processed
        valid_tags = df["tags_pred_added"].dropna()
        if not valid_tags.empty:
            # Convert any non-list values to lists if necessary
            all_tags = []
            for tags in valid_tags:
                if isinstance(tags, list):
                    all_tags.extend(tags)
                elif isinstance(tags, str):
                    # Handle case where tags might be stored as a string
                    try:
                        import json
                        parsed_tags = json.loads(tags.replace("'", "\""))
                        if isinstance(parsed_tags, list):
                            all_tags.extend(parsed_tags)
                    except:
                        # If parsing fails, treat as a single tag
                        all_tags.append(tags)
            
            tag_counter = Counter(all_tags)
            flow.report["top_predicted_clusters"] = tag_counter.most_common(10)
            flow.report["total_unique_clusters"] = len(tag_counter)


def _gather_domain_stats(df: pd.DataFrame, flow) -> None:
    """Analyze and gather domain-level statistics."""
    if "url_domain" in df.columns:
        # Create a dict with column name as key and aggregation function as value
        agg_dict = {}
        
        if "is_ai_pred_added" in df.columns:
            # Convert string 'true' to boolean True if needed
            if df["is_ai_pred_added"].dtype == 'object':
                df["is_ai_pred_added_bool"] = df["is_ai_pred_added"].astype(str).str.lower() == "true"
                agg_dict["is_ai_pred_added_bool"] = "sum"
            else:
                agg_dict["is_ai_pred_added"] = "sum"
        
        if "dense_vs_core_rouge_eval" in df.columns:
            agg_dict["dense_vs_core_rouge_eval"] = "mean"
        
        if "bert_score_summary_vs_dense_eval" in df.columns:
            agg_dict["bert_score_summary_vs_dense_eval"] = "mean"
        
        # Add count of articles per domain (correct format for article_count)
        # We don't use the tuple format with agg_dict, but directly include it
        
        # Only proceed if we have aggregations to perform
        if agg_dict:
            try:
                # First, get basic domain stats with article count
                domain_stats = df.groupby("url_domain").size().reset_index(name="article_count")
                
                # Then, if we have other metrics, add them
                if agg_dict:
                    metrics_df = df.groupby("url_domain").agg(agg_dict).reset_index()
                    # Merge with the basic stats
                    domain_stats = domain_stats.merge(metrics_df, on="url_domain", how="left")
                
                # Only include these reports if the relevant columns exist
                if "is_ai_pred_added_bool" in domain_stats.columns or "is_ai_pred_added" in domain_stats.columns:
                    ai_col = "is_ai_pred_added_bool" if "is_ai_pred_added_bool" in domain_stats.columns else "is_ai_pred_added"
                    flow.report["domain_top_ai"] = domain_stats.nlargest(5, ai_col).to_dict(orient="records")
                
                if "dense_vs_core_rouge_eval" in domain_stats.columns:
                    flow.report["domain_top_rouge"] = domain_stats.nlargest(5, "dense_vs_core_rouge_eval").to_dict(orient="records")
                
                if "bert_score_summary_vs_dense_eval" in domain_stats.columns:
                    flow.report["domain_top_bert"] = domain_stats.nlargest(5, "bert_score_summary_vs_dense_eval").to_dict(orient="records")
                
                # Always include domain article counts
                flow.report["domain_article_counts"] = domain_stats.nlargest(10, "article_count").to_dict(orient="records")
                
            except Exception as e:
                logger.error(f"Error calculating domain statistics: {str(e)}")
                # Still provide basic domain counts if possible
                try:
                    domain_counts = df["url_domain"].value_counts().reset_index()
                    domain_counts.columns = ["url_domain", "article_count"]
                    flow.report["domain_article_counts"] = domain_counts.head(10).to_dict(orient="records")
                except Exception:
                    logger.error("Unable to calculate even basic domain statistics")


def _generate_report_card(flow) -> None:
    """Generate a visual report card with metrics and charts."""
    current.card.append(Markdown("# 📊 Article Enrichment Report"))
    
    # Display basic statistics
    current.card.append(Markdown(f"**Total Articles Processed**: {len(flow.processed_df)}" if hasattr(flow, 'processed_df') else "**No articles processed**"))
    
    # Completion rates
    if "completion_rate" in flow.report:
        current.card.append(Markdown("## 📈 Step Completion Rates"))
        
        # Create a more visual table with formatted percentages
        completion_table = [["Step", "Completion Rate", "Number of processed items"]]
        for step, rate in flow.report["completion_rate"].items():
            formatted_rate = f"{rate[0]:.2%}"
            count = f"{rate[1]:,}"
            completion_table.append([step, formatted_rate, count])
        
        current.card.append(Table(completion_table))
        
        # Create a visualization of completion rates using VegaChart
        try:
            completion_data = [{"step": str(k), "rate": float(v[0])} for k, v in flow.report["completion_rate"].items()]
            vega_spec = {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "description": "Step Completion Rates",
                "data": {"values": completion_data},
                "mark": "bar",
                "encoding": {
                    "x": {"field": "step", "type": "nominal", "title": "Processing Step"},
                    "y": {"field": "rate", "type": "quantitative", "title": "Completion Rate", "axis": {"format": ".0%"}},
                    "color": {"field": "step", "type": "nominal", "legend": None}
                },
                "width": 400,
                "height": 300
            }
            current.card.append(VegaChart(vega_spec))
        except Exception as e:
            logger.warning(f"Could not create VegaChart for completion rates: {e}")

    # Display top clusters
    if "top_predicted_clusters" in flow.report:
        current.card.append(Markdown("## 🔍 Top Predicted Clusters"))
        cluster_table = [["Cluster", "Count"]]
        for tag, count in flow.report["top_predicted_clusters"]:
            cluster_table.append([tag, count])
        current.card.append(Table(cluster_table))
        
        # Try to create a visualization of top clusters
        try:
            cluster_data = [{"cluster": tag, "count": count} for tag, count in flow.report["top_predicted_clusters"]]
            vega_spec = {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "description": "Top Predicted Clusters",
                "data": {"values": cluster_data},
                "mark": "bar",
                "encoding": {
                    "y": {"field": "cluster", "type": "nominal", "title": "Cluster", "sort": "-x"},
                    "x": {"field": "count", "type": "quantitative", "title": "Count"},
                    "color": {"field": "cluster", "type": "nominal", "legend": None}
                },
                "width": 400,
                "height": 300
            }
            current.card.append(VegaChart(vega_spec))
        except Exception as e:
            logger.warning(f"Could not create VegaChart for clusters: {e}")

    # Display domain statistics
    if "domain_article_counts" in flow.report:
        current.card.append(Markdown("## 🏢 Top Domains by Article Count"))
        domain_table = [["Domain", "Article Count"]]
        for record in flow.report["domain_article_counts"]:
            domain_table.append([record["url_domain"], record["article_count"]])
        current.card.append(Table(domain_table))

    # Show top and bottom performers if available
    if all(key in flow.report for key in ["rouge_best", "rouge_worst"]):
        current.card.append(Markdown("## 📊 ROUGE Score (Dense vs Core Summaries) Analysis"))
        current.card.append(Markdown("### Top 5 Articles by ROUGE Score"))
        rouge_best_table = [["Title", "ROUGE Score"]]
        for article in flow.report["rouge_best"]:
            rouge_best_table.append([article["title"], f"{article['dense_vs_core_rouge_eval']:.4f}"])
        current.card.append(Table(rouge_best_table))
        
        current.card.append(Markdown("### Bottom 5 Articles by ROUGE Score"))
        rouge_worst_table = [["Title", "ROUGE Score"]]
        for article in flow.report["rouge_worst"]:
            rouge_worst_table.append([article["title"], f"{article['dense_vs_core_rouge_eval']:.4f}"])
        current.card.append(Table(rouge_worst_table))

    # Show top and bottom performers for BERTScore if available
    if all(key in flow.report for key in ["bert_best", "bert_worst"]):
        current.card.append(Markdown("## 📊 BERTScore (Summary vs Dense Summary) Analysis"))

        current.card.append(Markdown("### Top 5 Articles by BERTScore"))
        bert_best_table = [["Title", "BERTScore (F1)"]]
        for article in flow.report["bert_best"]:
            bert_best_table.append([article["title"], f"{article['bert_score_summary_vs_dense_eval']:.4f}"])
        current.card.append(Table(bert_best_table))

        current.card.append(Markdown("### Bottom 5 Articles by BERTScore"))
        bert_worst_table = [["Title", "BERTScore (F1)"]]
        for article in flow.report["bert_worst"]:
            bert_worst_table.append([article["title"], f"{article['bert_score_summary_vs_dense_eval']:.4f}"])
        current.card.append(Table(bert_worst_table))

    # Show top and bottom performers for Tag Similarity if available
    if all(key in flow.report for key in ["tag_similarity_best", "tag_similarity_worst"]):
        current.card.append(Markdown("## 🏷️ Tag Similarity Analysis"))

        current.card.append(Markdown("### Top 5 Articles by Tag Similarity"))
        tag_similarity_best_table = [["Title", "Tag Similarity"]]
        for article in flow.report["tag_similarity_best"]:
            tag_similarity_best_table.append([article["title"], f"{article['tag_similarity_eval']:.4f}"])
        current.card.append(Table(tag_similarity_best_table))

        current.card.append(Markdown("### Bottom 5 Articles by Tag Similarity"))
        tag_similarity_worst_table = [["Title", "Tag Similarity"]]
        for article in flow.report["tag_similarity_worst"]:
            tag_similarity_worst_table.append([article["title"], f"{article['tag_similarity_eval']:.4f}"])
        current.card.append(Table(tag_similarity_worst_table))


    # Add a note about data anomalies if detected
    if "content_anomalies_pct" in flow.report:
        current.card.append(Markdown("## ⚠️ Data Anomalies"))
        anomaly_table = [["Anomaly Type", "Count", "Percentage"]]
        
        if "content_anomalies_pct" in flow.report:
            anomaly_table.append([
                "Content Length Discrepancies", 
                f"{flow.report['content_anomalies_count']}", 
                f"{flow.report['content_anomalies_pct']:.2%}"
            ])
            
        if "summary_ratio_outliers_pct" in flow.report:
            anomaly_table.append([
                "Summary/Text Ratio Outliers", 
                f"{flow.report['summary_ratio_outliers_count']}", 
                f"{flow.report['summary_ratio_outliers_pct']:.2%}"
            ])
            
        current.card.append(Table(anomaly_table))
    
    
    # Step metrics overview
    if "step_metrics" in flow.report:
        current.card.append(Markdown("## 🛠️ Step Metrics Overview"))
        step_table = [["Step", "Total Time (s)", "Avg Prediction Time (s)", "Errors"]]
        for step_data in flow.report["step_metrics"]:
            step_table.append([
                step_data["step_name"],
                f"{step_data['total_processing_time']:.2f}",
                f"{step_data['avg_prediction_time']:.4f}",
                f"{step_data['errors']}"
            ])
        current.card.append(Table(step_table))

    # Execution time metrics
    if all(key in flow.report for key in ["avg_execution_time", "min_execution_time", "max_execution_time"]):
        current.card.append(Markdown("## ⏱️ Execution Time Statistics"))
        exec_time_table = [
            ["Metric", "Value (seconds)"],
            ["Average", f"{flow.report['avg_execution_time']:.2f}"],
            ["Minimum", f"{flow.report['min_execution_time']:.2f}"],
            ["Maximum", f"{flow.report['max_execution_time']:.2f}"]
        ]
        current.card.append(Table(exec_time_table))

    # Token usage overview
    if "token_usage_per_step" in flow.report:
        current.card.append(Markdown("## 🔢 Token Usage Overview"))
        token_table = [["Step", "Avg Prompt Tokens", "Avg Completion Tokens", "Avg Total Tokens"]]
        for token_data in flow.report["token_usage_per_step"]:
            token_table.append([
                token_data["step_name"],
                f"{token_data['avg_prompt_tokens']:.2f}",
                f"{token_data['avg_completion_tokens']:.2f}",
                f"{token_data['avg_total_tokens']:.2f}",
            ])
        current.card.append(Table(token_table))

    # Show errors per step if any
    if "errors_per_step" in flow.report and flow.report["errors_per_step"]:
        current.card.append(Markdown("## ⚠️ Errors by Step"))
        
        for step_name, errors_list in flow.report["errors_per_step"].items():
            if not errors_list:
                continue
            
            current.card.append(Markdown(f"### Step: `{step_name}`"))
            
            error_table = [["Index", "Article ID", "Error Message"]]
            for err in errors_list:
                error_table.append([
                    err.get("index", "N/A"),
                    err.get("article_id", "N/A"),
                    err.get("error_message", "N/A")
                ])
            
            current.card.append(Table(error_table))
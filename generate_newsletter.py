#!/usr/bin/env python3
"""
Main script to generate newsletter by executing the three flows in sequence:
1. Article Ingestion Flow
2. Article Enrichment Flow  
3. Article Selection Flow

This script orchestrates the complete pipeline from RSS ingestion to final 
article selection.
"""

import argparse
import logging
import subprocess
import os
import sys
from datetime import datetime, timedelta
from typing import Optional


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('newsletter_generation.log')
        ]
    )


def create_generation_directory() -> str:
    """
    Create a directory based on current date in ./generated_newsletters.
    
    Returns:
        str: Path to the created directory
    """
    # Create base directory if it doesn't exist
    base_dir = './generated_newsletters'
    os.makedirs(base_dir, exist_ok=True)
    
    # Create date-based subdirectory
    current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    generation_dir = os.path.join(base_dir, current_date)
    os.makedirs(generation_dir, exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Created newsletter directory: {generation_dir}")
    
    return generation_dir


def export_flow_card(
    flow_name: str, 
    generation_dir: str, 
    step_name: str = 'prepare_report'
) -> bool:
    """
    Export a flow's card data to HTML file.
    
    Args:
        flow_name: Name of the flow
        generation_dir: Directory to save the HTML file
        step_name: Name of the step to export (default: 'prepare_report')
        
    Returns:
        bool: True if export was successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Convert flow name to module path
        flow_module = flow_name.lower().replace('flow', '')
        if flow_module.startswith('article'):
            flow_module = flow_module.replace('article', 'article_')
        
        # Build the export command
        output_file = os.path.join(
            generation_dir, f"{flow_name.lower()}_report.html"
        )
        cmd = [
            'python', '-m', f'hex.flows.{flow_module}.flow', 
            'card', 'get', step_name, output_file
        ]
        
        logger.info(f"Exporting {flow_name} card to: {output_file}")
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Run the export command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully exported {flow_name} card to: {output_file}")
            return True
        else:
            logger.warning(
                f"Failed to export {flow_name} card (return code: {result.returncode})"
            )
            if result.stderr:
                logger.warning(f"Export error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to export {flow_name} card: {str(e)}")
        return False


def run_flow(flow_name: str, generation_dir: str, **kwargs) -> bool:
    """
    Run a Metaflow flow with the given parameters using subprocess.
    
    Args:
        flow_name: Name of the flow to run
        generation_dir: Directory to save flow logs
        **kwargs: Parameters to pass to the flow
        
    Returns:
        bool: True if flow completed successfully, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting {flow_name} flow with parameters: {kwargs}")
        
        # Convert flow name to module path 
        # (e.g., ArticleIngestionFlow -> article_ingestion)
        flow_module = flow_name.lower().replace('flow', '')
        if flow_module.startswith('article'):
            flow_module = flow_module.replace('article', 'article_')
        
        # Build the command to run the flow
        cmd = ['python', '-m', f'hex.flows.{flow_module}.flow', 'run', '--with', 'card']
        
        # Add parameters to the command
        for key, value in kwargs.items():
            if value is not None:
                if key != 'clean_tables' and isinstance(value, bool):
                    if value:
                        cmd.append(f'--{key}')
                else:
                    cmd.append(f'--{key}')
                    cmd.append(str(value))
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Create log file path
        flow_log_file = os.path.join(generation_dir, f"{flow_name.lower()}_flow.log")
        
        # Run the flow using subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Save flow logs to file
        with open(flow_log_file, 'w') as f:
            f.write(f"Flow: {flow_name}\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"Return code: {result.returncode}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("-" * 80 + "\n")
            if result.stdout:
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\n")
            if result.stderr:
                f.write("STDERR:\n")
                f.write(result.stderr)
                f.write("\n")
        
        logger.info(f"Flow logs saved to: {flow_log_file}")
        
        if result.returncode == 0:
            logger.info(f"Successfully completed {flow_name} flow")
            if result.stdout:
                logger.info(f"Flow output: {result.stdout}")
            
            # Export flow card after successful execution
            export_flow_card(flow_name, generation_dir)
            
            return True
        else:
            logger.error(
                f"Flow {flow_name} failed with return code {result.returncode}"
            )
            if result.stderr:
                logger.error(f"Flow error: {result.stderr}")
            if result.stdout:
                logger.info(f"Flow output: {result.stdout}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to run {flow_name} flow: {str(e)}")
        return False


def generate_newsletter(
    date_threshold: str,
    ingestion_articles_table: str,
    replicates_table: str,
    selected_articles_table: str,
    articles_limit: Optional[int] = None,
    selection_articles_limit: Optional[int] = None,
    clean_tables: bool = False,
    verbose: bool = False
) -> bool:
    """
    Generate newsletter by running the three flows in sequence.
    
    Args:
        date_threshold: Date threshold for article processing (RFC 2822 format)
        ingestion_articles_table: Table name for ingested articles
        replicates_table: Table name for replicated articles
        selected_articles_table: Table name for selected articles
        articles_limit: Maximum number of articles to process (None for no limit)
        selection_articles_limit: Maximum number of selected articles to process 
                                 (None for no limit)
        clean_tables: Whether to clean tables before processing
        verbose: Enable verbose logging
        
    Returns:
        bool: True if all flows completed successfully, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Create newsletter directory
    generation_dir = create_generation_directory()
    
    # Common parameters for all flows
    common_params = {
        'date_threshold': date_threshold,
        'clean_tables': clean_tables
    }
    
    if articles_limit is not None:
        common_params['articles_limit'] = articles_limit
    
    logger.info("Starting newsletter generation pipeline")
    logger.info(f"Newsletter directory: {generation_dir}")
    logger.info(f"Date threshold: {date_threshold}")
    logger.info(f"Ingestion articles table: {ingestion_articles_table}")
    logger.info(f"Replicates table: {replicates_table}")
    logger.info(f"Selected articles table: {selected_articles_table}")
    logger.info(f"Articles limit: {articles_limit}")
    logger.info(f"Selection articles limit: {selection_articles_limit}")
    logger.info(f"Clean tables: {clean_tables}")
    
    # Step 1: Article Ingestion Flow
    logger.info("=" * 50)
    logger.info("STEP 1: Article Ingestion Flow")
    logger.info("=" * 50)
    
    ingestion_params = {
        **common_params,
        'articles_table': ingestion_articles_table
    }
    
    if not run_flow('ArticleIngestionFlow', generation_dir, **ingestion_params):
        logger.error("Article ingestion flow failed. Stopping pipeline.")
        return False
    
    # Step 2: Article Enrichment Flow
    logger.info("=" * 50)
    logger.info("STEP 2: Article Enrichment Flow")
    logger.info("=" * 50)
    
    enrichment_params = {
        **common_params,
        'articles_table': ingestion_articles_table,
        'replicates_table': replicates_table
    }
    
    if not run_flow('ArticleEnrichmentFlow', generation_dir, **enrichment_params):
        logger.error("Article enrichment flow failed. Stopping pipeline.")
        return False
    
    # Step 3: Article Selection Flow
    logger.info("=" * 50)
    logger.info("STEP 3: Article Selection Flow")
    logger.info("=" * 50)
    
    # Calculate cluster_date_threshold as one week before date_threshold
    date_threshold_dt = datetime.strptime(
        date_threshold, '%a, %d %b %Y %H:%M:%S %z'
    )
    cluster_date_threshold_dt = date_threshold_dt - timedelta(weeks=1)
    cluster_date_threshold = cluster_date_threshold_dt.strftime(
        '%a, %d %b %Y %H:%M:%S %z'
    )
    
    selection_params = {
        'date_threshold': date_threshold,
        'clean_tables': True,
        'articles_table': replicates_table,
        'selected_articles_table': selected_articles_table,
        'date_threshold': date_threshold,
        'cluster_date_threshold': cluster_date_threshold,
        'newsletter_dir': generation_dir,
        'articles_limit': selection_articles_limit
    }
    
    if not run_flow('ArticleSelectionFlow', generation_dir, **selection_params):
        logger.error("Article selection flow failed.")
        return False
    
    logger.info("=" * 50)
    logger.info("NEWSLETTER GENERATION COMPLETED SUCCESSFULLY")
    logger.info(f"Results saved in: {generation_dir}")
    logger.info("=" * 50)
    
    return True


def main():
    """Main entry point for the newsletter generation script."""
    parser = argparse.ArgumentParser(
        description="Generate newsletter by running the complete pipeline"
    )
    
    parser.add_argument(
        '--ingestion-articles-table',
        type=str,
        required=True,
        help='Table where to save ingested articles'
    )
    
    parser.add_argument(
        '--replicates-table',
        type=str,
        required=True,
        help='Table where to save replicated articles'
    )
    
    parser.add_argument(
        '--selected-articles-table',
        type=str,
        required=True,
        help='Table where to save selected articles'
    )
    
    parser.add_argument(
        '--date-threshold',
        type=str,
        required=True,
        help=('Date threshold for article processing (RFC 2822 format, '
              'e.g., "Thu, 03 Apr 2025 18:00:00 +0000")')
    )
    
    parser.add_argument(
        '--articles-limit',
        type=int,
        default=None,
        help='Maximum number of articles to process (default: no limit)'
    )
    
    parser.add_argument(
        '--selection-articles-limit',
        type=int,
        default=5,
        help='Maximum number of selected articles to process (default: no limit)'
    )
    
    parser.add_argument(
        '--clean-tables',
        type=bool,
        default=False,
        help='Clean tables before processing'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate date threshold format
    try:
        datetime.strptime(args.date_threshold, '%a, %d %b %Y %H:%M:%S %z')
    except ValueError:
        logger.error(
            "Invalid date_threshold format. Expected format: "
            "'Thu, 03 Apr 2025 18:00:00 +0000'"
        )
        sys.exit(1)
    
    # Run the newsletter generation pipeline
    success = generate_newsletter(
        date_threshold=args.date_threshold,
        ingestion_articles_table=args.ingestion_articles_table,
        replicates_table=args.replicates_table,
        selected_articles_table=args.selected_articles_table,
        articles_limit=args.articles_limit,
        selection_articles_limit=args.selection_articles_limit,
        clean_tables=args.clean_tables,
        verbose=args.verbose
    )
    
    if success:
        logger.info("Newsletter generation completed successfully!")
        sys.exit(0)
    else:
        logger.error("Newsletter generation failed!")
        sys.exit(1)


if __name__ == '__main__':
    main() 
from metaflow import FlowSpec, step, Parameter

from hex.flows.article_ingestion.steps.start import execute as start_step
from hex.flows.article_ingestion.steps.ingest_rss_articles \
    import execute as ingest_rss_articles_step
from hex.flows.article_ingestion.steps.prepare_report \
    import execute as prepare_report_step
from hex.flows.article_ingestion.steps.end import execute as end_step


class ArticleIngestionFlow(FlowSpec):
    """
    Metaflow implementation of the article ingestion pipeline.

    This pipeline ingests articles from RSS feeds. 
    """

    # Define parameters that can be passed to the flow
    articles_table = Parameter('articles_table',
                               help='Table where to save articles',
                               default='articles')

    articles_limit = Parameter('articles_limit',
                               help='Maximum number of articles to load',
                               default=None,
                               type=int)

    date_threshold = Parameter('date_threshold',
                               help='Keep articles published after this date',
                               default='Thu, 03 Apr 2025 18:00:00 +0000')

    clean_tables = Parameter('clean_tables',
                                help=('Clean tables '
                                      '(articles_table)'),
                                default=False)

    @step
    def start(self):
        """Initialize the pipeline."""
        start_step(self)
        print("start")
        self.next(self.ingest_rss_articles)

    @step
    def ingest_rss_articles(self):
        """Ingest articles from RSS feeds."""
        ingest_rss_articles_step(self)
        self.next(self.prepare_report)

    @step
    def prepare_report(self):
        """Prepare a report with metrics and statistics."""
        prepare_report_step(self)
        self.next(self.end)

    @step
    def end(self):
        """Generate final report and complete the pipeline."""
        end_step(self)


if __name__ == '__main__':
    ArticleIngestionFlow()

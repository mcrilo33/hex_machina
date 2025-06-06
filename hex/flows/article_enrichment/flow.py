import logging
from metaflow import FlowSpec, step, Parameter

# Import individual step functions
from ttd.flows.article_enrichment.steps.start import execute as start_step
from ttd.flows.article_enrichment.steps.load_articles \
    import execute as load_articles_step
from ttd.flows.article_enrichment.steps.is_ai_articles \
    import execute as is_ai_articles_step
from ttd.flows.article_enrichment.steps.dense_summarizer \
    import execute as dense_summarizer_step
from ttd.flows.article_enrichment.steps.core_line_summarizer \
    import execute as core_line_summarizer_step
from ttd.flows.article_enrichment.steps.tagger import execute as tagger_step
from ttd.flows.article_enrichment.steps.merge_same_tags \
    import execute as merge_same_tags_step
from ttd.flows.article_enrichment.steps.update_tags import execute as update_tags_step
from ttd.flows.article_enrichment.steps.update_clusters \
    import execute as update_clusters_step
from ttd.flows.article_enrichment.steps.replicate_articles \
    import execute as replicate_articles_step
from ttd.flows.article_enrichment.steps.prepare_report \
    import execute as prepare_report_step
from ttd.flows.article_enrichment.steps.end import execute as end_step

logger = logging.getLogger(__name__)

class ArticleEnrichmentFlow(FlowSpec):
    """
    Metaflow implementation of the article processing pipeline.

    This pipeline processes articles, classifies them, generates summaries,
    extracts tags, and organizes them into clusters.
    """

    # Define parameters that can be passed to the flow
    articles_table = Parameter('articles_table',
                               help='Table to load articles from',
                               default='articles')

    articles_limit = Parameter('articles_limit',
                               help='Maximum number of articles to process',
                               default=None)

    date_threshold = Parameter('date_threshold',
                               help='Process articles published after this date',
                               default='Thu, 03 Mar 2025 18:00:00 +0000')

    replicates_table = Parameter('replicates_table',
                                help='Replicates articles to this table',
                                default='replicated_articles')

    clean_tables = Parameter('clean_tables',
                                help=('Clean tables '
                                      '(tags, tag_clusters, tagged_articles, replicated_articles)'),
                                default=False)

    @step
    def start(self):
        """Initialize the pipeline."""
        start_step(self)
        print("start")
        self.next(self.load_articles)

    @step
    def load_articles(self):
        """Load articles published after a date threshold."""
        load_articles_step(self)
        if len(self.articles) == 0:
            logger.warning("No articles to process.")
            logger.warning("Exiting flow.")
            self.next(self.end)
            return
        self.next(self.is_ai_articles)

    @step
    def is_ai_articles(self):
        """Classify articles as AI-generated or not."""
        is_ai_articles_step(self)
        self.next(self.dense_summarizer)

    @step
    def dense_summarizer(self):
        """Generate dense summaries for articles."""
        dense_summarizer_step(self)
        self.next(self.core_line_summarizer)

    @step
    def core_line_summarizer(self):
        """Generate core line summaries based on dense summaries."""
        core_line_summarizer_step(self)
        self.next(self.tagger)

    @step
    def tagger(self):
        """Extract tags from dense summaries."""
        tagger_step(self)
        self.next(self.merge_same_tags)

    @step
    def merge_same_tags(self):
        """Merge extracted tags across articles."""
        merge_same_tags_step(self)
        self.next(self.update_tags)

    @step
    def update_tags(self):
        """Save or update tags in the database."""
        update_tags_step(self)
        self.next(self.update_clusters)

    @step
    def update_clusters(self):
        """Save or update tags in the database."""
        update_clusters_step(self)
        self.next(self.replicate_articles)

    @step
    def replicate_articles(self):
        """Replicate articles with enriched data."""
        replicate_articles_step(self)
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
    ArticleEnrichmentFlow()

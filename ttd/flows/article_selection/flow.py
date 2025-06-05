from metaflow import FlowSpec, step, Parameter

from ttd.flows.article_selection.steps.start import execute as start_step
from ttd.flows.article_selection.steps.load_articles import execute as load_articles_step
from ttd.flows.article_selection.steps.select_articles import execute as select_articles_step
from ttd.flows.article_selection.steps.prepare_report \
    import execute as prepare_report_step
from ttd.flows.article_enrichment.steps.end import execute as end_step


class ArticleSelectionFlow(FlowSpec):
    """
    Metaflow implementation of the article selection pipeline.

    This pipeline loads already processed articles and classifies them.
    """

    # Define parameters that can be passed to the flow
    articles_table = Parameter('articles_table',
                               help='Table to load articles from',
                               default='articles')

    articles_limit = Parameter('articles_limit',
                               help='Maximum number of articles to select',
                               default=2)

    date_threshold = Parameter('date_threshold',
                               help='Select articles published after this date',
                               default='Thu, 03 Apr 2025 18:00:00 +0000')

    cluster_date_threshold = Parameter('cluster_date_threshold',
                               help='articles published after this date are used to compute clusters scores',
                               default='Thu, 03 Apr 2025 18:00:00 +0000')

    clean_tables = Parameter('clean_tables',
                                help=('Clean tables '
                                      '(selections, selected_articles)'),
                                default=False)

    selected_articles_table = Parameter('selected_articles_table',
                               help='Table to register selected articles',
                               default='selected_articles')

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
            self.log.warning("No articles to process.")
            self.log.warning("Exiting flow.")
            self.next(self.end)
            return
        self.next(self.select_articles)

    @step
    def select_articles(self):
        """Select articles based on a classification model."""
        select_articles_step(self)
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
    ArticleSelectionFlow()

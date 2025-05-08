""" End step. """
import logging

logger = logging.getLogger(__name__)


def execute(flow):
    """ Finalize the pipeline. """
    logger.info("Finishing the pipeline")

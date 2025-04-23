"""
ttd.enricher
------------

This module defines and exposes enrichment pipelines used to transform or predict values over article data.

Exports:
    - get_alpha_pipeline: A baseline enrichment pipeline used in the production routine.
"""

from .providers import get_alpha_pipeline, get_beta_pipeline

__all__ = [
    "get_alpha_pipeline",
    "get_beta_pipeline"
]
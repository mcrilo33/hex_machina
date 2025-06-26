#!/usr/bin/env bash
# -- run_generate_newsletter.sh ---------------------------------------------
# Builds the current date in RFC-2822 format and launches the generator.

export PYTHONPATH="./hex:$PYTHONPATH"
NOW_UTC="$(LC_TIME=C date -u -v-7d +"%a, %d %b %Y %H:%M:%S +0000")"
echo "NOW_UTC: $NOW_UTC"

python generate_newsletter.py \
  --ingestion-articles-table 'articles' \
  --replicates-table 'replicates' \
  --articles-limit 100 \
  --date-threshold "${NOW_UTC}" \
  --selection-articles-limit 6 \
  --selected-articles-table 'selected_articles_dummy_table'
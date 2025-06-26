#!/usr/bin/env bash
# -- run_generate_newsletter.sh ---------------------------------------------
# Builds the current date in RFC-2822 format and launches the generator.

source /Users/mathieucrilout/.miniconda3/bin/activate ttd
export PYTHONPATH="/Users/mathieucrilout/Repos/hex_machina/hex:$PYTHONPATH"
cd /Users/mathieucrilout/Repos/hex_machina || exit 1
NOW_UTC="$(LC_TIME=C date -u -v-7d +"%a, %d %b %Y %H:%M:%S +0000")"
echo "NOW_UTC: $NOW_UTC"

exec /Users/mathieucrilout/Repos/hex_machina/generate_newsletter.py \
  --ingestion-articles-table 'articles' \
  --replicates-table 'replicates' \
  --date-threshold "${NOW_UTC}" \
  --selection-articles-limit 6 \
  --selected-articles-table 'selected_articles_dummy_table'
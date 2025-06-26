# <img src="./docs/images/hex-eye.png" alt="hex-eye" width="38" height="38"/> Hex Machina – AI Newsletter Service

**Hex Machina is a free, AI-driven newsletter service** that automatically monitors AI research, blogs, and announcements, summarizes key insights, and delivers **high-quality, concise newsletters**.

> AI News, Compiled by the Machine.
You can find the newsletter at the following URL: **[https://hexmachina.beehiiv.com/](https://hexmachina.beehiiv.com/)**

Each newsletter was generated automatically with this project.

## <img src="./docs/images/hex-eye.png" alt="hex-eye" width="28" height="28"/> Overview

Keeping up with the **fast-moving AI landscape** is **time-consuming**. Traditional manual curation can't scale.  
**Hex Machina solves this with automated intelligence.**

## ✔ Features & Scope

**Ingestion** → Ingests articles from AI-related websites. <img src="./docs/images/hex-eye.png" alt="hex-eye" width="24" height="24"/>  

**Article Enrichment Flow** → Adds tags, summaries, etc... <img src="./docs/images/hex-eye.png" alt="hex-eye" width="24" height="24"/>  

**Selection** → Selects most relevant items in an unsupervised way. <img src="./docs/images/hex-eye.png" alt="hex-eye" width="24" height="24"/>  


**Newsletter Generator** → Compiles and formats weekly updates. <img src="./docs/images/hex-eye.png" alt="hex-eye" width="24" height="24"/>  

**Orchestration Script** → Runs the full pipeline automatically. <img src="./docs/images/hex-eye.png" alt="hex-eye" width="24" height="24"/>  

## 🏗 Technology Stack

| Component          | Technology                   |
|--------------------|------------------------------|
| Scraping           | Scrapy                       |
| Database           | TinyDB                       |
| LLMs               | OpenRouter / OpenAI          |
| Tagging & NLP      | Hugging Face / OpenAI        |
| Workflow           | Metaflow                     |
| Hosting            | Beehiiv                      |
| Ochestration       | Cronjob                      |

## 🚀 How to Run

### Prerequisites

1. **Python 3.9+** installed
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your environment variables** in the existing `.env` file:

   > **Note:** You need a paid, working API key for both OpenAI and OpenRouter platforms.  
   > Don't worry—processing thousands of articles typically costs only a couple of cents.

   ```bash
   # OpenAI API keys
   OPENAI_API_KEY=your_openai_api_key
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```
You can customize which RSS feeds are ingested by editing the following files:

- `data/rss_feeds.txt`: Add or remove URLs (one per line) to control which RSS feeds are scraped by the standard scraper.
- `data/rss_feeds_stealth.txt`: Add URLs here to use the stealth mode scraper, which is designed to bypass security checks and scrape sites that block regular scrapers.

Simply add the desired feed URLs to these files before running the pipeline to expand or modify your sources.

### Running the Full Pipeline

**Option 1: Using the shell script (recommended)**
> **Note:**  
> The `--articles-limit 100` flag controls how many articles are processed (about 10 minutes to run).  
> You can **remove** this limit or **increase** it to fetch and process more articles if you want a newsletter selected over more articles.  

```bash
chmod +x run_generate_newsletter.sh
./run_generate_newsletter.sh
```

**Option 2: Direct Python execution**
```bash
export PYTHONPATH="./hex:$PYTHONPATH"
python generate_newsletter.py \
  --ingestion-articles-table 'articles' \
  --replicates-table 'replicates' \
  --articles-limit 100 \
  --date-threshold "$(date -u -v-7d +"%a, %d %b %Y %H:%M:%S +0000")" \
  --selection-articles-limit 6 \
  --selected-articles-table 'selected_articles_dummy_table'
```

### Running Individual Flows

You can also run each flow separately:

```bash
# Article Ingestion Flow
python -m hex.flows.article_ingestion.flow run --with card

# Article Enrichment Flow  
python -m hex.flows.article_enrichment.flow run --with card

# Article Selection Flow
python -m hex.flows.article_selection.flow run --with card
```

### Output

The output of each pipeline run is organized in a timestamped folder inside `./generated_newsletters/`. Here is an example of the directory structure you will find after a run:

```text
generated_newsletters/2025-06-26_18-37-55
├── articleenrichmentflow_flow.log
├── articleenrichmentflow_report.html
├── articleingestionflow_flow.log
├── articleselectionflow_flow.log
├── articleselectionflow_report.html
├── images
│   ├── edito_image.png
│   └── hexmachina_wordcloud.png
└── newsletter_report.txt
```



## 📚 Documentation

[Hex Machina Documentation](docs/README.md)

## 💬 Contact & Support

For questions or contributions, contact **Mathieu Crilout** at <mathieu.crilout@gmail.com>.

## ⭐ Like this project?

If you find this useful, give it a ⭐ on **GitHub!** 😊

## 📜 License

The code is public, you can look at it, but this software is proprietary and owned by **Mathieu Crilout**.  
Unauthorized use, distribution, or modification is prohibited.

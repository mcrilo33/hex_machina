# 📢 Train, Tune, Deploy - AI Newsletter Service

🚀 **TTD (Train, Tune, Deploy) is a free, AI-driven newsletter service** that automatically monitors AI research, blogs, and announcements, summarizes key insights, and delivers **high-quality, concise newsletters**.

> AI News, Curated by AI.

## 📌 Overview

Keeping up with the **fast-moving AI landscape** is **time-consuming**. Traditional manual curation can’t scale.

💡 **TTD automates AI news curation**, leveraging **state-of-the-art AI models** to:

✅ Fetch **AI-related articles** from trusted sources.

✅ Tag, summarize, and classify posts for relevance.

✅ Format the best insights into **a structured newsletter**.

🔎 **The goal? Effortless, high-quality AI updates in one place.**

## 📜 Background

Most AI newsletters today are either:

❌ **Too limited** → They miss key developments.

❌ **Too time-consuming**.

🧠 **TTD solves this** using **AI-driven automation**, ensuring:

🔹 **Comprehensive coverage** of AI research.

🔹 **Timely and relevant content** filtering.

🔹 **Automatic newsletter generation** without human intervention.

## ✅ Features & Scope

### ✔ In-Scope

✔ **Scraper** → Fetches articles from AI-related websites.

✔ **Enricher** → Adds tags, reading time, complexity, summaries.

✔ **Classifier** → Selects most relevant items and filters out noise.

✔ **Newsletter Generator** → Compiles and formats daily updates.

✔ **Orchestration Script** → Runs the full pipeline automatically.

### ❌ Out of Scope (MVP)

🚫 **Social media sources** (Twitter, LinkedIn, etc.).

🚫 **Personalized content filtering** (future enhancement).

🚫 **Paid content sources**. *But no worries, there are a lot of very high quality publicly available content*.

### 📌 Key Components:

- Scraper 🕵️‍♂️ → Fetches AI articles hourly from public sources.
- Enricher 🤖 → Adds tags, reading time, and multi-level summaries.
- Classifier 🏆 → Scores relevance & filters bad items.
- Newsletter Generator 📝 → Formats top AI stories into a digest.
- Orchestrator 🔄 → Runs the entire pipeline automatically.

## 🏗 Technology Stack

| Component | Technology |
| --- | --- |
| Scraping            | Scrapy                       |
| Database            | TinyDB                       |
| Tagging & NLP       | Hugging Face / OpenAI API    |
| Summarization       | Transformer-based models     |
| Hosting             | Beehiv                       |
| Automation          | Cron Jobs / Python Scripts   |

## 📚 Documentation

[TTD Newsletter Documentation](docs/README.md)

##  Contact & Support

For questions or contributions, contact **Mathieu Crilout** at <mathieu.crilout@gmail.com>.

## ⭐ Like this project?

If you find this useful, give it a ⭐ on **GitHub!** 😊

## 📜 License

This software is proprietary and owned by **Mathieu Crilout**.  
Unauthorized use, distribution, or modification is prohibited.  
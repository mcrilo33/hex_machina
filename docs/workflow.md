# 🔁 Workflow Diagram

```mermaid
sequenceDiagram
    participant Scraper
    participant Enricher
    participant Classifier
    participant NewsletterFormatter
    participant WebService

    Scraper->>Enricher: Extract Metadata & Content
    Enricher->>Classifier: Tag, Summarize, etc...
    Classifier->>NewsletterFormatter: Rank
    NewsletterFormatter->>WebService: Generate Newsletter
```
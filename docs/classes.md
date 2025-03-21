# 🧱 Class Design

## Storage Services

```mermaid
classDiagram
    %% ===== BASE STORAGE SERVICE =====
    class StorageService {
        <<Service>>
        +get_table(table_name)
        +insert(table_name, data)
        +update(table_name, data, query_field, query_value)
        +delete(table_name, query_field, query_value)
        +get_all(table_name)
        +count_records(table_name)
    }
    %% ===== ARTICLE-SPECIFIC STORAGE =====
    class ArticleStorageService {
        <<Service>>
        -StorageService storage
        +save_articles(articles)
        +update_articles(articles)
        +get_articles(article_ids)
    }
    %% ===== MODEL-SPECIFIC STORAGE =====
    class ModelStorageService {
        <<Service>>
        -StorageService storage
        +save_model(model)
        +update_model(model)
        +get_model(model_id)
    }
    %% ===== PREDICTIONS STORAGE =====
    class PredictionsStorageService {
        <<Service>>
        -StorageService storage
        +save_predictions(predictions)
    }
    %% ===== TAGS STORAGE =====
    class TagsStorageService {
        <<Service>>
        -StorageService storage
        +save_tag(tag)
        +get_tag(tag_id)
        +get_tags_for_article(article_id)
    }
    %% ===== CONCEPTS STORAGE =====
    class ConceptsStorageService {
        <<Service>>
        -StorageService storage
        +save_concept(concept)
        +get_concept(concept_id)
        +get_concepts_for_article(article_id)
    }
    %% ===== RELATIONSHIPS =====
    StorageService <|-- ArticleStorageService
    StorageService <|-- ModelStorageService
    StorageService <|-- PredictionsStorageService
    StorageService <|-- TagsStorageService
    StorageService <|-- ConceptsStorageService
```

## Scrapers

```mermaid
classDiagram
    %% ===== BASE SCRAPER CLASS =====
    class BaseUrlScraper {
        <<Abstract>>
        +list~string~ source_urls
        +parse(response)*
        +store()*
    }
    %% ===== ARTICLE SCRAPER CLASS =====
    class ArticleWebsiteScraper {
        <<Abstract>>
        - ScraperStorageService storage_service
        +parse(response)*
        +parse_article(response)*
        +store(articles)
    }
    %% ===== GOOGLE RESEARCH SCRAPER =====
    class ResearchGoogleScraper {
        +parse(response)
        +parse_article(response)
    }
    %% ===== RELATIONSHIPS =====
    BaseUrlScraper <|-- ArticleWebsiteScraper
    ArticleWebsiteScraper <|-- ResearchGoogleScraper
    ArticleStorageService <-- ArticleWebsiteScraper : "Uses Storage"
```

## Enrichers

```mermaid
classDiagram 
    %% ===== BASE ENRICHER CLASS =====
    class BaseEnricher {
        <<Abstract>>
        - ModelStorageService model_storage_service
        - PredictionsStorageService predictions_storage_service
        +enrich(items)*
        +store(predictions)*
    }
    
    %% ===== ENRICHMENT PIPELINE =====
    class EnricherPipeline {
        <<Service>>
        - list~BaseEnricher~ enrichers
        +add_enricher(enricher)
        +run_pipeline(inputs)
    }

    %% ===== TAGS ENRICHER =====
    class TagsEnricher {
        - ModelStorageService model_storage_service
        - PredictionsStorageService predictions_storage_service
        - TagsStorageService tags_storage_service
        +enrich(articles)
        +store(predictions)
    }

    %% ===== CONCEPTS ENRICHER =====
    class ConceptsEnricher {
        - ModelStorageService model_storage_service
        - PredictionsStorageService predictions_storage_service
        - ConceptsStorageService concepts_storage_service
        +enrich(articles)
        +store(predictions)
    }

    %% ===== SUMMARIZATION ENRICHERS =====
    class OneLineSummaryEnricher {
        - ModelStorageService model_storage_service
        - PredictionsStorageService predictions_storage_service
        +enrich(articles)
        +store(predictions)
    }

    class OneMinSummaryEnricher {
        - ModelStorageService model_storage_service
        - PredictionsStorageService predictions_storage_service
        +enrich(articles)
        +store(predictions)
    }

    %% ===== READING TIME ENRICHER =====
    class ReadingTimeEnricher {
        - ModelStorageService model_storage_service
        - PredictionsStorageService predictions_storage_service
        +enrich(articles)
        +store(predictions)
    }

    %% ===== ARTICLE CLASSIFIER =====
    class ArticleClassifier {
        - ModelStorageService model_storage_service
        - PredictionsStorageService predictions_storage_service
        +enrich(articles)
        +store(articles)
    }

    %% ===== RELATIONSHIPS =====
    BaseEnricher <|-- TagsEnricher
    BaseEnricher <|-- ConceptsEnricher
    BaseEnricher <|-- OneLineSummaryEnricher
    BaseEnricher <|-- OneMinSummaryEnricher
    BaseEnricher <|-- ReadingTimeEnricher
    BaseEnricher <|-- ArticleClassifier

    EnricherPipeline --* BaseEnricher : "Runs Enrichers"
```
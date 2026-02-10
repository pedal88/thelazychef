# Visual Architecture Documentation 📊

This document provides visual diagrams of "The Lazy Chef" architecture, data flow, and deployment pipelines. These diagrams are rendered automatically by GitHub using Mermaid.js.

## 1. System Architecture (Bird's Eye View)
A high-level overview of how the Flask application sits between the user, Google Cloud services, and external data sources.

```mermaid
graph TD
    User[📱 User / Web Browser] -->|HTTPS| CDN[🌍 Google Cloud Run Load Balancer]
    CDN -->|Request| App[🍳 Flask App (The Lazy Chef)]

    subgraph "Google Cloud Platform"
        App -->|Read/Write| DB[(🗄️ Cloud SQL / PostgreSQL)]
        App -->|Store Images| GCS[☁️ Cloud Storage (Buckets)]
        
        subgraph "AI Services"
            App -->|Generate Recipe| Gemini[🧠 Gemini 1.5 Flash (AI Engine)]
            App -->|Generate Photos| Imagen[🎨 Imagen 3 (Vertex AI)]
        end
    end

    subgraph "External Sources"
        App -->|Scrape| Blog[🌐 Recipe Blogs]
        App -->|Download| Social[🎬 TikTok/Instagram]
    end
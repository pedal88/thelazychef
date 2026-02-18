# Resource (Blog) Creation Workflow

This swimlane diagram illustrates the lifecycle of a blog post: from AI generation to CMS processing and final publication.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as 👨🍳 Admin User
    participant AI as 🤖 Gemini Canvas
    participant CMS as 🛠️ TheLazyChef App
    participant DB as 🗄️ Database

    box rgb(240, 248, 255) Phase 1: Content Generation
    Admin->>AI: 1. Prompt: "Write a blog post about..."
    AI-->>Admin: 2. Generates Markdown Content
    Admin->>Admin: 3. Copies Markdown Code
    end

    box rgb(255, 245, 238) Phase 2: CMS Entry
    Admin->>CMS: 4. Navigates to /admin/resources/new
    Admin->>CMS: 5. Pastes Markdown & Uploads Cover Image
    Admin->>CMS: 6. Selects Status (Draft / Published)
    Admin->>CMS: 7. Clicks "Save Resource"
    end

    box rgb(240, 255, 240) Phase 3: System Processing
    CMS->>CMS: 8. Checks Slug (Auto-generates if empty)
    CMS->>CMS: 9. Uploads Image to Cloud Storage
    CMS->>DB: 10. INSERT Row into 'Resource' Table
    DB-->>CMS: 11. Confirm ID
    CMS-->>Admin: 12. Redirect to Resource List
    end

    box rgb(255, 250, 240) Phase 4: Rendering
    Admin->>CMS: 13. Views Public Page
    CMS->>DB: 14. Fetch Markdown Content
    CMS->>CMS: 15. Apply 'markdown' Filter (Text -> HTML)
    CMS-->>Admin: 16. Returns Beautifully Formatted Page
    end
```

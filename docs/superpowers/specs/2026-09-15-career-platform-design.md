# Career Platform Design Spec

## Summary

This project is a database-driven personal career platform for a professional targeting analytical and finance-focused recruiting opportunities. The product is intended to function as a polished public resume and portfolio while providing a structured content backend that can evolve into a broader career platform over time.

The implementation approach is Python-first: FastAPI for the app layer, Jinja templates for HTML rendering, and a dedicated `static/css` layer for styling. The first version should prioritize recruiter readability, role-targeted positioning, and easy content maintenance without requiring code edits for routine updates. The platform must be structured as a content system rather than a static page so it can grow into more advanced features later without a redesign.

The public profile must remain visible when the database is unavailable. In degraded mode, the site should serve the last known good profile snapshot or a static fallback profile while clearly marking the site as offline-safe, rather than showing a blank page or server error.

## Goals

- Present a strong, recruiter-friendly professional profile for analytics and finance roles
- Communicate value across resume, project work, skills, and credentials
- Support targeted positioning for multiple role categories without creating duplicate sites
- Maintain structured, editable records for resume content and portfolio items
- Provide a clean foundation for later features such as role-specific pages, content publishing, or application tracking

## Non-goals

- Multi-user team collaborative platform in v1
- Candidate sourcing or CRM workflows in v1
- Paid subscription, billing, or SaaS features in v1
- AI-driven resume generation or recommender features in v1
- Social networking or community features in v1

## Target audience

Primary audience:
- Recruiters and hiring teams evaluating candidates for analytics, finance, and adjacent business roles
- Hiring managers for strategy, operations, analytics, and financial analysis roles
- Network contacts and startup or consulting opportunities

Secondary audience:
- Collaborators, clients, and professional contacts
- Future employers evaluating work samples and case studies

## User needs

The site must answer these questions quickly:
- Who is this person, and what kind of work do they do?
- What outcomes have they delivered?
- What relevant skills and domain knowledge do they bring?
- Which role types or industries are they targeting?
- Where are they located, and what is their availability?

## Product scope

### Public site

The public site should include:
- A landing page / home page with professional positioning
- About / profile summary
- Experience timeline
- Projects and case studies
- Skills and toolset overview
- Credentials and education
- Optional thought leadership or articles section
- Contact or inquiry call to action

### Admin/content system

The admin system should allow updates to structured data without code changes. It must support:
- Profile details and contact metadata
- Multiple experience entries
- Multiple project entries
- Skill categories and proficiency levels
- Credentials, certifications, training, and education
- Role-specific positioning and tags
- Publishing state for content (draft, published, archived)
- Metadata like location, availability, and target roles

## Functional requirements

### 1. Profile management

- A single profile entity stores the core identity and summary text
- The profile includes name, headline, location, job preferences, and a short bio
- The profile supports a public summary and internal admin notes

### 2. Experience management

- Users can create, edit, and archive job experiences
- Each experience includes title, employer, dates, location, department or function, summary, and highlights
- Each entry supports metrics and quantified outcomes
- Entries can be filtered by role category or industry tag

### 3. Project management

- Users can create project case studies with title, description, problem, solution, tools, and results
- Each project can include links, tags, and role alignment
- The public site should render project cards and detailed pages

### 4. Skills and domain mapping

- Skills are stored as structured records grouped by category
- Categories may include analytics, finance, tools, business, operations, leadership, and product
- Users can indicate proficiency or relevance for each skill

### 5. Credentials and education

- Education records and certifications are stored as structured entries
- These are displayed as part of the professional profile and can be updated without code changes

### 6. Role-targeted positioning

- The platform supports different role lenses, such as analytics, finance, and related domains
- The content model should allow targeted statements without duplicating pages or fully separate sites
- The UI can render role-aware views or filters from the same underlying data

### 7. Content publishing

- Each public content item can have a draft/published status
- Draft items are only visible in admin
- Published items are visible on the public site
- Archived items are hidden but retained for history

### 8. Contact and inquiry handling

- The site may include a contact form or recruiter inquiry flow
- Inbound messages should be stored with metadata and reviewed in an admin area

### 9. Profile resilience and degraded-mode rendering

- The public profile must continue to render when the database is unavailable
- The application should attempt to load the latest successful snapshot first, then fall back to a static fallback profile if necessary
- Admin-only content editing should not block public profile visibility in a failure state
- A degraded-mode state should be logged and surfaced to the admin without exposing raw database errors to the public audience

## Non-functional requirements

### Performance

- The public site should load quickly for a simple single-user portfolio
- Content should be generated from database queries rather than slow or excessive processing
- The first release should avoid unnecessary complexity in caching or performance optimization

### Maintainability

- All content types must be modelled in a structured way with clear fields and relationships
- Repeated content patterns should be reduced through reusable templates and components
- The app should allow content updates without editing code for routine page changes

### Extensibility

- The platform must be able to add new sections without redesigning the entire site
- New collections should be able to be added through schema extensions
- The architecture should support future features like saved role filters, article pages, and application tracking

### Security

- All admin operations must be protected by authentication and authorization
- Public pages must not expose admin-only functionality
- User-submitted contact data should be validated and stored safely

## Information architecture

### Primary pages

- Home
- About
- Experience
- Projects
- Skills
- Credentials
- Contact

### Secondary pages

- Project detail page
- Role-targeted landing page (optional in v1, but the data model should support it)
- Article or insight detail page (optional future module)

### Admin pages

- Dashboard overview
- Profile editor
- Experience manager
- Projects manager
- Skills manager
- Credentials manager
- Contact submissions
- Publishing controls

## Data model

A lightweight relational database is the recommended fit for this product. The initial schema should prioritize clarity, flexibility, and easy querying, while using SQLite to keep the first implementation local and easy to run in Codespaces.

### Core entities

#### Profile
- id
- full_name
- headline
- summary
- location
- target_roles
- availability_status
- created_at
- updated_at

#### Experience
- id
- profile_id
- company_name
- title
- location
- start_date
- end_date
- current_role
- summary
- highlights_json
- metrics_json
- tags_json
- status

#### Project
- id
- profile_id
- title
- short_description
- problem_statement
- solution_summary
- tools_json
- impact_summary
- links_json
- tags_json
- status
- created_at
- updated_at

#### Skill
- id
- profile_id
- category
- name
- proficiency
- years_experience
- notes
- status

#### Credential
- id
- profile_id
- type
- name
- issuer
- date_earned
- expiration_date
- status

#### ContentPiece
- id
- profile_id
- type
- title
- slug
- excerpt
- body_markdown
- status
- published_at
- created_at
- updated_at

#### ContactSubmission
- id
- name
- email
- company
- message
- submitted_at
- processed

### Relationship notes

- One profile owns many experience, project, skill, credential, and content records
- Tag values should be normalized or stored as simple arrays depending on implementation needs
- Metrics and JSON fields are acceptable for flexible text and structured values, but the schema should remain explicit and readable

## Architecture recommendation

### Recommended stack

- Runtime: Python 3.12+
- Package/tooling: uv for dependency management and local setup
- Frontend: FastAPI with Jinja templates and a straightforward server-rendered page structure
- Server: Uvicorn for local development and runtime serving
- Backend: Python application layer with routes, validation, and admin operations
- Database: SQLite for the first implementation, with a straightforward path to upgrade to PostgreSQL later if the app grows
- ORM/migrations: SQLAlchemy 2.x with Alembic for schema evolution
- Testing: pytest, HTTPX, and FastAPI TestClient
- Styling: plain CSS in dedicated `static/css` files, optionally with a small utility layer or CSS variables for design consistency
- Hosting: first deploy locally in Codespaces for validation; later move to an Azure VM or Azure App Service-compatible deployment environment with persistent database and file storage
- Admin: concise CMS-like dashboard built into the app rather than a heavy external tool

### Why this architecture

A custom Python-based web app is the best fit because:
- the project must become content-structured and database-driven
- role targeting and curated views are easier to support in a custom data model
- the site is meant to evolve into a broader career platform without being dragged down by a static page architecture
- the content owner needs direct maintainability without relying on hardcoded front-end templates for every update
- FastAPI + Jinja is well-suited for a career profile site with a clean, template-driven public frontend and a simple admin workflow

### App boundaries

- Public frontend: reads published content and renders the portfolio/resume site using Jinja templates
- Admin interface: edits structured content and job search metadata
- Application service layer: validates and persists content updates, and handles degradation fallback logic
- Persistence layer: stores structured career content in SQLite and keeps a last-known-good snapshot for public visibility during outages
- Static assets: CSS, images, and shared frontend styling live in a dedicated `static/` structure

## User experience goals

The site should feel:
- credible and detail-oriented
- clean and recruiter-friendly
- concise, not visually noisy
- tailored to professional opportunity discovery
- strong in storytelling without being too personal or blog-like

The experience should help recruiters quickly understand:
- role alignment
- business relevance
- measurable impact
- domain knowledge and skill depth

## Content strategy

The content should emphasize value over self-promotion. The public profile should prioritize:
- concise positioning statement
- strong outcome-oriented accomplishment language
- quantifiable impact
- relevant skills and business context
- targeted examples showing fit for the roles being pursued

The site should avoid generic filler, vague claims, or purely self-focused language. It should read like a well-structured career narrative grounded in concrete work.

## Future roadmap

### Phase 1
- Resume and portfolio profile
- Structured experience and project records
- Recruiter-friendly landing pages
- Simple admin publishing workflow
- Local Codespaces deployment first for validation and iteration

### Phase 2
- Multiple role-specific views or positioning modes
- Better project detail pages and richer case studies
- Article / insights content module
- Contact submission improvements
- Production deployment on an Azure VM or equivalent Azure-hosted environment

### Phase 3
- Resume variant generation for different audiences
- Application tracking and opportunity history
- More advanced analytics and content tracking
- Expanded platform metrics and career management features

## Risks and considerations

### Overbuilding too early

The platform should not include advanced multi-user workflows, CRM, or community features before the core personal profile system is validated.

### Weak data structure

If the site is built without structured content records, routine updates will become expensive and brittle. The data model must be treated as the foundation of the product.

### Generic portfolio design

The site should not feel like a generic template. It must support clear role positioning, incentive-driven content hierarchy, and measurable accomplishments.

## Acceptance criteria

A v1 implementation is successful when all of the following are true:

- The site presents a recruiter-friendly summary and portfolio
- Experience, projects, credentials, and skills are stored in a database rather than static markup only
- The content can be edited without code-level changes for normal updates
- The site supports role-targeted positioning for analytics and finance related opportunities
- A simple admin path exists for publishing and updating content
- The site is structured to allow future expansion into a broader personal career platform

## Implementation considerations for the next phase

When implementation begins, the first milestone should be building the core data model and a minimal public rendering layer. The most important early tasks are:

1. Define and validate the schema for profile, experience, project, and skill records
2. Build a minimal admin interface for CRUD operations
3. Render the public profile from database records
4. Add a role-targeted profile view or role tags
5. Expand to additional collections only after this foundation is stable

This keeps the first delivery focused and avoids premature complexity.

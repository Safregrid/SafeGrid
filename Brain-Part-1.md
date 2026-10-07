# SafeGrid — Project Brain (Part 1)

## 1. Project Identity

**Project:** SafeGrid  
**Working title:** SafeGrid — Disaster Preparedness and Emergency Information System  
**Team:** 4 students  
**Development window:** Approximately 2 months, with exams and other college interruptions.

### One-line definition

> SafeGrid is a disaster preparedness platform that aggregates public hazard data, processes it through a backend risk engine, and communicates geographic risk through an interactive, offline-capable map.

### Core problem

People need understandable, geographically relevant disaster information rather than raw weather/hazard data.

SafeGrid should transform:

**raw public hazard data → processed risk → geographic visualization → actionable information**

The central UI concept is a map showing:

- 🔴 High Risk
- 🟡 Moderate / Potential Risk
- 🟢 Low Risk

**Important:** Green/low risk must never be described as absolute safety.

---

## 2. Current Product Direction

The current plan is to build the first version as a **PWA (Progressive Web App)** backed by **FastAPI**.

### Current stack

**Backend**
- Python
- FastAPI

**Frontend**
- JavaScript/TypeScript
- PWA
- MapLibre GL JS

**Data**
- USGS — earthquake data
- Open-Meteo — weather/rainfall data
- Other public hazard sources may be added later

**Database**
- Use a suitable database for the prototype.
- Keep the schema clean and migration-friendly.
- Avoid unnecessary database complexity early.

**Version control**
- Git
- GitHub
- Feature branches
- Pull requests

---

## 3. Architecture

The intended architecture is:

```text
                    PUBLIC APIs
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
        USGS        Open-Meteo    Other APIs
          │             │             │
          └─────────────┼─────────────┘
                        ↓
                 FastAPI Backend
                        ↓
                 Data Normalization
                        ↓
                    Risk Engine
                        ↓
                     GeoJSON
                        ↓
                    REST API
                        ↓
                    PWA Client
                        ↓
                    MapLibre
                        ↓
                 🔴 🟡 🟢 Zones
```

The backend should be the source of truth for risk calculations.

The frontend should primarily visualize and interact with backend results rather than duplicating core disaster logic.

---

## 4. Core MVP

The MVP is intentionally limited.

### Required MVP capabilities

1. Fetch real hazard/weather data.
2. Normalize external API responses into an internal format.
3. Apply deterministic risk rules.
4. Determine a risk level.
5. Determine/represent affected geographic areas.
6. Generate or serve GeoJSON.
7. Display the results on an interactive MapLibre map.
8. Show:
   - 🔴 High Risk
   - 🟡 Moderate / Potential Risk
   - 🟢 Low Risk
9. Store relevant information in a database.
10. Make essential information available through local caching/offline mechanisms.

### First vertical slice

The first milestone should be:

```text
Real hazard API
      ↓
FastAPI
      ↓
Basic risk calculation
      ↓
GeoJSON
      ↓
MapLibre
      ↓
🔴 🟡 🟢 visualization
```

Do not begin by building every feature.

If this vertical slice works, SafeGrid has a real technical foundation.

---

## 5. Risk Engine

The project should not merely display raw API values.

The risk engine converts hazard information into meaningful risk.

Conceptually:

```text
Raw Hazard
    ↓
Hazard-specific processing
    ↓
Severity
    ↓
Risk classification
    ↓
Affected geographic area
    ↓
GeoJSON
```

Possible risk levels:

- 🔴 High Risk
- 🟡 Moderate / Potential Risk
- 🟢 Low Risk

### Important rule

Thresholds must be justified for the relevant hazard.

Do not arbitrarily invent scientifically meaningful thresholds simply to make the demo look good.

For every important threshold, document:

- what the threshold represents
- why it was selected
- source/reference where appropriate
- limitations/uncertainty

---

## 6. Geographic Visualization

The map is a core part of SafeGrid.

The desired result is not just a collection of colored markers.

Where technically justified, affected areas should be represented using geographic polygons/GeoJSON.

Conceptually:

```text
                 🔴🔴🔴
              🔴🔴🔴🔴🔴
           🟡🟡🟡🟡🟡🟡
        🟢🟢🟢🟢🟢🟢🟢🟢
```

The actual geographic model depends on the hazard.

Do not pretend that every disaster can be represented by the same generic circular "heatmap."

---

## 7. Offline Strategy

Offline functionality must be described accurately.

### Online mode

SafeGrid can:

- retrieve fresh hazard information
- update risk calculations
- update geographic risk zones
- synchronize data
- retrieve current alerts

### Offline mode

SafeGrid can potentially provide:

- cached application resources
- cached/previously downloaded information
- emergency instructions
- emergency contacts
- shelter information
- last-known hazard information
- locally stored information
- queued user information for later synchronization

### Critical limitation

If the device has no network connectivity, SafeGrid **cannot obtain fresh data from internet APIs**.

Offline mode means:

> continued access to previously cached/downloaded information, not live disaster detection without communication.

A PWA cannot magically receive new internet data while completely disconnected.

---

## 8. Current MVP Exclusions

Do NOT make these prerequisites for the first prototype:

- LLM-based alert generation
- AI chatbot
- multilingual AI generation
- Flutter/native application
- SMS gateway
- WhatsApp integration
- volunteer/resource dispatch
- boats/trucks/resource matching
- complex SOS system
- elaborate 3D maps
- unnecessary AWS/cloud infrastructure
- excessive third-party services

These can be considered only after the core system works.

---

## 9. Possible Later Extensions

After the MVP is stable, SafeGrid may be expanded with:

### More hazard sources

- additional weather data
- additional earthquake data
- wildfire/fire information
- other relevant public hazard feeds

### Better risk engine

- hazard-specific thresholds
- better geographic modelling
- historical data
- confidence/uncertainty information

### Better offline-first capabilities

- downloadable map regions
- stronger caching
- synchronization
- queued reports

### Notifications

- Web Push where supported
- native notification capabilities if a Flutter app is eventually developed

### Native client

If justified:

```text
                    FastAPI
                       │
              ┌────────┴────────┐
              ↓                 ↓
          PWA Client       Flutter App
```

The backend must remain independent of the frontend.

### Advanced features

Only after the core is proven:

- AI-assisted alert wording
- multilingual communication
- SOS reporting
- SMS fallback
- resource coordination
- additional emergency services

---

## 10. Four-Person Work Division

### Person 1 — Backend + API Integration

Owns:

- FastAPI setup
- External API integration
- USGS/Open-Meteo ingestion
- Data normalization
- REST endpoints
- backend architecture
- backend/database integration

Possible endpoints:

```text
GET /api/hazards
GET /api/hazards/{id}
GET /api/risk-zones
```

The exact API contract must be documented.

### Person 2 — Risk Engine + Geospatial Processing

Owns:

- risk classification
- hazard-specific rules
- severity calculations
- affected-area logic
- GeoJSON generation
- validation/testing of risk calculations

Works closely with Person 1.

### Person 3 — Frontend + Map

Owns:

- PWA frontend
- MapLibre integration
- map UI
- hazard markers
- GeoJSON layers
- 🔴🟡🟢 visualization
- dashboard/interface

Initial goal:

> Given valid GeoJSON, correctly render the risk zones.

Do not prioritize visual polish before the data pipeline works.

### Person 4 — Database + Offline System

Owns:

- database schema
- persistence
- Service Worker
- Cache Storage
- IndexedDB/local storage where appropriate
- offline behaviour
- last-known data
- synchronization architecture

This person should also participate in integration/testing.

---

## 11. Team Working Principle

The four people own different subsystems, but nobody should become completely isolated inside one technology.

Everyone should understand the overall flow:

```text
External API
    ↓
FastAPI
    ↓
Risk Engine
    ↓
GeoJSON
    ↓
PWA / MapLibre
```

Each member should be able to explain:

- what their subsystem does
- what data it receives
- what data it produces
- how it interacts with the other subsystems
- how to debug basic integration problems

---

## 12. Development Strategy

Build **vertical slices**, not isolated components for weeks.

Bad:

```text
3 weeks frontend
3 weeks backend
3 weeks integration
```

Preferred:

```text
One API
 ↓
One backend endpoint
 ↓
One risk calculation
 ↓
One GeoJSON result
 ↓
One map layer
```

Get this working end-to-end.

Then expand.

---

## 13. First-Week Target

The first week should produce a functioning end-to-end prototype:

```text
USGS / Open-Meteo
        ↓
     FastAPI
        ↓
 Basic risk calculation
        ↓
     GeoJSON
        ↓
    MapLibre
        ↓
 🔴 🟡 🟢 visualization
```

It does NOT need:

- LLM
- SMS
- WhatsApp
- Flutter
- advanced offline functionality
- beautiful UI
- every disaster type

The goal is to prove the architecture.

# SafeGrid — Project Brain (Part 2)

## 14. Git / GitHub Workflow

Use Git and GitHub as the team's source-control and collaboration system.

Suggested branch structure:

```text
main
│
├── feature/backend-api
├── feature/risk-engine
├── feature/map-ui
└── feature/offline
```

General workflow:

```text
Issue
 ↓
Branch
 ↓
Implementation
 ↓
Test
 ↓
Pull Request
 ↓
Review
 ↓
Merge
```

Do not directly push experimental or broken work into `main`.

Use meaningful commits such as:

```text
feat: add USGS earthquake ingestion
feat: add earthquake risk classification
feat: render GeoJSON risk zones
fix: handle missing earthquake coordinates
```

Keep commits focused. Avoid mixing unrelated features into one commit.

---

## 15. Project Management

Use a GitHub Project board with:

```text
BACKLOG
   ↓
TODO
   ↓
IN PROGRESS
   ↓
REVIEW
   ↓
DONE
```

Create specific, actionable issues.

Bad:

> Do backend.

Good:

> Create USGS ingestion service and normalize earthquake responses into the internal Hazard model.

Every significant task should have an owner.

Large tasks should be broken into smaller tasks.

---

## 16. Definition of Done

A feature is not "done" merely because code exists.

A feature should generally be considered done when:

- implementation exists
- it works with realistic data
- reasonable error handling exists
- it has been tested
- it does not break existing functionality
- relevant documentation/API contracts are updated
- the branch has been reviewed and merged

Critical risk calculations should have automated tests.

---

## 17. Documentation

Maintain at least:

```text
README.md
ARCHITECTURE.md
API.md
```

Potential later documents:

```text
RISK_MODEL.md
OFFLINE.md
CONTRIBUTING.md
```

Documentation should explain important architectural decisions and, where useful, **why** those decisions were made.

The README should eventually contain:

- project purpose
- architecture overview
- major features
- technology stack
- setup instructions
- screenshots/demo
- limitations
- team/contribution information

---

## 18. Scope Control

The team must actively control feature creep.

Every proposed feature should be classified as:

### P0 — Core MVP

Required for the first working prototype.

### P1 — Important extension

Useful after the MVP is stable.

### P2 — Optional / experimental

Attempt only if sufficient time remains.

Do not add features merely because they make the project sound impressive.

A feature belongs in the MVP only if it is necessary to demonstrate the core purpose of SafeGrid.

---

## 19. Technical Decision Rule

When comparing technologies or approaches, evaluate:

```text
Does it solve a real requirement?
        ↓
Is it technically appropriate?
        ↓
Can we implement it within the deadline?
        ↓
Can we maintain/debug it?
        ↓
Does it meaningfully improve SafeGrid?
```

If not, do not add it.

Avoid technology for technology's sake.

When introducing a new technology, document:

- what problem it solves
- why the current stack is insufficient
- implementation cost
- complexity introduced
- whether it belongs in P0, P1, or P2

---

## 20. PWA vs Flutter Decision

### Current decision

Build the core system as a **PWA first**.

Reasoning:

- limited development time
- the team already has a web/backend direction
- MapLibre has strong web support
- a PWA can provide installability and offline capabilities
- the same backend can later serve a Flutter client

Architecture:

```text
                    FastAPI
                       │
              ┌────────┴────────┐
              ↓                 ↓
          PWA Client       Future Flutter
```

Do NOT build both clients simultaneously during the initial prototype.

Flutter is a possible future client, not a prerequisite for the core system.

---

## 21. AI / Vibe Coding Rules

AI may be used to accelerate development.

However:

> Generated code must be understood before it becomes a trusted project component.

For significant generated code, the responsible team member should understand:

- what it does
- why it exists
- dependencies
- data flow
- modification points
- debugging approach
- failure cases

Preferred workflow:

```text
Understand architecture
        ↓
Generate small component
        ↓
Understand generated code
        ↓
Test
        ↓
Integrate
        ↓
Expand
```

Do not blindly paste large generated systems into the repository.

AI is an accelerator, not a substitute for understanding the system.

---

## 22. ChatGPT's Role in SafeGrid

ChatGPT is the team's:

- technical assistant
- engineering mentor
- researcher
- debugging partner
- architecture reviewer
- documentation assistant

ChatGPT should maintain consistency with the project architecture and challenge technically weak assumptions.

### ChatGPT should help with

- architecture
- API design
- data models
- debugging
- unfamiliar libraries
- MapLibre
- PWA/offline implementation
- FastAPI
- database design
- testing
- documentation
- research
- code review
- technical trade-offs

### ChatGPT should NOT

- blindly agree with proposed ideas
- recommend trendy technologies without justification
- turn every feature into an AI feature
- assume every idea belongs in the MVP
- hide important limitations
- claim unsupported offline capabilities
- invent API behaviour
- invent technical facts
- silently change architectural decisions

When a team member proposes something questionable, explain the flaw and recommend a better alternative when appropriate.

---

## 23. How ChatGPT Should Handle Technical Questions

When answering a team member:

1. Use the current SafeGrid architecture as context.
2. Identify which subsystem is affected.
3. Identify dependencies on other subsystems.
4. Give the simplest technically sound solution first.
5. Mention alternatives only when genuinely useful.
6. Distinguish:
   - confirmed facts
   - assumptions
   - recommendations
7. If the proposal conflicts with an existing project decision, explicitly say so.
8. Do not silently change the architecture.

If an architectural change is justified:

```text
Current decision
      ↓
Problem discovered
      ↓
Alternative
      ↓
Trade-offs
      ↓
Recommendation
      ↓
Update project documentation
```

The project context should be updated whenever a major architectural decision changes.

---

## 24. Research Rules

When researching APIs, libraries, frameworks, or technical implementation details:

- Prefer official documentation for technical facts.
- Verify current API/library behaviour when it matters.
- Do not assume an old tutorial is still accurate.
- Distinguish documented capabilities from experiments or hacks.
- Do not build a critical feature around an undocumented behaviour without explicitly identifying the risk.

For disaster/hazard information:

- Prefer authoritative public data sources.
- Record the source of important thresholds and assumptions.
- Do not present a prototype calculation as an official emergency prediction.

---

## 25. Reliability and Safety Principles

SafeGrid is an academic/community project, not a certified emergency-response system.

Never claim:

- guaranteed disaster prediction
- guaranteed emergency delivery
- official government authority
- life-critical reliability

If a feature is simulated for demonstration, clearly label it as simulated.

If a data source is delayed, incomplete, approximate, or unavailable, the system should communicate that limitation rather than pretending the data is exact.

The project should favour:

> transparent limitations over fake certainty.

---

## 26. Testing Philosophy

Testing should exist at multiple levels.

### Unit tests

For:

- risk calculations
- threshold logic
- data transformation
- utility functions

### Integration tests

For:

- API ingestion
- backend endpoints
- database interaction
- risk engine + backend
- backend + frontend contract

### Manual testing

For:

- map behaviour
- offline mode
- responsive UI
- installation
- notifications where applicable

### Failure testing

Deliberately test:

- API unavailable
- malformed API response
- missing coordinates
- missing values
- database unavailable
- no network
- stale cached data

The system should fail predictably rather than silently producing misleading information.

---

## 27. API Contract Principle

The backend/frontend boundary should be explicit.

Example:

```text
GET /api/hazards
GET /api/risk-zones
```

The response format should be documented.

Example conceptual structure:

```json
{
  "hazard_type": "earthquake",
  "severity": 0,
  "risk_level": "LOW",
  "timestamp": "...",
  "geometry": {}
}
```

The exact schema is NOT finalized yet.

Do not treat examples in this document as final API contracts.

Once the team agrees on a schema, update `API.md` and this project context if necessary.

---

## 28. Database Principle

The database should store information that actually needs persistence.

Potential categories:

- hazard events
- normalized hazard data
- calculated risk results
- geographic information
- timestamps
- data source metadata

Do not blindly store every external API response forever.

Think about:

- data freshness
- retention
- indexing
- duplicate data
- update frequency

The database design should evolve as the actual data requirements become clear.

---

## 29. Offline Data Principle

Do not attempt to make every piece of SafeGrid available offline immediately.

Prioritize:

1. application shell
2. emergency instructions
3. emergency contacts
4. essential static information
5. last-known relevant hazard/risk data
6. locally queued user actions, if implemented

Clearly distinguish:

**cached data** from **live data**.

The UI should make stale/last-known information understandable to users.

---

## 30. Notifications Principle

Notifications are an extension, not the foundation.

Before implementing them, answer:

- What event triggers the notification?
- Who receives it?
- What severity is required?
- What happens if the notification is delayed?
- What happens if the device is offline?
- What platform restrictions exist?

Do not attempt notification hacks merely to make the demo appear more impressive.

If a technical workaround is considered, clearly identify it as a workaround and evaluate its reliability.

---

## 31. No Fake Complexity

The project should not become impressive merely because it contains many technologies.

Prefer:

```text
Real data
+
Correct processing
+
Clear architecture
+
Useful visualization
+
Reliable implementation
```

over:

```text
10 APIs
+
LLM
+
AWS
+
Flutter
+
Docker
+
Redis
+
Kubernetes
+
random AI features
```

The second is not automatically better.

Complexity must serve a real requirement.

---

## 32. Professional Development Progression

Follow this progression:

```text
WORKING
   ↓
CORRECT
   ↓
RELIABLE
   ↓
USEFUL
   ↓
POLISHED
   ↓
ADVANCED
```

Do not reverse this order.

A simple system using real data correctly is more valuable than a flashy interface using fake data.

---

## 33. Decision Log

### DECIDED

- Project direction: disaster preparedness/emergency information system
- Working name: SafeGrid
- Team: 4 people
- Initial client: PWA
- Backend: FastAPI
- Map: MapLibre
- Initial data: USGS + Open-Meteo
- Core output: geographic 🔴🟡🟢 risk visualization
- Development style: incremental vertical slices
- GitHub for version control/project management
- LLM/SMS/Flutter are not MVP requirements

### NOT YET DECIDED

- Exact database
- Exact risk thresholds
- Exact GeoJSON generation method for each hazard
- Final hosting/deployment
- Exact notification mechanism
- Whether/when a Flutter client will be created
- Which additional hazard sources will be added

Do not pretend undecided items are finalized.

When a decision is made, update this section.

---

## 34. Change Management

Major decisions should be recorded.

When changing architecture, document:

```text
Date:
Decision:
Previous approach:
New approach:
Reason:
Trade-offs:
Impact on team:
```

Avoid repeatedly changing technology stacks because a new tool looks interesting.

The project should optimize for **delivery and learning**, not constant reinvention.

---

## 35. Team Communication Principle

The Shared ChatGPT Project is intended to reduce the need for one team member to act as the information bridge between everyone.

Team members should ask project questions directly inside the shared project.

However:

> Important technical decisions must still be recorded in project documentation.

Do not rely on ChatGPT conversation history as the only source of truth.

The actual source of truth should eventually be:

```text
GitHub repository
+
Project documentation
+
Shared Project context
```

---

## 36. Final North Star

SafeGrid should demonstrate that the team can:

> **Take messy real-world disaster data, process it using its own backend logic, convert it into meaningful geographic risk information, and deliver it through a usable application.**

Everything else is secondary.

The project should be ambitious enough to teach real engineering, but disciplined enough to actually finish.


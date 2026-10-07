# SafeGrid 🌍🚨
> **Disaster Preparedness & Emergency Risk Information System**

SafeGrid is an open-source disaster preparedness platform that transforms messy public hazard data into clear, understandable geographic risk zones displayed on an interactive, offline-ready map.

---

## 💡 What is SafeGrid in Simple Words?

When a disaster happens, raw weather reports and earthquake coordinates are confusing for ordinary citizens. 
**SafeGrid solves this by:**
1. Fetching real public disaster data (earthquakes, extreme weather).
2. Processing that data through our own backend risk engine.
3. Classifying danger into simple color zones:
   - 🔴 **High Risk** (immediate threat / epicenters)
   - 🟡 **Moderate Risk** (buffer zones / potential impact)
   - 🟢 **Low Risk** (minimal hazard — *never described as absolute safety*)
4. Displaying these zones on a fast, mobile-friendly map that works even when network connectivity drops.

---

## 🏗️ Architecture & Data Flow

```text
  [ Public APIs ] (USGS Earthquakes, Open-Meteo Weather)
         ↓
  [ FastAPI Backend ] (Ingestion, Validation & Normalization)
         ↓
  [ Risk Engine ] (Severity Scoring & Affected Radius Calculation)
         ↓
  [ GeoJSON REST API ] (/api/hazards, /api/risk-zones)
         ↓
  [ Frontend PWA + MapLibre GL JS ] (Interactive 🔴 🟡 🟢 Map Layers)
         ↓
  [ Database & Offline Cache ] (Service Worker + IndexedDB / Local Cache)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.10+, FastAPI, Pydantic |
| **Frontend** | TypeScript / JavaScript, Progressive Web App (PWA) |
| **Mapping Engine**| MapLibre GL JS |
| **Data Sources** | USGS (Earthquake API), Open-Meteo (Weather API) |
| **Storage & Cache**| Relational / Document DB (TBD), Service Worker, IndexedDB |
| **Version Control**| Git + GitHub (Feature Branch Workflow) |

---

## 👥 Team Roles & Responsibilities

| Role | Focus | Core Responsibilities |
| :--- | :--- | :--- |
| **Person 1** | **Backend & APIs** | FastAPI setup, USGS/Open-Meteo integration, data normalization, REST endpoints. |
| **Person 2** | **Risk Engine & GeoJSON** | Hazard scoring logic, severity thresholds, risk boundary calculation, GeoJSON output generation. |
| **Person 3** | **Frontend & Map UI** | PWA interface, MapLibre GL JS integration, rendering 🔴🟡🟢 layers, hazard markers, dashboard. |
| **Person 4** | **Database & Offline Mode** | Database schema, persistence, Service Worker caching, IndexedDB offline data, handling stale data indicators. |

---

## 🎯 Target Milestone: The First Vertical Slice

Before building complex features or bells and whistles, the team must complete one complete end-to-end working pipeline:

```text
USGS API  ➜  FastAPI Ingestion  ➜  Basic Risk Scoring  ➜  GeoJSON  ➜  MapLibre  ➜  🔴 🟡 🟢 Map
```

If this flow works reliably, the core technical foundation of SafeGrid is proven.

---

## 🚫 Out of Scope for MVP (What We Are NOT Building Yet)

To finish on time, the team has explicitly excluded:
- ❌ AI chatbots & LLM-generated alerts
- ❌ SMS / WhatsApp gateways
- ❌ Native mobile apps (Flutter/React Native) — *PWA web first*
- ❌ Complex volunteer/resource dispatch systems
- ❌ Expensive cloud infrastructure

---

## 🌿 Git & Collaboration Workflow

We follow a strict **branch-per-feature** workflow:

```text
main
 ├── feature/backend-api    (Person 1)
 ├── feature/risk-engine    (Person 2)
 ├── feature/map-ui         (Person 3)
 └── feature/offline        (Person 4)
```

1. **Never commit directly to `main`**.
2. Create a feature branch: `git checkout -b feature/<feature-name>`.
3. Keep commits atomic and clearly described (e.g. `feat: add USGS earthquake parsing`).
4. Open a Pull Request (PR) to `main` and get a team review before merging.

---

## ⚠️ Safety & Honesty Disclaimer

SafeGrid is an academic and community research prototype.
- It is **not** a certified government emergency broadcast or official rescue system.
- It **never** claims guaranteed disaster prediction.
- Stale, cached, or simulated demo data is always explicitly marked as such to the user.

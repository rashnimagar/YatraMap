# YatraMap — Kathmandu Valley Bus Route & Navigation System

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1.1-green.svg)](https://www.djangoproject.com/)
[![Folium](https://img.shields.io/badge/Folium-0.20.0-orange.svg)](https://python-visualization.github.io/folium/)
[![Tests](https://img.shields.io/badge/Tests-46%20Passed-brightgreen.svg)]()

A Django-based public-transit route planning and navigation web application engineered for the Kathmandu Valley (covering Kathmandu, Lalitpur, and Bhaktapur). YatraMap enables passengers to find direct bus routes, compute optimal multi-route transfer journeys using route-aware shortest-path algorithms, inspect interactive geographic maps, browse public transit operators, and discover nearby bus stops.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Routing System](#routing-system)
- [Maps & Cartography](#maps--cartography)
- [Transit Data](#transit-data)
- [Current Dataset](#current-dataset)
- [Installation (Windows PowerShell)](#installation-windows-powershell)
- [Database Management](#database-management)
- [Transit Data Import](#transit-data-import)
- [Distance Calculation](#distance-calculation)
- [Running the Project](#running-the-project)
- [Testing](#testing)
- [Development Workflow](#development-workflow)
- [Git & Database Snapshot Policy](#git--database-snapshot-policy)
- [Troubleshooting](#troubleshooting)
- [Credits & Project Context](#credits--project-context)
- [Verified Project State](#verified-project-state)

---

## Overview

Public transit in the Kathmandu Valley is composed of numerous crisscrossing bus networks operated by cooperatives and private operators. Passengers frequently face challenges identifying which buses connect specific hubs, where to transfer between different routes, and how far their journeys will take them.

**YatraMap** solves this by modeling the valley's public transport network as a directed graph. It provides:
1. Fast direct route discovery when source and destination stops share a bus line.
2. Intelligent multi-leg transfer calculation via Dijkstra's algorithm, factoring in transfer penalties to prefer seamless, minimal-change itineraries over fragmented paths.
3. Interactive geographic visualizations with stop sequences, transfer highlights, and journey legends.
4. An operator and route catalog providing complete stop-by-stop itineraries with cumulative distance metrics.

---

## Features

- **Bus Stop Search & Autocomplete:** Fast client-side stop search across 133 active stations with keyboard navigation and instant selection.
- **Origin & Destination Selection:** Clear input forms with origin/destination swap controls and validation against identical stops.
- **Direct Route Search:** Identifies every bus route serving both origin and destination stops, honoring bidirectional travel rules and sequence direction.
- **Multi-Route Transfer Journeys:** Graph-based pathfinding calculates connected journeys across different routes when no direct bus exists.
- **Best Connected Journey Optimization:** Route-aware Dijkstra search balances total road distance against passenger transfer inconvenience.
- **Transfer Point Indication:** Explicitly identifies interchange stops with dedicated icons and boarding instructions.
- **Accurate Distance Calculations:** Cumulative journey distances derived from consecutive stop coordinates and route sequence distances.
- **Travel Time Estimation:** Heuristic time calculations combining average valley bus speed (18 km/h) with transfer delay allowances.
- **Operator Directory:** Browse active public transit operators (e.g., Sajha Yatayat) and see total active routes operated.
- **Operator Route Directory:** Explore every route managed by an operator, complete with stop counts and terminal destinations.
- **Route Detail Itineraries:** Ordered stop-by-stop lists for each route showing sequence numbers, landmarks, and cumulative step distances.
- **Interactive Search Maps:** Embedded Folium maps showing origin (green), destination (red), intermediate stops (blue), and plotted route paths.
- **Full Route Maps:** Interactive detail maps illustrating complete end-to-end bus lines across Kathmandu Valley.
- **Multi-Color Transfer Maps:** Distinct color palettes per transit segment with amber interchange markers and floating journey legends.
- **Nearby Stops Geolocation API:** JSON endpoint (`/api/nearby-stops/`) computing the 5 nearest stops to user GPS coordinates via the Haversine formula.
- **Responsive Mobile-First UI:** Transit-focused aesthetic styled with custom CSS (`yatra-map.css`), responsive layouts, and accessible typography.
- **Transit CSV Data Import:** Built-in Django management command (`import_transit_data`) for reproducible database seeding.
- **Automated Distance Tool:** Standalone script (`calculate_distances.py`) that computes consecutive stop distances in kilometers.

---

## Technology Stack

- **Backend Framework:** Django 6.1.1 (Python 3.13)
- **Database:** SQLite 3 (`db.sqlite3`)
- **Admin Dashboard:** Django Jazzmin 3.0.5
- **Interactive Mapping:** Folium 0.20.0 (Leaflet.js integration) with Branca 0.8.2
- **Map Tiles:** CARTO Voyager Raster Tiles (`https://{s}.basemaps.cartocdn.com/rastertiles/voyager/...`)
- **Configuration Management:** python-dotenv 1.2.3
- **Frontend / Presentation:** Vanilla HTML5, Vanilla CSS3 (`routes/static/css/yatra-map.css`), Vanilla JavaScript (Fetch API, HTML5 Geolocation, LocalStorage)
- **Standard Library Modules:** `dataclasses`, `heapq`, `itertools`, `math`, `csv`, `decimal`, `pathlib`

---

## Project Structure

```text
YatraMap/
├── config/                             # Django project configuration
│   ├── __init__.py
│   ├── asgi.py                         # ASGI interface entry point
│   ├── settings.py                     # Project settings, installed apps, CARTO config
│   ├── urls.py                         # Root URL routing
│   └── wsgi.py                         # WSGI interface entry point
├── data/                               # Transit CSV dataset and preprocessing tools
│   ├── calculate_distances.py          # Haversine distance calculator for route_stops.csv
│   ├── operators.csv                   # Transit operators master data
│   ├── route_stops.csv                 # Route-stop sequence and distance data
│   ├── routes.csv                      # Bus route definitions
│   └── stops.csv                       # Geocoded bus stops (latitude/longitude)
├── routes/                             # Core transit application
│   ├── management/
│   │   └── commands/
│   │       └── import_transit_data.py  # Management command for CSV ETL import
│   ├── migrations/
│   │   ├── 0001_initial.py             # Database schema migration
│   │   └── __init__.py
│   ├── services/                       # Cohesive domain services
│   │   ├── __init__.py
│   │   ├── network_route_map.py        # NetworkRouteMapBuilder & multi-route Folium maps
│   │   ├── route_map.py                # RouteMapBuilder & direct/full route Folium maps
│   │   ├── route_search.py             # RouteSearchService & direct search logic
│   │   └── transit_router.py           # TransitRouter & Dijkstra graph routing
│   ├── static/
│   │   ├── css/
│   │   │   └── yatra-map.css           # Custom responsive styles and design tokens
│   │   └── js/
│   │       └── yatra-map.js
│   ├── templates/
│   │   └── routes/
│   │       ├── base.html               # Base layout, navigation, and footer
│   │       ├── operator_detail.html    # Operator routes detail view
│   │       ├── operators.html          # Operators listing view
│   │       ├── route_detail.html       # Route itinerary and full map view
│   │       └── route_search.html       # Homepage with search form, results, and maps
│   ├── admin.py                        # Jazzmin/Django admin model registrations
│   ├── apps.py                         # Application configuration
│   ├── models.py                       # Transit models (Operator, BusStop, BusRoute, RouteStop)
│   ├── tests.py                        # 46 comprehensive unit and integration tests
│   ├── urls.py                         # App URL patterns with class-based view bindings
│   └── views.py                        # Django Class-Based Views (CBVs)
├── .env                                # Local environment variables (CARTO_API_KEY)
├── .gitignore                          # Git ignore rules
├── db.sqlite3                          # Seeded SQLite database snapshot (133 stops, 13 routes)
├── manage.py                           # Django CLI administrative utility
└── requirements.txt                    # Python project dependencies
```

---

## Architecture

The YatraMap codebase follows a clean, class-based architecture separating HTTP request handling, domain services, map generation, and data ETL:

### 1. Presentation Layer (Class-Based Views)
- **`RouteSearchView(View)`**: Handles homepage GET requests, coordinates direct route queries, triggers multi-route transfer searches, renders Folium map components, and returns template context.
- **`NearbyStopsView(View)`**: REST-style JSON endpoint validating latitude/longitude queries and returning the nearest 5 stops sorted by distance.
- **`OperatorListView(ListView)`**: Generic ListView querying active operators annotated with active route counts.
- **`OperatorDetailView(DetailView)`**: Generic DetailView presenting an operator's active routes with prefetched stops.
- **`RouteDetailView(DetailView)`**: Generic DetailView assembling ordered stops and embedding the full route Folium map.

### 2. Domain & Routing Services
- **`RouteSearchService`**: Discovers direct routes between two stops, calculates total segment distance, and computes time estimates.
- **`TransitRouter`**: Assembles directed transit graphs from database records, executes route-aware Dijkstra pathfinding, calculates transfer penalties, and groups consecutive edges into `TransitSegment` objects.

### 3. Map Builder Services
- **`RouteMapBuilder`**: Constructs Folium maps for direct route search results (`build_search_map`) and complete route itineraries (`build_full_route_map`), rendering custom HTML `DivIcon` markers.
- **`NetworkRouteMapBuilder`**: Assembles multi-segment transit journey maps (`build_map`) with segment color-coding, amber transfer icons (`T`), and floating HTML legends.

### 4. Data Processing Services
- **`TransitDataImporter`**: Atomic ETL service reading CSV files from `data/` and upserting records into `Operator`, `BusStop`, `BusRoute`, and `RouteStop` models.
- **`RouteDistanceCalculator`**: Standalone service calculating consecutive stop distances in `data/route_stops.csv`.

### 5. Pure Utilities & Backward Compatibility
- **`haversine_distance(...)`**: Intentionally preserved as a stateless mathematical utility function implementing the great-circle distance formula.
- **Backward-Compatible Wrappers**: Top-level function signatures (`find_routes`, `calculate_distance`, `calculate_estimated_minutes`, `build_transit_graph`, `find_shortest_path`, `count_transfers`, `build_segments`, `create_route_map`, `create_full_route_map`, `create_network_route_map`) are maintained as pass-through wrappers to ensure zero disruption to existing callers and tests.

---

## Routing System

The routing engine operates at two distinct levels:

### 1. Direct Route Search (`RouteSearchService`)
1. Fetches all active `RouteStop` entries containing the source stop.
2. Cross-references routes serving the destination stop.
3. For forward routes (`destination_sequence > source_sequence`), extracts the slice of stops between them.
4. For bidirectional routes where destination precedes source, extracts and reverses the stop sequence.
5. Computes actual journey distance and estimated travel duration.

### 2. Multi-Route Network Graph (`TransitRouter`)
When no single direct route connects the chosen stops, YatraMap computes transfer journeys:
- **Graph Nodes:** Active `BusStop` records.
- **Graph Edges:** Consecutive stops on an active route represent directed `TransitEdge` instances with edge distance. Bidirectional routes generate edges in both forward and reverse directions.
- **State Representation:** Dijkstra's search tracks state as `(stop_id, current_route_id)`. Tracking `current_route_id` allows the algorithm to determine when a passenger switches routes.
- **Transfer Penalties:**
  $$\text{Routing Cost} = \text{Actual Distance} + (\text{Transfers} \times \text{Transfer Penalty})$$
  Default transfer penalty is $2.0\text{ km}$, preventing the algorithm from proposing routes with excessive transfers for negligible distance savings.
- **Segment Grouping:** Continuous edges on the same bus line are bundled into `TransitSegment` records, detailing operator, route number, and boarding stops.

---

## Maps & Cartography

YatraMap uses **Folium** to generate interactive Leaflet maps with CARTO Voyager tiles:

- **CARTO Voyager Tiles:** High-contrast, clean cartographic style suitable for public transit visualization.
- **API Key Configuration:** CARTO tiles require an API key to eliminate tile watermarks. Configure this in `.env`:
  ```env
  CARTO_API_KEY=your_carto_api_key_here
  ```
  `config/settings.py` reads `os.environ.get("CARTO_API_KEY", "")` and passes it as `?key=...` when requesting raster tiles.
- **Map Types:**
  - **Selected Search Map:** Renders the active journey with numbered circular markers (Green origin, blue intermediate, red destination) and fitted bounding boxes.
  - **Full Route Map:** Displays the entire route sequence for route detail pages.
  - **Network Transfer Map:** Colors each route leg with a distinct palette (blue, violet, emerald, orange, pink, cyan), highlights interchange points with amber `T` markers, and includes a fixed overlay legend.

---

## Transit Data

Transit data resides in the `data/` directory across four relational CSV files:

### 1. `data/operators.csv`
Defines public transport companies/cooperatives.
- `operator_id`: Unique slug identifier (e.g., `sajha`).
- `name`: Official operator name (e.g., `Sajha Yatayat`).
- `description`: Overview of operator services.

### 2. `data/stops.csv`
Defines geocoded stations and stops.
- `stop_id`: Unique slug identifier (e.g., `lagankhel`).
- `name`: Display name of the stop.
- `latitude`: Decimal latitude (WGS 84, between -90 and 90).
- `longitude`: Decimal longitude (WGS 84, between -180 and 180).
- `location_description`: Optional landmark or locality note.

### 3. `data/routes.csv`
Defines bus lines.
- `route_id`: Unique route slug (e.g., `sajha-01`).
- `operator_id`: Foreign key reference to `operators.csv`.
- `route_number`: Public route badge number (e.g., `1`).
- `name`: Origin - Destination name (e.g., `Lagankhel - Naya Buspark`).
- `is_bidirectional`: Boolean (`true`/`false`) indicating if buses run both ways.

### 4. `data/route_stops.csv`
Defines ordered stop sequences and distances along each route.
- `route_id`: Reference to `routes.csv`.
- `stop_id`: Reference to `stops.csv`.
- `sequence`: 1-based integer sequence order.
- `distance_from_previous`: Kilometers from the immediately preceding stop, formatted to 2 decimal places. Generated automatically by `calculate_distances.py`. The first stop of every route (`sequence = 1`) has an empty string for this field.

---

## Current Dataset

The committed dataset contains verified public bus transit coverage for Kathmandu Valley:

| Entity | Verified Count | Primary Source |
| :--- | :---: | :--- |
| **Operators** | **1** | Sajha Yatayat |
| **Bus Stops** | **133** | Major transit nodes across KTM, Lalitpur, and Bhaktapur |
| **Bus Routes** | **13** | Core valley arterial and ring-road corridors |
| **Route Stops** | **300** | Ordered sequenced stop associations |

> **Note on `db.sqlite3`:** The SQLite database file is intentionally tracked in Git as a pre-seeded, ready-to-run development and demo snapshot.

---

## Installation (Windows PowerShell)

Follow these exact steps in **Windows PowerShell**:

### 1. Clone the Repository
```powershell
git clone https://github.com/rashnimagar/YatraMap.git
cd YatraMap
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` first).*

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
A default `.env` file is included with CARTO credentials. To customize:
```powershell
# Create or edit .env
Set-Content -Path .env -Value "CARTO_API_KEY=your_key_here"
```

### 5. Apply Migrations
```powershell
python manage.py migrate
```

### 6. Verify Installation
```powershell
python manage.py check
python manage.py test
```

### 7. Run the Development Server
```powershell
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000/` in your browser.

---

## Database Management

The repository includes `db.sqlite3` so that all 133 stops and 13 routes are available immediately without manual setup.

### Rebuilding the Database from Scratch
To perform a complete clean rebuild from CSV files:

```powershell
# 1. Remove existing database
Remove-Item .\db.sqlite3 -Force

# 2. Run initial database migrations
python manage.py migrate

# 3. Recalculate route stop distances
python .\data\calculate_distances.py

# 4. Import all transit data
python manage.py import_transit_data
```

---

## Transit Data Import

The `import_transit_data` command parses `data/*.csv` files within an atomic transaction:

```powershell
# Standard import (updates or creates records)
python manage.py import_transit_data

# Clean re-import (clears existing transit models first)
python manage.py import_transit_data --clear
```

Output:
```text
Imported 1 operators.
Imported 133 stops.
Imported 13 routes.
Imported 300 route-stop records.

Transit data imported successfully.
Operators: 1
Stops: 133
Routes: 13
Route stops: 300
```

---

## Distance Calculation

The `data/calculate_distances.py` script reads `data/stops.csv` and `data/route_stops.csv`, computes the great-circle Haversine distance between consecutive stops on every route, and updates `data/route_stops.csv`:

```powershell
python .\data\calculate_distances.py
```

Output:
```text
Updated 300 route-stop records.
```

---

## Running the Project

Launch the local development server:
```powershell
python manage.py runserver
```

Open your browser to:
```text
http://127.0.0.1:8000/
```

### Implemented URL Routes

| URL Pattern | View Class | URL Name | Description |
| :--- | :--- | :--- | :--- |
| `/` | `RouteSearchView` | `route_search` | Homepage, autocomplete, route search, and map |
| `/operators/` | `OperatorListView` | `operators` | List of transit operators with active route counts |
| `/operators/<int:pk>/` | `OperatorDetailView` | `operator_detail` | Operator profile with list of operated routes |
| `/routes/<int:pk>/` | `RouteDetailView` | `route_detail` | Detailed route stop itinerary and full interactive map |
| `/api/nearby-stops/` | `NearbyStopsView` | `nearby_stops` | JSON API returning 5 closest stops to `?lat=...&lng=...` |
| `/admin/` | `AdminSite` | `admin:index` | Jazzmin-styled Django administrative portal |

---

## Testing

The project maintains a 100% passing test suite across models, services, graph routing, class-based views, and API endpoints:

```powershell
# Verify system configuration
python manage.py check

# Verify migration consistency
python manage.py makemigrations --check

# Execute test suite
python manage.py test
```

Current verified output:
```text
System check identified no issues (0 silenced).
No changes detected
Creating test database for alias 'default'...
..............................................
----------------------------------------------------------------------
Ran 46 tests in 0.313s

OK
Destroying test database for alias 'default'...
```

---

## Development Workflow

When updating or adding new bus routes and stops:

1. **Edit Transit CSV Files:** Add or update records in `data/stops.csv`, `data/routes.csv`, or `data/route_stops.csv`.
2. **Recalculate Segment Distances:**
   ```powershell
   python .\data\calculate_distances.py
   ```
3. **Import Data into Database:**
   ```powershell
   python manage.py import_transit_data --clear
   ```
4. **Run System Checks & Migrations Check:**
   ```powershell
   python manage.py check
   python manage.py makemigrations --check
   ```
5. **Run the Test Suite:**
   ```powershell
   python manage.py test
   ```
6. **Start Server & Validate in Browser:**
   ```powershell
   python manage.py runserver
   ```

---

## Git & Database Snapshot Policy

- **Tracked `db.sqlite3`:** SQLite database file is intentionally tracked so developers and evaluators can immediately run the application with zero seeding steps.
- **Commit Best Practice:** When transit data files in `data/` are modified, run `python manage.py import_transit_data --clear` and commit both the CSV files and the updated `db.sqlite3` file together.

---

## Troubleshooting

### 1. `DisallowedHost` or Invalid Host Header
- **Symptom:** `Invalid HTTP_HOST header: '...'. You may need to add '...' to ALLOWED_HOSTS.`
- **Resolution:** In `config/settings.py`, `DEBUG = True` allows `localhost` and `127.0.0.1`. If hosting on an IP or network domain, append the hostname to `ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'your_ip']`.

### 2. Map Tiles Showing Watermark or Failing to Load
- **Symptom:** Leaflet map displays an "API KEY REQUIRED" watermark or tiles fail to render.
- **Resolution:** Confirm that `.env` contains a valid `CARTO_API_KEY`. Sign up at [CARTO Basemaps](https://carto.com/basemaps/) for a free API key.

### 3. Missing Virtual Environment / ModuleNotFoundError
- **Symptom:** `ModuleNotFoundError: No module named 'django'`
- **Resolution:** Activate your virtual environment with `.\venv\Scripts\Activate.ps1` before executing Python or management commands.

### 4. Empty Distances on Route Stops
- **Symptom:** Search results display `0.0 km` or stop sequence distances are missing.
- **Resolution:** Run `python .\data\calculate_distances.py`, followed by `python manage.py import_transit_data --clear`.

### 5. Geolocation / Nearby Stops Returns 400 Bad Request
- **Symptom:** `/api/nearby-stops/` returns status 400.
- **Resolution:** Ensure both `lat` and `lng` query parameters are provided as valid decimal floats (e.g., `/api/nearby-stops/?lat=27.673&lng=85.324`).

---

## Credits & Project Context

- **Project:** YatraMap — Kathmandu Valley Bus Route & Navigation System
- **Focus Area:** Public transit routing, graph pathfinding, and interactive cartography for Kathmandu, Lalitpur, and Bhaktapur.
- **Repository:** [rashnimagar/YatraMap](https://github.com/rashnimagar/YatraMap)

---

## Verified Project State

- **Django System Check:** Passed (0 issues silenced)
- **Migrations Consistency Check:** Passed (no outstanding migrations)
- **Test Suite Status:** **46 / 46 Tests Passing**
- **Operators Count:** 1
- **Bus Stops Count:** 133
- **Bus Routes Count:** 13
- **Route Stops Count:** 300
- **Refactoring Status:** Clean Class-Based Architecture completed
- **Database Snapshot:** `db.sqlite3` verified and included

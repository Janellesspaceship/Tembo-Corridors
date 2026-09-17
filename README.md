# Tembo-Corridors
Data-analytics project mapping human-elephant conflict risk and critical movement-corridor pinch points across Kenya's elephant range, using public GBIF, WDPA, WorldPop, and OpenStreetMap data — built on BigQuery, with a Looker Studio dashboard and Streamlit app.

# Tembo Corridors — Predicting Human-Elephant Conflict Risk & Mapping Critical Movement Corridors in Kenya

> *Tembo (Swahili): elephant.*

## 1. Introduction

Kenya's elephant range increasingly overlaps with farmland, roads, and settlements. Elephants raiding crops near reserve edges is one of the most consistent and costly forms of human-wildlife conflict in the country — it damages livelihoods, occasionally causes injury or death, and drives retaliatory killing of elephants. At the same time, the historic migration corridors elephants rely on to move between protected areas (e.g., Amboseli–Tsavo–Laikipia) are being fragmented by fencing, roads, and expanding settlements.

These two problems — where conflict happens, and where corridors are breaking — are usually studied separately. This project ties them together: **it identifies where human-elephant conflict is most likely, and which specific movement corridors are most critical and most at risk of being severed**, so that limited mitigation budget (fencing, early-warning systems, corridor easements) can go to the highest-impact locations first.

**Note on approach:** this is a data *analytics* project, not a machine-learning project. No model is trained. Every number in the final ranking — conflict-risk score, corridor criticality, composite priority score — is a transparent, documented calculation (descriptive statistics, spatial joins, and a hand-weighted rubric) that a non-technical planner can audit line by line.

## 2. Problem Statement

- **Diagnosis difficulty:** Conflict incidents and corridor fragmentation are both driven by the same underlying spatial pressure (human expansion into elephant range), but are rarely modeled together, so mitigation decisions are made reactively, one incident at a time.
- **Current practice:** Fencing and mitigation resources are often allocated based on where the last incident happened, not where the next one is most likely, and rarely account for corridor connectivity at all.
- **Consequence:** Communities absorb crop losses and safety risk; KWS pays recurring compensation claims; corridors quietly close off without anyone tracking the cumulative effect until elephant populations become isolated.
- **Goal:** Build a transparent risk + corridor-criticality score, at the level of specific zones and specific corridor segments, that mitigation planners can act on directly.
- **Impact:** Better-targeted fencing/early-warning deployment, stronger case for corridor protection easements, and a quantified estimate of compensation/crop-loss cost avoided by acting on the top-ranked locations.

## 3. Research Questions

1. Where are elephant populations currently concentrated in Kenya, based on observation data?
2. Where does human settlement/agriculture overlap most with that elephant range, and is this overlap increasing?
3. Which spatial/environmental factors are most strongly associated with conflict-risk zones — proximity to protected-area edges, water sources, cropland, roads (measured via correlation and cross-tabulation, not prediction)?
4. Representing elephant range as a connectivity network (habitat patches as nodes, viable movement paths as edges), where are the critical corridors, and which are most fragmented or at risk of being severed by roads/settlements (measured via standard graph-theory metrics like betweenness centrality — a deterministic calculation, not a trained model)?
5. Combining conflict risk and corridor criticality into one score, which specific zones/corridor segments should be prioritized for mitigation first?
6. What is the estimated economic/safety benefit (crop loss avoided, compensation payouts avoided) of protecting the top-ranked zones/corridors?

## 4. Objectives

- Quantify where human-elephant conflict risk is highest across Kenya's elephant range.
- Model elephant habitat connectivity as a network and identify critical, at-risk movement corridors.
- Combine both into a single, explainable priority score for mitigation planning.
- Deliver the analysis through a BigQuery-backed pipeline, a planner-facing dashboard, and an interactive web app for exploring specific zones and corridors.

## 5. Architecture

```
 ┌─────────────────────┐     ┌───────────────────────┐     ┌─────────────────────┐
 │   Raw Data Sources    │ →  │   BigQuery (staging,    │ →  │  Python / GeoPandas /  │
 │ (elephant sightings,   │     │   spatial joins,        │     │  NetworkX (risk model  │
 │  WorldPop, OSM roads,  │     │   ST_DWITHIN, etc.)      │     │  + corridor graph)      │
 │  protected areas)       │     │                         │     │                         │
 └─────────────────────┘     └───────────────────────┘     └─────────────────────┘
                                                                         │
                        ┌─────────────────────────────────────────────────┼───────────────────────────┐
                        ▼                                                 ▼                            ▼
              ┌────────────────────┐                          ┌────────────────────┐       ┌────────────────────┐
              │  BigQuery: scored    │                          │  Looker Studio /      │       │  Streamlit web app    │
              │  risk + corridor      │                          │  Plotly dashboard      │       │  (explore any zone/    │
              │  table                │                          │                        │       │  corridor's score)     │
              └────────────────────┘                          └────────────────────┘       └────────────────────┘
```

## 6. Data Sources

*(All sources below are public and independent of any prior/inaccessible project. Two sources listed here were the original plan but were replaced during the build — noted explicitly, not silently swapped. See Current Status and ETL Workflow for what was actually used.)*

| Source | What it provides | Format / access | Status |
|---|---|---|---|
| **GBIF** (Global Biodiversity Information Facility) | Elephant (*Loxodonta africana*) occurrence records for Kenya, pooled from 50+ contributing datasets including a KWS Laikipia-Samburu aerial census and iNaturalist observations | Darwin Core Archive / CSV via gbif.org query or API, filtered to `country=Kenya`, `has coordinate=true` | ✅ Used — 4,265 records |
| ~~WDPA~~ (World Database on Protected Areas) | Was the original plan for protected-area boundaries | Shapefile/geodatabase from protectedplanet.net | ❌ Replaced — the global shapefile export was unreliable to extract/access under the project timeline |
| **OpenStreetMap / Nominatim** (via OSMnx `geocode_to_gdf`) | Protected-area boundaries by name, geocoded individually | Live API, polygon per named reserve | ✅ Used instead of WDPA — 13/13 target reserves |
| ~~WorldPop~~ | Was the original plan for population-density human-pressure proxy | GeoTIFF, worldpop.org | ❌ Dropped from scope — replaced by settlement/road proximity instead |
| ~~OpenStreetMap Overpass API~~ (live roads/settlements/cropland pull) | Was the original plan for roads, settlements, cropland | GeoJSON via Overpass | ❌ Replaced — live queries consistently timed out (network-level, confirmed across a default and an alternate mirror) |
| **Manually compiled reference data** | 15 major towns and 4 major highway routes relevant to the corridor landscape | Hand-curated CSV/coordinates in `src/etl/build_manual_infrastructure_fallback.py` | ✅ Used instead — a stated, documented limitation, not a hidden shortcut |
| African Elephant Database / KWS range reports (secondary, for validation) | Known elephant range and corridor maps, used to sanity-check identified corridors | PDF/report — manual reference, not a pipeline input | Used informally — top risk zones (Kimana, Isiolo, Archer's Post, Voi) are consistent with known reporting |

## 7. ETL Workflow

1. **Extract**
   - Query GBIF for *Loxodonta africana* occurrences in Kenya (`has coordinate = true`) and download via the REST API (`src/etl/pull_gbif_elephants.py`).
   - Geocode 13 named protected areas via OSMnx/Nominatim (`src/etl/pull_protected_areas_osm.py`).
   - Build a manually compiled settlements + roads reference for the corridor landscape (`src/etl/build_manual_infrastructure_fallback.py`) — a live Overpass-based version (`src/etl/pull_osm_infrastructure.py`) exists and can replace this if network access improves.
2. **Load to BigQuery** — create a new BigQuery project/dataset (free tier) and load each source as a staging table: `elephant_occurrences`, `protected_areas`, `population_grid`, `roads`, `settlements`, `cropland`.
3. **Transform**
   - Build a grid (hex or square cells) over Kenya's elephant range extent.
   - Per cell, compute: elephant sighting density, distance to protected-area boundary, distance to nearest road, distance to nearest settlement, population density, cropland proximity.
   - Construct a connectivity graph: nodes = habitat patches/grid cells within elephant range; edges = movement feasibility between adjacent cells, weighted by a "crossing cost" (higher cost where roads/settlements/farmland intervene).
3. **Score** *(all hand-weighted and documented — no training, no fitted model)*
   - Conflict-risk score per cell = weighted sum of elephant presence + human-pressure proximity + cropland proximity, weights chosen and justified up front (e.g. via reference to literature/expert reasoning), not fitted to data.
   - Corridor criticality = standard graph-theory metrics (betweenness centrality, least-cost path analysis) identifying pinch points — cells that, if lost, would disconnect elephant ranges. These are deterministic calculations on the network, not a learned model.
   - Composite priority score = risk × corridor criticality, min-max normalized and ranked.
4. **Load** — Write the scored, ranked table back to BigQuery.
5. **Serve** — Dashboard reads directly from BigQuery; Streamlit app queries BigQuery on demand for the selected zone/corridor.

## 8. Features

- Elephant range & sighting density map.
- Human-elephant conflict-risk heatmap.
- Corridor network map with critical pinch points highlighted.
- Ranked, filterable table of priority zones/corridor segments with factor-level score breakdown.
- "What-if" tool in the app — simulate a new road/settlement and see the effect on corridor connectivity.
- Estimated cost-avoided summary (crop loss / compensation payouts) for top-ranked locations.

## 9. Tech Stack

- **Data warehouse:** Google BigQuery (including BigQuery GIS functions)
- **Processing:** Python, Pandas, GeoPandas, NumPy
- **Network/corridor analysis:** simplified pairwise gap-distance analysis between protected areas (a scoped-down stand-in for full betweenness-centrality/graph analysis, given the project timeline — see Future Improvements)
- **Data acquisition:** GBIF REST API (elephant occurrences), OSMnx/Nominatim (protected-area boundaries by name), manually compiled fallback data for roads/settlements (see Data Sources note below)
- **Scoring:** plain Python/Pandas for min-max normalization and the documented weighted-sum score (no scikit-learn model fitting)
- **Warehouse:** Google BigQuery (elephant occurrences and scored conflict-risk grid loaded as tables)
- **Mapping:** Plotly
- **Dashboard:** Looker Studio (connected live to BigQuery) — *pending, see Current Status*
- **Web app:** Streamlit (also serves as the project's dashboard view — metrics, map, ranked table — while the separate Looker Studio dashboard is being finished)
- **Version control:** Git/GitHub

## 10. Project Structure

```
tembo-corridors/
├── data/
│   ├── raw/                # GBIF elephant occurrences
│   └── processed/          # cleaned protected areas, settlements, roads, scored grid, corridor gaps
├── src/
│   ├── etl/                # GBIF pull, protected-area pull, OSM infrastructure pull, BigQuery load
│   ├── scoring/             # grid building, conflict-risk scoring, corridor gap analysis
│   └── utils/
├── app/
│   └── streamlit_app.py    # interactive web app + dashboard view
├── dashboard/
│   └── looker_studio_link.md
├── notebooks/               # exploratory analysis, article figures
├── README.md
└── requirements.txt
```

## 11. Current Status

- [x] GBIF elephant occurrence data pulled and coverage checked — 4,265 records, concentrated in Narok, Kajiado, Taita Taveta, Laikipia, Isiolo, and Samburu (the corridor landscape, as expected). Note: ~80% of records come from iNaturalist citizen-science observations, so this reflects observation effort/presence more than true density — documented as a limitation.
- [x] Protected-area boundaries sourced — **switched from WDPA to OSM/Nominatim** after the WDPA global shapefile export proved unreliable to extract under the project timeline (see Data Sources note below). 13 of 13 target reserves successfully geocoded (Maasai Mara, Amboseli, Tsavo East/West, Chyulu Hills, Ol Pejeta, Lewa, Borana, Solio, Samburu, Buffalo Springs, Shaba, Meru).
- [x] New BigQuery project/dataset created; `elephant_occurrences` and `conflict_risk_grid` tables loaded.
- [x] Roads/settlements sourced — **live Overpass API pulls consistently failed** (network-level timeout to overpass-api.de from the development machine, confirmed across multiple attempts and an alternate mirror). Replaced with a manually compiled, stated-limitation fallback: 15 major towns and 4 major highway routes relevant to the corridor landscape. WorldPop population raster was dropped from scope entirely in favor of this settlement/road proximity approach.
- [x] Grid built (1,209 cells, ~11km resolution) and per-cell features computed (elephant density, distance to settlement, distance to road, inside-protected-area flag).
- [x] Conflict-risk score computed: transparent weighted formula (40% elephant presence, 30% settlement proximity, 30% road proximity). 188 cells flagged as priority zones (high risk, currently unprotected). Top results cluster around Kimana, Isiolo, Archer's Post, and Voi — independently consistent with known Kenyan human-elephant conflict reporting.
- [x] Corridor analysis — **simplified from full betweenness-centrality graph analysis to pairwise gap-distance analysis** between the 13 protected areas, given the project timeline. This is a stated scope reduction, not a hidden shortcut (see Future Improvements).
- [x] Streamlit app built — combines the dashboard view (summary metrics, risk map) and the interactive explorer (filters, single-cell breakdown) in one deliverable.
- [ ] Looker Studio dashboard connected to BigQuery — pending.
- [ ] Technical article written.

## 12. Future Improvements

- Incorporate real KWS/county-level HEC incident or compensation-claim data, if accessible, to validate the descriptive risk indicators against actual outcomes rather than proxies alone.
- Replace the manually compiled roads/settlements fallback with a live OSM pull once network access to Overpass is available (the code for this already exists in `src/etl/pull_osm_infrastructure.py` — it simply couldn't complete under this project's network conditions).
- Replace the simplified pairwise corridor-gap analysis with a full graph-theory network (betweenness centrality across a denser habitat-patch grid, not just named reserves) for genuine pinch-point identification.
- *(Out of current scope, flagged as a possible next phase, not part of this capstone):* explore a trained Graph Neural Network to enable "what happens if we add this road" simulations — this would move the project from analytics into machine learning.
- Extend the same descriptive framework to other conflict-prone species (lion, buffalo) as additional layers.
- Fold this in as one module of a broader Kenya conservation-priority platform (the earlier "Hifadhi Index" concept), once this species-specific analysis is proven.

## 13. Recommendations

- Keep the risk and corridor-gap results separately visible (not just a combined number) — a planner needs to know *why* a location ranked high.
- Validate at least a handful of top-ranked conflict zones against known reporting (news, KWS/Trust reports) before presenting results as fact — the Kimana/Isiolo/Archer's Post/Voi clustering already does this informally and holds up.
- Frame this explicitly as a decision-support and prioritization tool, not a guarantee of where conflict will occur.
- Treat the manually compiled roads/settlements data and the simplified corridor-gap analysis as documented, load-bearing limitations of this version — not omissions to gloss over in the write-up.
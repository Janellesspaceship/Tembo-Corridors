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

*(All sources below are public and independent of any prior/inaccessible project — the pipeline is fully reproducible from scratch.)*

| Source | What it provides | Format / access |
|---|---|---|
| **GBIF** (Global Biodiversity Information Facility) | Elephant (*Loxodonta africana*) occurrence records for Kenya, pooled from 50+ contributing datasets including a KWS Laikipia-Samburu aerial census and iNaturalist observations | Darwin Core Archive / CSV via gbif.org query or API, filtered to `country=Kenya`, `has coordinate=true` |
| **WDPA** (World Database on Protected Areas / Protected Planet, UNEP-WCMC & IUCN) | Kenya's protected-area boundaries, IUCN category, designation, size, year established | Shapefile/geodatabase from protectedplanet.net (also available as a ready Earth Engine asset: `WCMC/WDPA/current/polygons`), filtered to Kenya |
| **WorldPop** | Population density raster (~1km resolution) — human-pressure proxy | GeoTIFF, worldpop.org, Kenya extract |
| **OpenStreetMap** (via Overpass API / OSMnx) | Roads, settlements, cropland/land-use tags | GeoJSON, Kenya extract |
| African Elephant Database / KWS range reports (secondary, for validation) | Known elephant range and corridor maps, used to sanity-check identified corridors | PDF/report — manual reference, not a pipeline input |
| News/incident reports (optional, stretch) | Spot-validation of conflict hotspots | Manual/scraped |

## 7. ETL Workflow

1. **Extract**
   - Query GBIF for *Loxodonta africana* occurrences in Kenya (`has coordinate = true`) and download as CSV/Darwin Core Archive.
   - Download WDPA protected-area polygons for Kenya from Protected Planet (or pull the `WCMC/WDPA/current/polygons` Earth Engine asset).
   - Download WorldPop population raster for Kenya.
   - Pull OSM roads/settlements/cropland for Kenya via Overpass/OSMnx.
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
- **Network/corridor analysis:** NetworkX (betweenness centrality, least-cost paths) — descriptive graph metrics, no training involved
- **Road/settlement data:** OSMnx
- **Scoring:** plain Python/Pandas for min-max normalization and the documented weighted-sum score (no scikit-learn model fitting)
- **Mapping:** Plotly, Folium
- **Dashboard:** Looker Studio (connected live to BigQuery)
- **Web app:** Streamlit
- **Version control:** Git/GitHub

## 10. Project Structure

```
tembo-corridors/
├── data/
│   ├── raw/                # WorldPop, OSM extracts
│   └── processed/          # cleaned, joined feature/grid tables
├── sql/
│   ├── staging/            # BigQuery staging table DDL
│   └── scoring/            # spatial join + scoring queries
├── src/
│   ├── etl/                # extraction + transformation scripts
│   ├── network/            # corridor graph construction + centrality analysis
│   ├── scoring/            # composite risk/priority score logic
│   └── utils/
├── app/
│   └── streamlit_app.py    # interactive web app
├── dashboard/
│   └── looker_studio_link.md
├── notebooks/               # exploratory analysis, article figures
├── README.md
└── requirements.txt
```

## 11. Current Status

- [ ] GBIF elephant occurrence data pulled and coverage checked (record count, counties/regions represented).
- [ ] WDPA protected-area boundaries for Kenya downloaded and validated for spatial joins.
- [ ] New BigQuery project/dataset created; staging tables loaded.
- [ ] WorldPop + OSM ingestion pipeline built.
- [ ] Grid built and per-cell features computed.
- [ ] Conflict-risk score computed and mapped.
- [ ] Corridor graph built; centrality/pinch-point analysis run.
- [ ] Composite priority score finalized, weights documented.
- [ ] Dashboard built.
- [ ] Streamlit app built.
- [ ] Technical article written.

## 12. Future Improvements

- Incorporate real KWS/county-level HEC incident or compensation-claim data, if accessible, to validate the descriptive risk indicators against actual outcomes rather than proxies alone.
- *(Out of current scope, flagged as a possible next phase, not part of this capstone):* explore a trained Graph Neural Network to enable "what happens if we add this road" simulations — this would move the project from analytics into machine learning.
- Extend the same descriptive framework to other conflict-prone species (lion, buffalo) as additional layers.
- Fold this in as one module of a broader Kenya conservation-priority platform (the earlier "Hifadhi Index" concept), once this species-specific analysis is proven.

## 13. Recommendations

- Keep the risk and corridor scores separately visible (not just the combined number) — a planner needs to know *why* a location ranked high.
- Validate at least a handful of top-ranked conflict zones and corridors against known reporting (news, KWS/Trust reports) before presenting results as fact.
- Frame this explicitly as a decision-support and prioritization tool, not a guarantee of where conflict will occur.
# Offline Data Pipeline (R1)

Builds the prepared city graph from open data (OSM, DEM, rainfall, census)
and loads it into PostGIS. Runs once/periodically - NOT on the request path.

Entry: `build_graph.py`

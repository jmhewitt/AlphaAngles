# AlphaAngles

Analyze a terrain [DEM](https://en.wikipedia.org/wiki/Digital_elevation_model) file using [alpha angles](https://www.avalanche-center.org/Education/glossary/alpha-angle.php) to estimate potential avalanche runout paths associated with a collection of trigger points.

Trigger points should mark the highest point of a potential avalanche path.

Outdoor mapping tools, such as [caltopo](https://caltopo.com) and [gaiagps](https://www.gaiagps.com), can be used to define trigger points and download them as a [GeoJSON](https://en.wikipedia.org/wiki/GeoJSON) file.  Within such tools, a "Marker" object can define individual trigger points.  Alternatively, the waypoints along a "line", "route", or "track" can define  a collection of trigger points.

Potential runout paths are saved as polygons in a GeoJSON file that can be imported into outdoor mapping tools to assist in route planning.

# Example

Sample usage from a (unix) command line prompt:
```
./alphas.py -o runouts.geojson -d USGS_DEM_FILE.tif -t export.json
```

A complete list of options can be found by running:
```
./alphas.py --help
```

# System Requirements

- Python with packages [rasterio](https://rasterio.readthedocs.io/en/stable/#), [pyproj](https://pypi.org/project/pyproj/), [geojson](https://pypi.org/project/geojson/), and [numpy](https://numpy.org)
- [GDAL](https://gdal.org) with Python support enabled, to get the command line tools [gdal_polygonize.py-3.11](https://gdal.org/programs/gdal_polygonize.html) and [ogr2ogr](https://gdal.org/programs/ogr2ogr.html)
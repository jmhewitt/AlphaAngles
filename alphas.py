#!/usr/bin/env python3

#
# process command line arguments
#

import argparse

argParser = argparse.ArgumentParser(
    description="""
    Analyze a terrain DEM file using alpha angles to estimate potential 
    avalanche runout paths associated with a collection of trigger points.

    Trigger points should mark the highest point of a potential avalanche path.

    Outdoor mapping tools, such as caltopo.com and gaiagps.com, can be used to 
    define trigger points and download them as a GeoJSON file.  Within such 
    tools, a "Marker" object can define individual trigger points.  
    Alternatively, the waypoints along a "line", "route", or "track" can define 
    a collection of trigger points.

    Potential runout paths are saved as polygons in a GeoJSON file that can be 
    imported into outdoor mapping tools to assist in route planning.

    Sample usage: 
      ./alphas.py -o runouts.geojson -d USGS_DEM_FILE.tif -t export.json

    System requirements:
      - GDAL with command line tools gdal_polygonize.py-3.11 and ogr2ogr
      - Python packages rasterio, pyproj, geojson, and numpy
    """,
    formatter_class=argparse.RawTextHelpFormatter
)

argParser.add_argument(
    "-d", "--dem", help="DEM file", 
    required=True
)

argParser.add_argument(
    "-t", "--triggers", 
    help="GeoJSON file with lon/lat coordinates for trigger points",
    required=True
)

argParser.add_argument("-a", "--alpha", help="Alpha (runout) angle", default=19)

argParser.add_argument(
    "-o", "--output", help="Name of output file (GeoJSON format)", 
    default='output.geojson'
)

# evaluate and extract arguments
args = argParser.parse_args()
runout_angle = int(args.alpha)
dem_file = args.dem
trigger_file = args.triggers
ofile = args.output

#
# packages
#

# GIS
import rasterio
from pyproj import Proj, Transformer
import geojson
# math
import numpy as np
# system, etc.
import tempfile
import os
import shutil
import sys

#
# check for existence of post-processing tools
# 

# define post-processing tools
gdal_polygonize = "gdal_polygonize.py-3.11"
ogr2ogr = "ogr2ogr"

if shutil.which(gdal_polygonize) is None:
    raise Exception("Could not find shell tool " + gdal_polygonize)

if shutil.which(ogr2ogr) is None:
    raise Exception("Could not find shell tool " + ogr2ogr)

#
# load data
#

# Open the terrain DEM
dem = rasterio.open(dem_file)

# extract list of coordinates from geojson
triggers_raw = [
    # wrap individual points in a list
    [feature['geometry']['coordinates']] if 
    feature['geometry']['type'] == 'Point' else 
    # return lists of points (i.e., such as line segments) as-is
    feature['geometry']['coordinates']
    # load trigger points from input geojson file
    for feature in geojson.load(open(trigger_file))["features"]
]

# convert to a simple list of coordinates
triggers = [item for sublist in triggers_raw for item in sublist]

# assume that trigger points are latlon format
trigger_proj = 4326

#
# prepare common values
#

# convert runout threshold to numerically efficient threshold (tan^2)
runout_thresh = np.power(np.tan(runout_angle / 180 * np.pi), 2)

# extract terrain data
dem_values = dem.read(1)

# mesh grid of coordinates
height = dem.height
width = dem.width
cols, rows = np.meshgrid(np.arange(width), np.arange(height))
xs, ys = rasterio.transform.xy(dem.transform, rows, cols)
eastings = np.array(xs)
northings = np.array(ys)

#
# process triggers
#

# initialize output in raster format
runout_terrain = np.full(dem.shape, False, dtype = bool)

# define coordinate projections
transformer = Transformer.from_crs(trigger_proj, dem.crs)

# for progress messages
iter = 1
n = len(triggers)

# process all trigger points
for trigger in triggers:

    # progress message
    print("Trigger " + str(iter) + " of " + str(n))
    iter += 1
    
    # project the trigger point into the terrain's coordinate system
    loc = trigger
    trigger_x, trigger_y = transformer.transform(loc[1], loc[0])

    # get elevation at trigger location
    trigger_elevation = [val[0] for val in dem.sample([(trigger_x,trigger_y)])]

    # raster of distances from trigger point
    dx = eastings - trigger_x
    dy = northings - trigger_y
    dists = dx * dx + dy * dy

    # raster of elevation changes relative to trigger
    dz = trigger_elevation - dem_values

    # ignore uphill locations
    dz[dz<0] = 0

    # identify large angles between trigger point and all points in dem
    dz = dz * dz
    runout_terrain = runout_terrain | (dz / dists > runout_thresh)

#
# save runout raster
#

# specify raster output dimensions, etc.
profile = dem.profile
profile['nodata'] = 0
profile.update(
    dtype = rasterio.ubyte,
    count = 1,
    compress =  
    'lzw'
)

# post-process raster in temporary folder
with tempfile.TemporaryDirectory() as tmpdir:

    # write runout raster to disk
    f = os.path.join(tmpdir, 'runout.tif')
    with rasterio.open(f, 'w', **profile) as dst:
        dst.write(runout_terrain.astype(rasterio.ubyte), 1)
        dst.close()

    # vectorize raster
    fshape = os.path.join(tmpdir, "runout_proj.geojson")
    os.system(gdal_polygonize + " " + f + " " + fshape)

    # reproject to lonlat
    fout = os.path.join(tmpdir, "runout.geojson")
    os.system(ogr2ogr + " -t_srs EPSG:4326 " + fout + " " + fshape)

    # copy to working directory
    shutil.move(fout, ofile)

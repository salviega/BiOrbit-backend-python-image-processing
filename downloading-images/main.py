# Standard library imports
import glob
import json
import os

# Third-party library imports
from decouple import config
import geopandas as gpd
import fiona
import folium
import numpy as np
import rasterio
import rasterio.mask
import pyproj
from pyproj import Proj
from pyproj import CRS
from shapely.ops import transform
from shapely.geometry import mapping, shape
from send2trash import send2trash

# External library imports
from osgeo import gdal

# Project-specific library imports
from satelliteAPI import LandsatAPI


def replace_spaces_with_underscore(string):
    """
    Replaces spaces in a string with underscores and makes all letters lowercase.
    """
    return string.replace(' ', '_').lower()

def create_folder(name, output_path):
    try:
        # If an output path is specified, add it to the folder name
        if output_path:
            name = os.path.join(output_path, name)

        # Create a new folder with the specified name
        os.makedirs(name)

        # Print a message to confirm that the folder was created
        print(f"Created new folder '{name}'")

        return name
    except:
        return os.path.join(output_path, name)


def create_shapefile(file, protected_area_name, output_path):
    # Load the GeoJSON file using GeoPandas
    gdf = gpd.read_file(file)

    # Reproject the GeoDataFrame to EPSG:32618
    gdf = gdf.to_crs(CRS('EPSG:32618'))

    # Calculate the area in hectares
    area = gdf.geometry.area.sum() / 10000
    print(f"Total area of shape: {area} hectares")

    # Save the GeoDataFrame to a shapefile
    new_output_path = os.path.join(output_path, protected_area_name + '.shp')
    gdf.to_file(new_output_path)

    return new_output_path


def get_footprint(path_to_geojson):
    """
    Get the footprint of a location given a GeoJSON file path.
    """
    # Create a new folium map centered on the location defined by the GeoJSON file
    boundary = gpd.read_file(path_to_geojson)
    center = list(boundary.centroid.iloc[0].coords)[0][::-1]
    m = folium.Map(center, zoom_start=11)

    # Load the GeoJSON file containing the boundary and add it to the map
    folium.GeoJson(boundary).add_to(m)

    # Get the footprint by extracting the coordinates from the GeoJSON data
    with open(path_to_geojson) as f:
        geojson_data = json.load(f)

    coords = []
    if 'features' in geojson_data:
        features = geojson_data['features']
        if len(features) > 0 and 'geometry' in features[0]:
            coords = features[0]['geometry']['coordinates'][0]

    # Return the coordinates as an array
    return coords


# site's coord (EPSG:4326)
protected_area_name = replace_spaces_with_underscore(config('PROTECTED_AREA'))
latitude = config('LATITUDE')
longitude = config('LONGITUDE')
geojson_path = config('GEOJSON_PATH')  # https://geojson.io/

# USGS website
username = config('USERNAME')
password = config('PASSWORD')

# chromedriver path
chromedriver_path = config('CHROMEDRIVER_PATH')

# download directory
downloads_dir = config('DOWNLOADS_DIR')

# landsat directory
landsat_dir = config('LANDSAT_DIR')

# folders name
bands_folder = config('BANDS_FOLDER')
ndvi_folder = config('NDVI_FOLDER')


protected_area_dir = create_folder(protected_area_name, landsat_dir)
protected_area_shape_dir = create_shapefile(geojson_path, protected_area_name, protected_area_dir)
footprint = get_footprint(geojson_path)

api = LandsatAPI(username, password, chromedriver_path, downloads_dir, protected_area_dir)
api.query(footprint, 60)



# Standard library imports
from datetime import date
import json
import os

# Third-party library imports
from decouple import config
import geopandas as gpd
from flask import Flask, jsonify, request
import folium
import shapefile
from pyproj import Proj, transform
from shapely.geometry import Polygon
from pyproj import Transformer

# External library imports

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


def create_shapefile(coordinates, protected_area_name, output_path):

    # Flatten the nested list to match the expected format
    coordinates = [tuple(coord) for coord in coordinates[0]]

    # Define the input and output CRS (Coordinate Reference Systems)
    in_crs = 'EPSG:4326'
    out_crs = 'EPSG:32618'

    # Create a Transformer object to convert coordinates between CRS
    transformer = Transformer.from_crs(in_crs, out_crs)

    # Transform the coordinates from input CRS to output CRS
    coords = [transformer.transform(lon, lat) for lon, lat in coordinates]

    # Create a Shapely Polygon object from the transformed coordinates
    poly = Polygon(coords)

    # Calculate the area in hectares
    area = poly.area / 10000
    print(f"Total area of shape: {area} hectares")

    # Create a GeoDataFrame with the polygon geometry
    gdf = gpd.GeoDataFrame({'name': [protected_area_name], 'geometry': [poly]}, crs=out_crs)

    # Save the GeoDataFrame as a shapefile
    new_output_path = os.path.join(output_path, protected_area_name + '.shp')
    gdf.to_file(new_output_path)

    print("Shapefile created successfully!")
    return new_output_path, area


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


def save_geojson_to_folder(geojson_str, folder_path, filename):
    """
    Saves a GeoJSON string to a file in the specified folder with the specified filename.

    Args:
    geojson_str (str): A string representing the GeoJSON data.
    folder_path (str): The path to the folder where the file will be saved.
    filename (str): The name of the file to be saved.

    Returns:
    None
    """
    if not os.path.exists(folder_path):
        name = os.path.join(folder_path, filename + '_map.geojson')
        os.makedirs(name)

    file_path = os.path.join(folder_path, filename)

    with open(file_path, 'w') as f:
        f.write(geojson_str)

    print(f'Saved GeoJSON to {file_path}')

    return file_path


def custom_encoder(obj):
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    else:
        return None


app = Flask(__name__)


@app.route('/processing', methods=['POST'])
def handle_post_request():
    # retrieve data from the request body
    data = request.get_json()

    # process the data
    result = process_data(data)

    print(data)
    protected_area_id = data['data']['idInteger']
    protected_area_name = data['data']['name']
    protected_area_photo = data['data']['photo']
    protected_area_description = data['data']['description']
    protected_area_geojson = data['data']['geoJson']
    footprint = json.loads(protected_area_geojson)
    protected_area_country = data['data']['country']


    # site's coord (EPSG:4326)
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

    # Open shapes file
    pnnsfl_panel_path = config('PROTECTED_AREA_PANEL_PATH')
    pnnsfl_shape_path = config('PROTECTED_AREA_SHAPE_PATH')

    # folders name
    bands_folder = config('BANDS_FOLDER')
    ndvi_folder = config('NDVI_FOLDER')
    deforestation_folder = config('DEFORESTATION_FOLDER')

    protected_area_dir = create_folder(protected_area_name, landsat_dir)
    protected_area_deforestation_dir = create_folder(deforestation_folder, protected_area_dir)
    protected_area_shape_dir, protected_area_total_extension = create_shapefile(footprint, protected_area_name,
                                                                                protected_area_dir)

    # geojson_path = save_geojson_to_folder(geojson_path, protected_area_dir, protected_area_name)
    #footprint = get_footprint(geojson_path)

    api = LandsatAPI(username, password, chromedriver_path, downloads_dir, protected_area_dir,
                     protected_area_deforestation_dir)
    api.query(chromedriver_path, downloads_dir, footprint, 10)
    '''forest_cover = api.processing(protected_area_name, protected_area_total_extension, protected_area_dir,
                                  footprint, protected_area_shape_dir, bands_folder, ndvi_folder, deforestation_folder)

    forest_cover.protected_area_name = config('PROTECTED_AREA')
    forest_cover.photo = 'photo'
    forest_cover.description = 'description'
    forest_cover.footprint = footprint

    # Custom encoder function for date objects

    # Create a dictionary with the attributes and their values
    forest_cover_dict = {
        "protected_area_name": forest_cover.protected_area_name,
        "photo": forest_cover.photo,
        "description": forest_cover.description,
        "footprint": forest_cover.footprint,
        "last_detection_date": forest_cover.last_detection_date,
        "total_extension_protected_area": forest_cover.total_extension_protected_area,
        "detection_date_list": forest_cover.detection_date_list,
        "total_extension_forest_cover_list": forest_cover.total_extension_forest_cover_list
    }

    # Convert dictionary to a JSON string using the custom encoder
    forest_cover_json = json.dumps(forest_cover_dict, default=custom_encoder)

    # Print the JSON string
    print(forest_cover_json)'''

    # return the result as JSON
    return jsonify(result)


def process_data(data):
    # implement your processing logic here
    return {'message': 'Data processed successfully.'}


if __name__ == '__main__':
    app.run(debug=True)

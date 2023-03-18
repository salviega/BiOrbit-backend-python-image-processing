# Standard library imports
import glob
import os

# Third-party library imports
import geopandas as gpd
import fiona
import folium
import numpy as np
import rasterio
import rasterio.mask
import pyproj
from pyproj import Proj
from shapely.ops import transform
from shapely.geometry import mapping, shape
from send2trash import send2trash

# External library imports
from osgeo import gdal

# Project-specific library imports
import AtmosphericCorrection as ac
from NDVI import ndvi, forest_not_forest, forest_ndvi

def get_folder(protected_area_dir, bands_folder):
    # Get a list of all the directories in the protected_area_dir
    dir_list = [os.path.join(protected_area_dir, d) for d in os.listdir(protected_area_dir) if os.path.isdir(os.path.join(protected_area_dir, d))]

    # Sort the list of directories in ascending order
    sorted_dir_list = sorted(dir_list)

    # Get the last directory in the sorted list
    last_dir = sorted_dir_list[-1]

    last_folder_ndvi = os.path.join(last_dir)
    return last_folder_ndvi


def get_filelist(protected_area_date, bands_folder, format_name):
    # Get a list of all the directories in the protected_area_date
    dir_list = [os.path.join(protected_area_date, d) for d in os.listdir(protected_area_date) if os.path.isdir(os.path.join(protected_area_date, d))]

    # Sort the list of directories in ascending order
    sorted_dir_list = sorted(dir_list)

    # Get the last directory in the sorted list
    last_dir = sorted_dir_list[0]

    last_folder_bands = os.path.join(last_dir)

    file_list = sorted(glob.glob(os.path.join(last_folder_bands, format_name)))

    return file_list

def change_crs(latitude, longitude,pnnsfl_panel_path, geojson_path):
    # Load GeoJSON boundary and display it on a folium map
    boundary = gpd.read_file(geojson_path)
    m = folium.Map([latitude, longitude], zoom_start=11)
    folium.GeoJson(boundary).add_to(m)

    # Get the first geometry (assumes there is only one)
    footprint = boundary['geometry'].iloc[0]

    # Convert coords EPSG:4326 to EPSG:32618
    in_crs = 'EPSG:4326'  # WGS84 lat/long
    out_crs = 'EPSG:32618'  # UTM zone 19N
    transformer = pyproj.Transformer.from_crs(in_crs, out_crs, always_xy=True)
    footprint = transform(transformer.transform, footprint)

    # Write the transformed polygon to a shapefile
    with fiona.open(pnnsfl_panel_path, 'w', driver='ESRI Shapefile', crs=out_crs, schema={
        'geometry': 'Polygon',
        'properties': [('Name', 'str')]
    }) as polyShp:
        polyShp.write({
            'geometry': mapping(footprint),
            'properties': {'Name': ''}
        })

    print('Done!')


def transform_shapefile_coords(shapefile_path, in_crs='EPSG:4326', out_crs='EPSG:32618'):
    # Read in the shapefile coordinates
    c = fiona.open(shapefile_path)
    coords = [np.array(poly['geometry']['coordinates'])
              for poly in c.values()]
    print(coords)
    coodList_transform = []
    inProj = Proj(init='EPSG:4326')
    outProj = Proj(init='EPSG:32618')

    for x in coords:
        for y in x:
            for z in y:
                x1, y2 = z[0], z[1]
                x2, y2 = pyproj.transform(inProj, outProj, x1, y2)
                _cood = x2, y2
                coodList_transform.append(_cood)
    rowName = ''
    scheme = {
        'geometry': 'Polygon',
        'properties': [('Name', 'str')]
    }

    polyShp = fiona.open(shapefile_path,
                         'w',
                         driver='ESRI Shapefile',
                         schema=scheme,
                         crs='EPSG:32618')

    rowDict = {
        'geometry': {'type': 'Polygon',
                     'coordinates': [coodList_transform]},
        'properties': {'Name': rowName},
    }
    polyShp.write(rowDict)
    polyShp.close()
    print('Done!')


def clip_raster_on_mask(shapes, tiflist):
    for tif in tiflist:
        try:

            if os.path.splitext(tif)[1].upper() not in ['.TIF', '.TIFF']:
                continue

            basename = os.path.basename(tif)
            if not any(basename.endswith(f'B{i}.TIF') for i in [2, 3, 4, 5, 8]):
                send2trash(tif)
                continue

            with rasterio.open(tif) as src:
                out_image, out_transform = rasterio.mask.mask(src, shapes, crop=True)
                out_meta = src.meta.copy()
                out_meta.update({"driver": "GTiff",
                                 "height": out_image.shape[1],
                                 "width": out_image.shape[2],
                                 "transform": out_transform})
                out_tif = os.path.join(os.path.dirname(tif), '_mask'.join(os.path.splitext(basename)))
                with rasterio.open(out_tif, "w", **out_meta) as dest:
                    dest.write(out_image)

            send2trash(tif)
        except:
            continue

    print('\n')
    print('==============')
    print('Bands clipped!')


def affine_tif(tiflist):

    red_band_path = tiflist[2]
    red_band = rasterio.open(red_band_path)

    for tif in tiflist:
        if tif.endswith('.TIF'):
            band = rasterio.open(tif)
            with rasterio.open('_affine'.join(os.path.splitext(tif)),
                               'w',
                               driver='GTiff',
                               count=1,
                               height=red_band.height,
                               width=red_band.width,
                               dtype='float64',
                               transform=red_band.transform,
                               crs='EPSG:32618') as raster:
                raster.write(band.read(1), 1)
                raster.close()
                send2trash(tif)

    print("---")
    print("---")
    print("The band are affined")
    print("---")
    print("---")


def generate_atmospheric_correction(protected_area_date, tiflist, metadata):
    """
    Generates atmospheric correction for each TIFF file in the input list, and saves the reflectance data as a new TIFF
    file with '_reflectance' appended to the original filename. The original TIFF file is deleted after processing.

    :param tiflist: list of input TIFF filenames
    :param metadata: list of metadata for the input TIFF files
    """
    bandlist = [2, 3, 4, 5]  # band list: blue, green, red, NIR

    for i, tif_path in enumerate(tiflist):
        print(f"Processing band {bandlist[i]} for {tif_path}")
        with rasterio.open(tif_path) as tif:
            arr = tif.read(1)
            mp_reflactance, ap_reflectance = ac.reflectance_rescaling_coefficients(protected_area_date, metadata[0], bandlist[i])
            sume = ac.sun_elevation(metadata[0])
            reflectance = ac.radiance_to_reflectance(bandlist[i], arr, mp_reflactance, ap_reflectance, sume)
            profile = tif.profile.copy()
            profile.update(count=1, dtype='float64')
            reflectance_path = os.path.splitext(tif_path)[0] + '_reflectance.TIF'
            with rasterio.open(reflectance_path, 'w', **profile) as dst:
                dst.write(reflectance, 1)
            send2trash(tif_path)

    print("Atmospheric correction was successful.")


def generate_ndvi(tif_list, protected_area_date, folder_name, shapes):

    # Extract red and near-infrared bands
    red_band = tif_list[2]
    nir_band = tif_list[3]

    # Create NDVI folder
    ndvi_folder = os.path.join(protected_area_date, folder_name)

    # Calculate NDVI and save it to a file
    ndvi_file = os.path.join(ndvi_folder, 'NDVI.TIF')
    ndvi(red_band, nir_band, shapes, ndvi_file)

    # Convert forest NDVI and save it to a file
    clipped_file, total_area = forest_ndvi(red_band, nir_band, shapes, 0.3, ndvi_file)

    # Convert NDVI to forest/not-forest classification and save it to a file
    #forest_not_forest(ndvi_file, shapes, 0.7, ndvi_file)

    return clipped_file, total_area






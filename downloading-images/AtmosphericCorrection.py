# Standard library imports
import os
import numpy as np
from math import cos

# Third-party library imports
import rasterio
from rasterio.merge import merge
import unpackqa
import rioxarray as rxr
import xarray as xr

# External library imports

# Project-specific library imports


def radiometric_rescaling_coefficients(path_landsat8_metadata, band):
    with open(path_landsat8_metadata, 'r') as open_metaLandsat:
        content = open_metaLandsat.readlines()
        open_metaLandsat.close()
        rescaling_coefficients = []
        for line in content:
            if 'RADIANCE_MULT_BAND_' + str(band) in line:
                print(line)
                multiplicative_rescaling = line.split()
                multiplicative_rescaling = float(multiplicative_rescaling[-1])
                rescaling_coefficients.append(multiplicative_rescaling)  # getting the G value
            elif 'RADIANCE_ADD_BAND_' + str(band) in line:
                print(line)
                additive_rescaling = line.split()
                additive_rescaling = float(additive_rescaling[-1])
                rescaling_coefficients.append(additive_rescaling)  # Getting the B value
        print('get data')
        return rescaling_coefficients


def reflectance_rescaling_coefficients(protected_area_date, path_landsat8_metadata, band):
    """
    extract the reflectance rescaling coefficients from Landsat metadata. These coefficients are used to convert the
    raw digital numbers (DN) to at-sensor reflectance values.
    """
    with open(path_landsat8_metadata, 'r') as open_metaLandsat:
        content = open_metaLandsat.readlines()
        open_metaLandsat.close()
        rescaling_coefficients = []
        for line in content:
            if 'REFLECTANCE_MULT_BAND_' + str(band) in line:
                print(line)
                multiplicative_rescaling = line.split()
                multiplicative_rescaling = float(multiplicative_rescaling[-1])
                rescaling_coefficients.append(multiplicative_rescaling)  # getting the G value
            elif 'REFLECTANCE_ADD_BAND_' + str(band) in line:
                print(line)
                additive_rescaling = line.split()
                additive_rescaling = float(additive_rescaling[-1])
                rescaling_coefficients.append(additive_rescaling)  # Getting the B value

        filename = os.path.basename(protected_area_date)
        split_folder = filename.split('-')

        if 'LC08' in split_folder[-1]:
            rescaling_coefficients = rescaling_coefficients[:-2]
            return rescaling_coefficients

        rescaling_coefficients = rescaling_coefficients[2:]
        return rescaling_coefficients


def sun_elevation(path_landsat8_metadata):
    with open(path_landsat8_metadata, 'r') as open_metaLandsat:
        content = open_metaLandsat.readlines()
        open_metaLandsat.close()
        _sun_elevation_ = None
        for line in content:
            if 'SUN_ELEVATION' in line:
                print(line)
                _sun_elevation = line.split()
                _sun_elevation = float(_sun_elevation[-1])
                _sun_elevation_ = _sun_elevation  # getting sun elevation
        print('get data')
        return _sun_elevation_


def dn_to_radiance(band, arr, ML, AL):
    """
    # DN to Radiance: Gain And Bias method:

        Lλ = ML*Qcal+AL

        where:

        Lλ: top of atmosphere (TOA) reflectance and/or radiance
        ML: Band-specific multiplicative rescaling factor from the metadata (RADIANCE_MULT_BAND_x, where x is the band number)
        Qcal: Quantized and calibrated standard product pixel values (DN)
        AL: Band-specific additive rescaling factor from the metadata (RADIANCE_ADD_BAND_x, where x is the band number)
        """
    new_data_array = np.empty_like(arr)
    for i, row in enumerate(arr):
        for j, col in enumerate(row):

            # checking if the pixel value is not nan, to avoid background correction
            if arr[i][j] != np.nan:
                new_data_array[i][j] = ML * arr[i][j] + AL
    print(f'Radiance calculated for band {band}')
    return new_data_array


def radiance_to_reflectance(band, arr, Mp, Ap, SUME):
    """
    ρλ′= Mρ*Qcal+Aρ

    where:

    ρλ': TOA planetary reflectance, without correction for solar angle.  Note that ρλ' does not contain a correction for the sun angle.
    Qcal: Quantized and calibrated standard product pixel values (DN)
    Mρ: Band-specific multiplicative rescaling factor from the metadata (REFLECTANCE_MULT_BAND_x, where x is the band number)
    Aρ: Band-specific additive rescaling factor from the metadata (REFLECTANCE_ADD_BAND_x, where x is the band number)
    """
    new_data_array = np.empty_like(arr)
    for i, row in enumerate(arr):
        for j, col in enumerate(row):

            # checking if the pixel value is not nan, to avoid background correction
            if arr[i][j] != np.nan:
                new_data_array[i][j] = Mp * arr[i][j] + Ap

    """
    TOA reflectance with a correction for the sun angle is then:

    ρλ= ρλ′/cos(θSZ) = ρλ′/sin(θSE)

    where:

    ρλ:  TOA planetary reflectance
    θSE: Local sun elevation angle. The scene center sun elevation angle in degrees is provided in the metadata (SUN_ELEVATION).
    θSZ: Local solar zenith angle;  θSZ = 90° - θSE
    """
    θSZ = 90 - SUME
    new_data_array = new_data_array / cos(θSZ)
    return new_data_array


def apply_cloud_mask(qa_path, product='LANDSAT_8_C2_L2_QAPixel', flags=['Cloud', 'Cloud Shadow']):
    # Apply a cloud mask to an image using Landsat Quality Assessment (QA) data
    with rasterio.open(qa_path) as src:
        qa_data = src.read(1)

    cloud_mask = unpackqa.unpack_to_dict(qa_data, product=product, flags=flags)

    return cloud_mask

def combine_tifs(tif_list, output_path):
    """
    Combines multiple TIFF images into a single multiband TIFF file.

    Args:
    tiff_list (list of str): List of filenames for TIFF images to be combined.
    output_filename (str): Filename for the output multiband TIFF file.
    """
    # Open all TIFF images and read their metadata
    tiffs = []
    for tiff_filename in tif_list:
        tiff = rasterio.open(tiff_filename)
        tiffs.append(tiff)
    metadata = tiffs[0].meta.copy()

    # Update the metadata for the output multiband TIFF
    metadata.update(count=len(tif_list), dtype=rasterio.float32)

    # Merge all TIFF images into the output multiband TIFF
    merged, _ = merge(tiffs)

    # Write the output multiband TIFF to disk
    with rasterio.open(output_path, 'w', **metadata) as out:
        out.write(merged)

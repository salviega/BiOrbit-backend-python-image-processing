# Standard library imports
import os

# Third-party library imports
import numpy as np
import rasterio
from rasterio.mask import mask

# External library imports
from osgeo import gdal

# Project-specific library imports


def ndvi(band4_path, band5_path, shapes, output_path):
    with rasterio.open(band4_path) as band4:
        with rasterio.open(band5_path) as band5:
            red = band4.read(1)
            nir = band5.read(1)

            # Calculate NDVI
            ndvi_data = (nir - red) / (nir + red)

            with rasterio.open(
                    output_path,
                    'w',
                    driver='Gtiff',
                    width=ndvi_data.shape[1],
                    height=ndvi_data.shape[0],
                    count=1,
                    dtype='float64',
                    transform=band4.transform,
                    crs='EPSG:32618'
            ) as dst:
                dst.write(ndvi_data, 1)

    print('NDVI file created successfully')

    # Clip NDVI to the provided shapes
    clipped_file = os.path.join(os.path.dirname(output_path), 'NDVI_mask_clipped.TIF')
    with rasterio.open(output_path) as src:
        out_image, out_transform = mask(src, shapes, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        with rasterio.open(clipped_file, "w", **out_meta) as dest:
            dest.write(out_image)

    print('NDVI mask clipped to provided shapes')


def forest_ndvi(band4_path, band5_path, shapes, threshold, output_path):
    with rasterio.open(band4_path) as band4:
        with rasterio.open(band5_path) as band5:
            red = band4.read(1)
            nir = band5.read(1)

            # Calculate NDVI
            ndvi_data = (nir - red) / (nir + red)

            # Set values less than threshold to np.nan and same 0
            ndvi_data[ndvi_data < threshold] = np.nan
            ndvi_data[ndvi_data == 0] = np.nan

            with rasterio.open(
                    output_path,
                    'w',
                    driver='Gtiff',
                    width=ndvi_data.shape[1],
                    height=ndvi_data.shape[0],
                    count=1,
                    dtype='float64',
                    transform=band4.transform,
                    crs='EPSG:32618'
            ) as dst:
                dst.write(ndvi_data, 1)

    print('NDVI file created successfully')

    # Clip forest NDVI to the provided shapes
    clipped_file = os.path.join(os.path.dirname(output_path), 'forest_NDVI_mask_clipped.TIF')
    with rasterio.open(output_path) as src:
        out_image, out_transform = mask(src, shapes, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        with rasterio.open(clipped_file, "w", **out_meta) as dest:
            dest.write(out_image)

    print('Forest NDVI mask clipped to provided shapes')

    with rasterio.open(clipped_file) as src:
        band_forest = src.read(1)
        pixel_size = src.res[0] * src.res[1]  # assuming square pixels
        # Create a mask of the pixels greater than 0
        new_mask = band_forest > 0
        # Count the number of pixels greater than 0
        num_pixels = np.count_nonzero(new_mask)
        # Calculate the total area of the pixels greater than 0 in hectares
        total_area = num_pixels * pixel_size / 10000
        print(f"Total area of NDVI: {total_area} hectares")

    return clipped_file, total_area


def replace_nan_values(forest_cover, before_band_path, current_band_path, output_path, index):
    # Split the file path into components using the forward slash as the separator
    before_band_path_components = before_band_path.split("/")
    current_band_path_components = current_band_path.split("/")

    # Get the date component from the path (assumes the date component is the third-last element in the path)
    date_before_band_path_components = before_band_path_components[6]
    date_current_band_path_components = current_band_path_components[5]
    forest_cover.detection_date_list.append(date_current_band_path_components)

    if index == 1:
        date_before_band_path_components = date_before_band_path_components.replace('__.TIF', '')

    elif index >= 2:
        splited_before_band_path_components = date_before_band_path_components.split('__')
        new_date_before_band_path_components = splited_before_band_path_components[1]
        date_before_band_path_components = new_date_before_band_path_components.replace('.TIF', '')

    name = date_before_band_path_components + '__' + date_current_band_path_components
    new_output_path = os.path.join(output_path, name + '.TIF')

    # Open both input bands using rasterio
    with rasterio.open(before_band_path) as src1, rasterio.open(current_band_path) as src2:
        # Read the NDVI arrays for both bands
        ndvi_values1 = src1.read(1)
        ndvi_values2 = src2.read(1)

        # Create a new raster file with the same shape and metadata as the second input band
        metadata = src2.meta.copy()


        # Replace NaN values in the second image's NDVI array with corresponding values in the first image
        # if the values of the first image are not NaN
        ndvi_values2 = np.where(np.isnan(ndvi_values2) & (~np.isnan(ndvi_values1)), ndvi_values1, ndvi_values2)

        # Create a new raster file with the same shape and metadata as the second input band
        metadata = src2.meta.copy()
        with rasterio.open(new_output_path, 'w', **metadata) as dst:
            dst.write(ndvi_values2, 1)

            # Calculate the area of pixels greater than 0 in hectares
            pixel_size = metadata['transform'][0]
            area = (ndvi_values2 > 0.6).sum() * (pixel_size ** 2) / 10000
            print(f'Total area of NDVI: {area:.2f} hectares')
            forest_cover.total_extension_forest_cover_list.append(area)


def forest_not_forest(ndvi_file, shapes, threshold, output_path):
    """Classify forest and non-forest areas based on NDVI values and clip the output to the provided shapefile.

    Args:
        ndvi_file (str): Filepath of the NDVI image.
        shapes (list): List of shape tuples used to clip the output. Each shape tuple should be in the format (geometry, id).
        output_path (str): Filepath of the output forest mask raster file.

    Returns:
        None
    """
    # Open the NDVI image and replace 0 values with NaNs
    with rasterio.open(ndvi_file) as src:
        ndvi = src.read(1)
        ndvi[ndvi == 0] = np.nan

    # Create a boolean mask of the forest pixels
    forest_mask = ndvi >= threshold

    # Save the forest mask to a new raster file
    with rasterio.open(output_path, 'w', driver='GTiff', height=forest_mask.shape[0], width=forest_mask.shape[1],
                       count=1, dtype=rasterio.uint8, crs=src.crs, transform=src.transform) as dst:
        dst.write(forest_mask.astype(rasterio.uint8), 1)

    print('Forest/non-forest classification successful')

    # Clip forest/not-forest classification to the provided shapes
    clipped_file = os.path.join(os.path.dirname(output_path), 'forest_mask_clipped.tif')
    with rasterio.open(output_path) as src:
        out_image, out_transform = mask(src, shapes, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})
        with rasterio.open(clipped_file, "w", **out_meta) as dest:
            dest.write(out_image)

    print('Forest/non-forest mask clipped to provided shapes')

    with rasterio.open(clipped_file) as src:
        band_forest = src.read(1)
        pixel_size = src.res[0] * src.res[1]  # assuming square pixels
        # Create a boolean mask of the NaN pixels
        nan_mask = np.isnan(band_forest)
        # Invert the mask to get a mask of the non-NaN pixels
        non_nan_mask = ~nan_mask
        # Count the number of non-NaN pixels
        num_non_nan_pixels = np.count_nonzero(non_nan_mask)
        # Calculate the total area of the non-NaN pixels in hectares
        total_area = num_non_nan_pixels * pixel_size / 10000
        print(f"Total area of forest/non-forest: {total_area} hectares")

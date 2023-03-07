import os

import rasterio
from rasterio.mask import mask
import numpy as np


def ndvi(band4, band5, output_path):
    """" to solve the issue of red surface reflectances close to zero : just add a constant to the red band surface
    reflectance. This constant must be greater than the standard deviation of atmospheric correction noise. As this
    one is usually close to 0.01, the constant could be 0.05.
    """

    dataset1 = rasterio.open(band4)
    dataset2 = rasterio.open(band5)

    red = dataset1.read(1)
    nir = dataset2.read(1)

    # Calculate NDVI
    ndvi = (nir - red) / (nir + red)

    arr = rasterio.open(output_path,
                        'w',
                        driver='Gtiff',
                        width=ndvi.shape[1], height=ndvi.shape[0],
                        count=1,
                        dtype='float64',
                        transform=dataset1.transform,
                        crs='EPSG:32618')
    arr.write(ndvi, 1)
    arr.close()
    print('succesful')


def forest_not_forest(ndvi_file, shapes, output_path):
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

    # Set a threshold value for forest/non-forest classification
    threshold = 0.7

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


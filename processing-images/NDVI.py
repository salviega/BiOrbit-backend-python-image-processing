import rasterio
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

    ndviS = np.empty_like(red)
    for i, row in enumerate(red):
        for j, col in enumerate(row):
            if nir[i][j] != np.nan or red[i][j] != np.nan:
                # ndviS[i][j] = ((nir[i][j] - red[i][j]) / (nir[i][j] + red[i][j])) # Normalized difference vegetation index (NDVI)
                # ndviS[i][j] = ((nir[i][j] - red[i][j]) + 0.05 / (nir[i][j] + red[i][j]) +0.05) # Atmospheric Correction Resistant Vegetation Index (ANCORVI)
                ndviS[i][j] = ((nir[i][j] - red[i][j]) + 0.05 / (
                            nir[i][j] + red[i][j]) + 0.05) * 0.0001  # scale factor

    arr = rasterio.open(output_path,
                        'w',
                        driver='Gtiff',
                        width=dataset1.width, height=dataset1.height,
                        count=1,
                        dtype='float64',
                        transform=dataset1.transform,
                        crs='EPSG:32618')
    arr.write(ndviS, 1)
    arr.close()
    print('succesful')


def forest_not_forest(ndvi, output_path):
    dataset = rasterio.open(ndvi)
    band = dataset.read(1)
    ndviS = np.empty_like(band)

    for i, row in enumerate(band):
        for j, col in enumerate(row):
            if band[i][j] < 0:
                ndviS[i][j] = np.nan
            if 0.00006 < band[i][j] < 0.0001:
                ndviS[i][j] = band[i][j]
            else:
                ndviS[i][j] = np.nan

    arr = rasterio.open(output_path,
                        'w',
                        driver='Gtiff',
                        width=dataset.width, height=dataset.height,
                        count=1,
                        dtype='float64',
                        transform=dataset.transform,
                        crs='EPSG:32618')
    arr.write(ndviS, 1)
    arr.close()
    print('succesful')


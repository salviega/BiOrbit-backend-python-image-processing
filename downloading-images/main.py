# Third-party library imports
from decouple import config

# Project-specific library imports
from satelliteAPI import LandsatAPI

# site's coord (EPSG:4326)
protected_area = config('PROTECTED_AREA')
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

api = LandsatAPI(username, password, chromedriver_path, downloads_dir, landsat_dir)
api.query((latitude, longitude), ("01/01/2021", "04/31/2021"))  # date start & date end

# Standard library imports
import datetime
import glob
import os.path
from datetime import timedelta
import shutil
import tarfile
import time

# Third-party library imports
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from send2trash import send2trash

# Project-specific library imports
from processing import *
from NDVI import *


class LandsatAPI:
    def __init__(self, username, password, chromedriver_path, downloads_dir, protected_area_dir,
                 protected_area_deforestation_dir):

        self.username = username
        self.password = password
        self.driver = 10 # prepare_and_run_chromium(chromedriver_path, downloads_dir)
        self.download_folder = downloads_dir
        self.protected_area_dir = protected_area_dir
        self.protected_area_deforestation_dir = protected_area_deforestation_dir

    def query(self, chromedriver_path, downloads_dir, coordinates, date_range):
        class SatelliteImage:
            def __int__(self, code, data_acquired, path, row):
                self.code = code
                self.data_acquired = data_acquired,
                self.path = path,
                self.path = row

        while True:
            try:
                # Load login USGS website
                self.driver.get('https://ers.cr.usgs.gov/login')
                time.sleep(3)

                # Login to USGS
                login_form = self.driver.find_element(By.ID, "loginForm")
                username_input = login_form.find_element(By.NAME, "username")
                username_input.send_keys(self.username)
                password_input = login_form.find_element(By.NAME, "password")
                password_input.send_keys(self.password)
                login_button = login_form.find_element(By.ID, "loginButton")
                login_button.click()
                time.sleep(3)

                # Navigate to home page
                self.driver.get('https://earthexplorer.usgs.gov')
                time.sleep(3)

                # Select coordinates types: decimals
                decimals_button = self.driver.find_element(By.XPATH, '//*[@id="lat_lon_section"]/fieldset/label[2]')
                decimals_button.click()

                # Add coords
                for coord in coordinates:
                    time.sleep(1.5)
                    latitude = str(coord[1])
                    longitude = str(coord[0])
                    coord_entry_add_button = self.driver.find_element(By.ID, "coordEntryAdd")
                    coord_entry_add_button.click()
                    self.driver.execute_script("document.getElementsByClassName('latitude txtbox decimalBox')["
                                               "1].click();")
                    self.driver.execute_script(f"document.getElementsByClassName('latitude txtbox decimalBox')["
                                               f"1].value = {latitude};")
                    self.driver.execute_script("document.getElementsByClassName('longitude txtbox decimalBox')["
                                               "1].click();")
                    self.driver.execute_script(f"document.getElementsByClassName('longitude txtbox decimalBox')["
                                               f"1].value = {longitude};")
                    self.driver.execute_script(f"document.getElementsByClassName('ui-button ui-corner-all "
                                               f"ui-widget')[7].click();")

                # Add data range
                start, end = get_date_range(date_range)
                start_date_input = self.driver.find_element(By.ID, "start_linked")
                start_date_input.send_keys(start)
                end_date_input = self.driver.find_element(By.ID, "end_linked")
                end_date_input.send_keys(end)
                search_button = self.driver.find_element(By.XPATH,
                                                         "/html/body/div[1]/div/div/div[2]/div[2]/div[1]/div[10]/input[1]")
                search_button.click()
                time.sleep(6)

                # Next page: Data Sets
                # Select dataset(s):
                category_button = self.driver.find_element(By.XPATH,
                                                           "/html/body/div[1]/div/div/div[2]/div[2]/div[2]/div[3]/div[1]/ul/li[14]/div")
                category_button.click()
                subcategory_button = self.driver.find_element(By.XPATH,
                                                              "/html/body/div[1]/div/div/div[2]/div[2]/div[2]/div[3]/div[1]/ul/li[14]/ul/li[3]/div")
                subcategory_button.click()
                subcategory_checkbox = self.driver.find_element(By.XPATH,
                                                                "/html/body/div[1]/div/div/div[2]/div[2]/div[2]/div[3]/div[1]/ul/li[14]/ul/li[3]/ul/fieldset/li[1]/span/div[1]/input")
                subcategory_checkbox.click()
                result_button = self.driver.find_element(By.XPATH,
                                                         "/html/body/div[1]/div/div/div[2]/div[2]/div[2]/div[3]/div[3]/input[3]")
                result_button.click()
                time.sleep(3)

                # Next page: Results
                # Select image for download

                # Get images downloaded
                tar_list = glob.glob(os.path.join(self.download_folder, '*.tar'))
                satellite_image_downloaded_date_list = []

                for tar in tar_list:
                    split_satellite_image_downloaded_name = tar.split('_')
                    satellite_image_downloaded_date = split_satellite_image_downloaded_name[3]
                    satellite_image_downloaded_date_list.append(satellite_image_downloaded_date)

                html = self.driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                time.sleep(3)

                # Extract number of images
                number_images = soup.find('th', {'class': 'ui-state-icons'}).get_text()
                images = [int(item) for item in number_images.split() if item.isdigit()]

                # Extract number of pages
                number_pages = soup.find(class_='paginationControl unselectable')
                pages = 0
                for item in number_pages:
                    if 'of' in item:
                        for _item in item.split():
                            if _item.isdigit():
                                pages = int(_item)
                                break

                image = 0
                page = 1
                while page <= pages:

                    print('\n')
                    print('========')
                    print(f'Page: {page}')
                    print(f'Pages: {pages}')

                    html = self.driver.page_source
                    soup = BeautifulSoup(html, "html.parser")
                    time.sleep(3)

                    result_content = soup.find_all(class_='resultRowContent')
                    j = 0
                    for content in result_content:

                        name = content.find('li').getText()
                        satellite_image = SatelliteImage()
                        satellite_image.name = name
                        satellite_image.data_acquired = content.find_all('li')[1].getText()
                        satellite_image.path = content.find_all('li')[2].getText()
                        satellite_image.row = content.find_all('li')[3].getText()

                        # were images download yet?
                        split_satellite_image_name = satellite_image.name.split(' ')
                        satellite_image_name = split_satellite_image_name[1]
                        image_enable = False

                        for tar in tar_list:
                            if satellite_image_name in tar:
                                image_enable = True

                        if image_enable:
                            print(f"{satellite_image_name} was already downloaded ")

                            j += 1
                            image += 1

                            if j < len(result_content):
                                continue

                            # Change the page
                            if j == len(result_content):

                                if page < pages:
                                    page += 1
                                    next_page_button = self.driver.find_element(By.XPATH,
                                                                                '/html/body/div[1]/div/div/div[2]/div[2]/div[4]/form/div[2]/div[2]/div/div[2]/a[3]')
                                    next_page_button.click()
                                    time.sleep(5)
                                    break

                                else:
                                    page += 1
                                    print('\n')
                                    print('=====================================')
                                    print('The satellite images were downloaded!')
                                    break

                        # Download image
                        time.sleep(0.5)
                        downloads = self.driver.find_elements(By.CLASS_NAME, 'download')
                        downloads[j].click()
                        time.sleep(6)

                        download_button = self.driver.execute_script(
                            "return document.querySelector('.btn.btn-secondary.downloadButton')")

                        if not download_button is None:

                            self.driver.execute_script(
                                "document.getElementsByClassName('ui-button ui-corner-all ui-widget "
                                "ui-button-icon-only ui-dialog-titlebar-close')[2].click();")

                            j += 1
                            image += 1

                            if j < len(result_content):
                                continue

                            # Change the page
                            if j == len(result_content):
                                if page < pages:
                                    page += 1
                                    next_page_button = self.driver.find_element(By.XPATH,
                                                                                '/html/body/div[1]/div/div/div[2]/div[2]/div[4]/form/div[2]/div[2]/div/div[2]/a[3]')
                                    next_page_button.click()
                                    time.sleep(5)
                                    break
                                else:
                                    page += 1
                                    print('\n')
                                    print('=====================================')
                                    print('The satellite images were downloaded!')
                                    break

                        self.driver.execute_script(
                            "document.getElementsByClassName('btn btn-secondary productOptionsButton')[0].click();")

                        self.driver.execute_script("document.getElementsByClassName('btn btn-secondary "
                                                   "secondaryDownloadButton')[0].click();")

                        print('\n')
                        print(f'Image: {image + 1}')
                        print(satellite_image.name)

                        wait_for_downloads(self.download_folder)
                        wait_for_download_completion(self.download_folder)
                        time.sleep(0.5)

                        self.driver.execute_script("document.getElementsByClassName('btn btn-secondary "
                                                   "closeProductOptionsButton')[0].click();")

                        self.driver.execute_script("document.getElementsByClassName('ui-button ui-corner-all ui-widget "
                                                   "ui-button-icon-only ui-dialog-titlebar-close')[2].click();")

                        j += 1
                        image += 1

                        # Change the page
                        if j == len(result_content):

                            if page < pages:
                                page += 1
                                next_page_button = self.driver.find_element(By.XPATH,
                                                                            '/html/body/div[1]/div/div/div[2]/div[2]/div[4]/form/div[2]/div[2]/div/div[2]/a[3]')
                                next_page_button.click()
                                time.sleep(6)

                            else:
                                page += 1
                                print('\n')
                                print('=====================================')
                                print('The satellite images were downloaded!')

                time.sleep(1.5)
                self.driver.close()
                break
            except Exception as error:
                print(f"Exception: {error}")
                crdownload_list = glob.glob(os.path.join(self.download_folder, '.crdownload'))
                for file in crdownload_list:
                    os.remove(file)
                time.sleep(1.5)
                self.driver.close()
                self.driver = prepare_and_run_chromium(chromedriver_path, downloads_dir)
                continue

    def processing(self, protected_area_name, protected_area_total_extension, footprint, protected_area_dir,
                   protected_area_shape_path, bands_folder, ndvi_folder, deforestation_folder):

        class ForestCover:
            def __int__(self, protected_area_name, photo, description, footprint, last_detection_date,
                        total_extension_protected_area, detection_date_list, total_extension_forest_cover_list):
                self.protected_area_name = protected_area_name
                self.photo = photo,
                self.description = description,
                self.coordinates = footprint,
                self.last_detection_date = last_detection_date,
                self.total_extension_protected_area = total_extension_protected_area,
                self.detection_date_list = detection_date_list,
                self.total_extension_forest_cover_list = total_extension_forest_cover_list

        forest_cover = ForestCover()
        forest_cover.last_detection_date = datetime.date.today()
        forest_cover.total_extension_protected_area = protected_area_total_extension
        forest_cover.detection_date_list = []
        forest_cover.total_extension_forest_cover_list = []

        # extract_and_move_file(self.download_folder, self.protected_area_dir, 'bands_folder', 'ndvi_folder')

        # Open shapes file

        with fiona.open(protected_area_shape_path, "r") as panel, fiona.open(protected_area_shape_path,
                                                                             "r") as protected_area_src:
            protected_area_shape = [feature['geometry'] for feature in protected_area_src]

        protected_area_dates = get_sorted_tif_list(self.protected_area_dir, deforestation_folder)

        '''for protected_area_date in protected_area_dates:

            # clip to panel
            tif_list = get_filelist(protected_area_date, bands_folder, "*.TIF")
            clip_raster_on_mask(protected_area_shape, tif_list)

            # affine shapes
            tif_list = get_filelist(protected_area_date, bands_folder, '*.TIF')
            affine_tif(tif_list)

            tif_list = get_filelist(protected_area_date, bands_folder, '*.TIF')
            name = os.path.basename(protected_area_date) + '_B2_B3_B4_B5_multiband.TIF'
            output_path = os.path.join(protected_area_date, name)
            create_multiband_color_tiff(tif_list, output_path)

            # convert DN to Radiance
            tif_list = get_filelist(protected_area_date, bands_folder, '*.TIF')
            metadata_list = get_filelist(protected_area_date, bands_folder, '*MTL.txt')
            generate_atmospheric_correction(protected_area_date, tif_list, metadata_list)

            # NDVI
            tif_list = get_filelist(protected_area_date, bands_folder, '*.TIF')
            protected_area_ndvi_dir, protected_area_ndvi_total_extension = generate_ndvi(tif_list, protected_area_date,
                                                                                         ndvi_folder + '_folder',
                                                                                         protected_area_shape)'''

        filename_1 = 'ndvi_folder/forest_NDVI_mask_clipped.TIF'
        filename_2 = 'forest_NDVI_mask_clipped.TIF'

        for i, protected_area_date in enumerate(protected_area_dates):

            if i == 0:

                tif_list = get_filelist(protected_area_date, bands_folder, "*.TIF")
                ndvi_date = os.path.join(protected_area_date, filename_1)
                multi_band_tiff = glob.glob(protected_area_date + '/*.TIF')
                multi_band_tiff = multi_band_tiff[0]

                replace_nan_value_multiband(ndvi_date, multi_band_tiff)

                with rasterio.open(ndvi_date) as src:
                    band_forest = src.read(1)
                    pixel_size = src.res[0] * src.res[1]  # assuming square pixels
                    # Create a mask of the pixels greater than 0
                    new_mask = band_forest > 0
                    # Count the number of pixels greater than 0
                    num_pixels = np.count_nonzero(new_mask)
                    # Calculate the total area of the pixels greater than 0 in hectares
                    total_area = num_pixels * pixel_size / 10000
                    print(f"Total area of NDVI: {total_area} hectares")
                    forest_cover.total_extension_forest_cover_list.append(total_area)

                # construct the new filename using ndvi_date
                split_name = protected_area_date.split('/')
                output_file = os.path.join(self.protected_area_deforestation_dir, split_name[-1] + '__.TIF')
                forest_cover.detection_date_list.append(split_name[-1])

                shutil.copy(ndvi_date, output_file)
                continue

            if i < 1:
                deforestation_tiff_list = sorted(glob.glob(os.path.join(self.protected_area_deforestation_dir, '*.TIF')))

                ndvi_before_date = os.path.join(deforestation_tiff_list[i-1])
                ndvi_current_date_dir = get_folder(protected_area_dates[i], ndvi_folder)
                ndvi_current_date = os.path.join(ndvi_current_date_dir, filename_2)

                replace_nan_values(forest_cover, ndvi_before_date, ndvi_current_date, self.protected_area_deforestation_dir, i)

        return forest_cover


def extract_and_move_file(download_folder, protected_area_dir, bands_folder_name, ndvi_folder_name):
    # Get the latest downloaded file
    tar_list = glob.glob(os.path.join(download_folder, '*.tar'))

    for tar_file in tar_list:
        # Extract the downloaded file to a folder
        extract_dir = os.path.splitext(tar_file)[0]
        tar = tarfile.open(tar_file)
        tar.extractall(extract_dir)
        tar.close()

        # Move the downloaded file to the trash folder
        send2trash(tar_file)

        # Move the extracted folder to the Landsat8 folder
        dir_name = os.path.basename(os.path.normpath(extract_dir))
        split_folder = dir_name.split('_')
        name = split_folder[3]
        name = name[:4] + '-' + name[4:]
        name = name[:7] + '-' + name[7:] + '-' + split_folder[0]
        new_folder = os.path.join(protected_area_dir, name)
        os.makedirs(new_folder, exist_ok=True)
        move_dir = os.path.join(download_folder, dir_name)
        shutil.move(move_dir, new_folder)
        on_new_folder = os.path.join(new_folder, dir_name)
        print(new_folder)

        try:
            os.rename(on_new_folder, os.path.join(new_folder, bands_folder_name))

        except:
            send2trash(on_new_folder)
            continue

        # Create NDVI directory
        ndvi_folder_path = os.path.join(new_folder, ndvi_folder_name)
        os.makedirs(ndvi_folder_path, exist_ok=True)


def get_date_range_for_download(landsat_folder):
    """
    Determines the date range for downloading a satellite image based on the files in the given folder.
    """
    # Get the latest two date directories
    date_dirs = sorted(os.listdir(landsat_folder))[-2:]
    # Convert the date strings to datetime objects
    dates = [datetime.strptime(date, '%Y-%m-%d') for date in date_dirs]
    # Calculate the date range between the two dates
    date_range = dates[0] - dates[1]

    # Get the current date
    today = datetime.date.today()
    # Calculate the start and end dates for downloading the satellite image
    if date_range == timedelta(days=7):
        start = today - timedelta(days=9)
    else:
        start = today - timedelta(days=7)
    end = today.strftime('%m/%d/%Y')

    # Return the start and end dates as a tuple
    return start.strftime('%m/%d/%Y'), end


def get_footprint(latitude, longitude, path_to_geojson):
    """
    Get the footprint of a location given its latitude and longitude, using a GeoJSON file to define the boundary.
    """
    # Create a new folium map centered on the given latitude and longitude
    m = folium.Map([latitude, longitude], zoom_start=11)

    # Load the GeoJSON file containing the boundary and add it to the map
    boundary = gpd.read_file(path_to_geojson)
    folium.GeoJson(boundary).add_to(m)

    # Get the footprint by iterating over the geometry column of the boundary GeoDataFrame
    footprint = None
    for i in boundary['geometry']:
        footprint = i

    return footprint


def wait_for_download_completion(download_folder):
    """
    Wait until all downloads in the given folder have completed.
    """
    print("Downloading...")
    while any(filename.endswith(".crdownload") for filename in os.listdir(download_folder)):
        time.sleep(1)  # Wait 1 second between checks
    print("Download completed!")


def wait_for_downloads(download_folder):
    """
    Wait until a file with a .crdownload extension appears in the download folder, indicating that a download is in
    progress.
    """
    print("Waiting for the download to start...")
    while not any(filename.endswith(".crdownload") for filename in os.listdir(download_folder)):
        time.sleep(1)  # Wait 1 second between checks
    print("Download started!")


def prepare_and_run_chromium(chromedriver_path, downloads_dir):
    # Set download options for headless mode
    options = Options()

    # options.headless = True

    options.add_experimental_option("prefs", {
        "download.default_directory": downloads_dir,
        "download.prompt_for_download": False,
    })

    # Create a Service object
    service = Service(chromedriver_path)

    # Start Chrome driver and set download behavior
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": downloads_dir})

    # Return the driver object
    return driver


def get_date_range(date_range_days):
    """
    Returns a tuple of the start and end dates for a given date range.

    Args:
        date_range_days (int): The number of days in the date range.

    Returns:
        tuple: A tuple of the start and end dates as strings in the format 'mm/dd/yyyy'.
    """
    # Get the current date
    today = datetime.date.today()

    # Format the current date as a string
    end = today.strftime('%m/%d/%Y')

    # Calculate the start date that is `date_range_days` days ago from the current date
    start = today - datetime.timedelta(days=date_range_days)

    # Format the start date as a string
    start_str = start.strftime('%m/%d/%Y')

    # Return the start and end dates as a tuple
    return start_str, end


def get_sorted_tif_list(path, ignore_folder_name):
    """
    Returns a list of all folders in the specified path, sorted by name.
    """
    tif_list = []
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path) and item != ignore_folder_name:
            tif_list.append(item_path)
    return sorted(tif_list)

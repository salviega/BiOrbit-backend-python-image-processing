# Standard library imports
import datetime
from datetime import timedelta
import glob
import os
import shutil
import tarfile
import time

# Third-party library imports
from bs4 import BeautifulSoup
import folium
import geopandas as gpd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from send2trash import send2trash

# Project-specific library imports


class LandsatAPI:
    def __init__(self, username, password, chromedriver_path, downloads_dir, landsat_dir):

        self.username = username
        self.password = password
        self.driver = prepare_and_run_chromium(chromedriver_path, downloads_dir)
        self.download_folder = downloads_dir
        self.landsat_dir = landsat_dir

    def query(self, coordinates, date):
        class SatelliteImage:
            def __int__(self, code, data_acquired, path, row):
                self.code = code
                self.data_acquired = data_acquired,
                self.path = path,
                self.path = row

        # Log in to USGS
        login_form = self.driver.find_element(By.ID, "loginForm")
        username_input = login_form.find_element(By.NAME, "username")
        username_input.send_keys(self.username)
        password_input = login_form.find_element(By.NAME, "password")
        password_input.send_keys(self.password)
        login_button = login_form.find_element(By.ID, "loginButton")
        login_button.click()
        time.sleep(2)

        # Navigate to home page
        self.driver.get('https://earthexplorer.usgs.gov')
        time.sleep(3)

        # Select coordinates types: decimals
        decimals_button = self.driver.find_element(By.XPATH, '//*[@id="lat_lon_section"]/fieldset/label[2]')
        decimals_button.click()
        time.sleep(1)

        # Add coords
        latitude, longitude = coordinates
        coord_entry_add_button = self.driver.find_element(By.ID, "coordEntryAdd")
        coord_entry_add_button.click()
        latitude_input = self.driver.find_element(By.XPATH, "/html/body/div[7]/div[2]/div[2]/input")
        latitude_input.send_keys(latitude)
        longitude_input = self.driver.find_element(By.XPATH, "/html/body/div[7]/div[2]/div[5]/input")
        longitude_input.send_keys(longitude)
        submit_button = self.driver.find_element(By.XPATH, "/html/body/div[7]/div[3]/div/button[1]")
        submit_button.click()
        time.sleep(0.5)

        # Add data range
        start, end = date
        start_date_input = self.driver.find_element(By.ID, "start_linked")
        start_date_input.send_keys(start)
        end_date_input = self.driver.find_element(By.ID, "end_linked")
        end_date_input.send_keys(end)
        search_button = self.driver.find_element(By.XPATH,
                                                 "/html/body/div[1]/div/div/div[2]/div[2]/div[1]/div[10]/input[1]")
        search_button.click()

        # Next page: Data Sets
        # Select dataset(s):
        category_button = self.driver.find_element(By.XPATH,
                                                   "/html/body/div[1]/div/div/div[2]/div[2]/div[2]/div[3]/div["
                                                   "1]/ul/li[14]/span/div")
        category_button.click()
        subcategory_button = self.driver.find_element(By.XPATH,
                                                      "/html/body/div[1]/div/div/div[2]/div[2]/div[2]/div[3]/div["
                                                      "1]/ul/li[14]/ul/li[3]/span/div")
        subcategory_button.click()
        subcategory_checkbox = self.driver.find_element(By.XPATH,
                                                        "/html/body/div[1]/div/div/div[2]/div[2]/div[2]/div[3]/div["
                                                        "1]/ul/li[14]/ul/li[3]/ul/fieldset/li[1]/span/div[1]/input")
        subcategory_checkbox.click()
        result_button = self.driver.find_element(By.XPATH,
                                                 "/html/body/div[1]/div/div/div[2]/div[2]/div[2]/div[3]/div[3]/input[3]"
                                                 )
        result_button.click()
        time.sleep(2)

        # Next page: Results
        # Select image for download
        html = self.driver.page_source
        soup = BeautifulSoup(html, "html.parser")

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

            result_content = soup.find_all(class_='resultRowContent')
            j = 0
            for content in result_content:
                name = content.find('li').getText()
                if 'LC09' in name:
                    continue

                satellite_image = SatelliteImage()
                satellite_image.name = name
                satellite_image.data_acquired = content.find_all('li')[1].getText()
                satellite_image.path = content.find_all('li')[2].getText()
                satellite_image.row = content.find_all('li')[3].getText()

                # Download image
                downloads = self.driver.find_elements(By.CLASS_NAME, 'download')
                downloads[j].click()
                time.sleep(1.5)

                download_tabindex = self.driver.find_element(By.XPATH, "/html/body/div[6]")

                product_options_button = download_tabindex.find_element(By.XPATH, '//*[@id="optionsContainer"]/div'
                                                                                  '/div[1]/button')
                product_options_button.click()
                time.sleep(1.5)

                '''
                    TODO: product_bundle_button isn't downloading the image
                '''

                product_bundle_button = self.driver.find_element(By.XPATH, '/html/body/div[6]/div[2]/div/div['
                                                                           '2]/div/div[2]/div/div/div[2]/div[2]/button')
                product_bundle_button.click()

                wait_for_downloads(self.download_folder)
                wait_for_download_completion(self.download_folder)
                print('\n')
                time.sleep(1.5)

                cancel_button = self.driver.find_element(By.XPATH,
                                                         '//*[@id="632210d4770592cf_Modal"]/div/div/div[1]/div['
                                                         '2]/button')
                cancel_button.click()
                time.sleep(1.5)

                ''' 
                    <- bug  
                '''

                print('\n')
                print(f'Image: {image + 1}')
                print(satellite_image.name)

                j += 1
                image += 1

                # Change the page
                if j == len(result_content):

                    if page < pages:
                        page += 1
                        next_page_button = self.driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div['
                                                                              '2]/div[4]/form/div[2]/div[2]/div/div['
                                                                              '2]/a[3]')
                        next_page_button.click()
                        time.sleep(1.5)

                    else:
                        page += 1
                        print('\n')
                        print('=====================================')
                        print('The satellite images were downloaded!')
                        time.sleep(1.5)
                        self.driver.quit()

            extract_and_move_file(self.download_folder, self.landsat_dir, 'band', 'NDVI')


def extract_and_move_file(downloads_dir, landsat_dir, bands_folder_name, ndvi_folder_name):
    """
    Extracts the downloaded file, moves the extracted folder to Landsat8 folder with a new name, and removes the
    downloaded file.
    """
    # Extract the downloaded files
    files = glob.glob(downloads_dir + '/*.tar')
    for file in files:
        try:
            file_name = os.path.basename(file)
            file_name_without_ext = os.path.splitext(file_name)[0]
            file_folder_name = file_name_without_ext.replace('_', ' ').split()
            name = file_folder_name[3]
            name = name[:4] + '-' + name[4:]
            name = name[:7] + '-' + name[7:]

            with tarfile.open(file) as tar:
                tar.extractall(os.path.join(downloads_dir, file_name_without_ext))
            tar.close()

            # Move to trash .tar
            send2trash(file)

            # Move extracted folder to Landsat8 folder with a new name
            extracted_folder = os.path.join(downloads_dir, file_name_without_ext)
            new_folder = os.path.join(landsat_dir, name)

            if not os.path.exists(new_folder):

                os.makedirs(new_folder, exist_ok=True)
                shutil.move(extracted_folder, os.path.join(new_folder, bands_folder_name))

                # Create NDVI directory
                os.mkdir(os.path.join(new_folder, ndvi_folder_name))

            else:
                send2trash(os.path.join(downloads_dir, file_name_without_ext))

        except:
            continue

    print('\n')
    print('===================================')
    print("The satellite images were extracted")


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
    '''
        TODO: Fix the headless
    '''

    # options.headless('--headless')

    ''' 
        <- bug  
    '''
    options.add_experimental_option("prefs", {
        "download.default_directory": downloads_dir,
        "download.prompt_for_download": False,
    })

    # Create a Service object
    service = Service(chromedriver_path)

    # Start Chrome driver and set download behavior
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": downloads_dir})

    # Load the website and wait for 3 seconds
    driver.get('https://ers.cr.usgs.gov/login')
    time.sleep(3)

    # Return the driver object
    return driver

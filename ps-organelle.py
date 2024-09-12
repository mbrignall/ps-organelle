import os
import requests
import time
from dotenv import load_dotenv
from requests.exceptions import ChunkedEncodingError, ConnectionError

# Load environment variables
load_dotenv()

# Fetch the API token from .env
API_TOKEN = os.getenv('PATCHSTORAGE_API_TOKEN')

# Correct API base URLs
BASE_PATCHES_URL = 'https://patchstorage.com/api/beta/patches'
PATCH_DETAIL_URL_TEMPLATE = 'https://patchstorage.com/api/beta/patches/{patch_id}'
DOWNLOAD_URL_TEMPLATE = 'https://patchstorage.com/api/beta/patches/{patch_id}/files/{file_id}/download/'

# Headers for API requests, including User-Agent
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (compatible; PatchstorageClient/1.0)'  # Set the User-Agent header
}

# Directory where patches will be saved
BASE_DOWNLOAD_DIR = 'patches'

def fetch_patches(platform_id=154):
    """Fetches patches for the Organelle platform using the beta API."""
    url = BASE_PATCHES_URL
    params = {
        'platforms': platform_id,
        'page': 1,        # Start on page 1
        'per_page': 100   # Adjust as needed
    }

    patches = []
    while True:
        try:
            response = requests.get(url, headers=HEADERS, params=params)
            
            if response.status_code == 403:
                print(f"Error: Received status code {response.status_code} - Forbidden")
                print(f"Response content: {response.text}")
                break
            
            if response.status_code != 200:
                print(f"Error: Received status code {response.status_code} from {url}")
                print(f"Response content: {response.text}")
                break

            # Attempt to parse the response as JSON
            data = response.json()
            
            # Check if the response is a list of patches
            if isinstance(data, list):
                patches.extend(data)  # If data is a list, extend it directly
            else:
                print(f"Unexpected response format: {data}")
                break

            # Check if we've fetched all patches (if the length of patches returned is less than per_page, stop)
            if len(data) < params['per_page']:
                break  # No more pages to fetch
            
            # Increment the page parameter for the next request
            params['page'] += 1

        except requests.exceptions.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response text: {response.text}")
            break
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            break

    return patches

def fetch_patch_detail(patch_id):
    """Fetch detailed information about a patch including file URLs."""
    url = PATCH_DETAIL_URL_TEMPLATE.format(patch_id=patch_id)
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch patch details for ID {patch_id}. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed for patch {patch_id}: {e}")
        return None

def download_patch_file(download_url, save_path, retries=3):
    """Download a single patch file using the provided download URL with retry logic."""
    attempt = 0
    while attempt < retries:
        try:
            print(f"Downloading {save_path} (Attempt {attempt + 1}/{retries})...")
            response = requests.get(download_url, headers=HEADERS, stream=True, timeout=10)

            # Check if the response is successful
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                print(f"Downloaded patch file {save_path}")
                return  # Exit the function after a successful download
            else:
                print(f"Failed to download patch file from {download_url}. Status code: {response.status_code}")
                print(f"Response content: {response.text}")
                break

        except (ChunkedEncodingError, ConnectionError, requests.exceptions.Timeout) as e:
            print(f"Download failed due to {type(e).__name__}: {e}")
            attempt += 1
            time.sleep(2)  # Wait before retrying
            if attempt == retries:
                print(f"Failed to download {save_path} after {retries} attempts.")
                break

def process_and_download_patches():
    """Process patches and download patch files into category/tag subfolders."""
    patches = fetch_patches()

    for patch in patches:
        patch_id = patch['id']
        patch_title = patch['title']

        # Get the first category and first tag
        category = patch['categories'][0]['slug'] if patch['categories'] else 'uncategorized'
        first_tag = patch['tags'][0]['slug'] if patch['tags'] else 'untagged'

        # Create top-level category folder
        category_dir = os.path.join(BASE_DOWNLOAD_DIR, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

        # Create subfolder for the first tag within the category
        tag_dir = os.path.join(category_dir, first_tag)
        if not os.path.exists(tag_dir):
            os.makedirs(tag_dir)

        # Fetch detailed patch information to get download URLs
        patch_detail = fetch_patch_detail(patch_id)
        if patch_detail:
            for file_obj in patch_detail.get('files', []):
                download_url = file_obj['url']
                file_name = file_obj['filename']

                # Set the full path where the file will be saved
                save_path = os.path.join(tag_dir, file_name)

                # Download the file
                download_patch_file(download_url, save_path)

def main():
    """Main function to download all Organelle patches and store them by tag."""
    process_and_download_patches()

if __name__ == '__main__':
    main()

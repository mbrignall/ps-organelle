import argparse
import os
import requests
from dotenv import load_dotenv
import time
from requests.exceptions import ChunkedEncodingError, ConnectionError
from export_to_org import export_patches_to_org  # Import the Org export function

# Load environment variables
load_dotenv()

# Fetch the API token from .env
API_TOKEN = os.getenv('PATCHSTORAGE_API_TOKEN')

# API URLs
BASE_PATCHES_URL = 'https://patchstorage.com/api/beta/patches'
PATCH_DETAIL_URL_TEMPLATE = 'https://patchstorage.com/api/beta/patches/{patch_id}'

# Headers for API requests, including User-Agent
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (compatible; PatchstorageClient/1.0)'  # Set the User-Agent header
}

# Directory where patches will be saved
BASE_DOWNLOAD_DIR = 'patches'

# Function to fetch patches based on command-line flags
def fetch_patches(platform_id=154, category=None, tag=None):
    """Fetch patches for the Organelle platform with optional filtering by category or tag."""
    url = BASE_PATCHES_URL
    params = {
        'platforms': platform_id,
        'page': 1,
        'per_page': 100  # Adjust as needed
    }

    if category:
        params['categories'] = category
    if tag:
        params['tags'] = tag

    patches = []
    while True:
        try:
            response = requests.get(url, headers=HEADERS, params=params)
            if response.status_code == 403:
                print(f"Error: Received status code {response.status_code} - Forbidden")
                break
            if response.status_code != 200:
                print(f"Error: Received status code {response.status_code} from {url}")
                break

            data = response.json()

            if isinstance(data, list):
                patches.extend(data)
            else:
                print(f"Unexpected response format: {data}")
                break

            if len(data) < params['per_page']:
                break
            params['page'] += 1

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            break

    return patches

# Function to fetch detailed patch info
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

# Function to download patch files
def download_patch_file(download_url, save_path, retries=3):
    attempt = 0
    while attempt < retries:
        try:
            print(f"Downloading {save_path} (Attempt {attempt + 1}/{retries})...")
            response = requests.get(download_url, headers=HEADERS, stream=True, timeout=10)

            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                print(f"Downloaded patch file {save_path}")
                return
            else:
                print(f"Failed to download patch file. Status code: {response.status_code}")
                break

        except (ChunkedEncodingError, ConnectionError, requests.exceptions.Timeout) as e:
            print(f"Download failed due to {type(e).__name__}: {e}")
            attempt += 1
            time.sleep(2)
            if attempt == retries:
                print(f"Failed to download {save_path} after {retries} attempts.")
                break

# Function to download and process patches
def process_and_download_patches(patches):
    for patch in patches:
        patch_id = patch['id']
        patch_title = patch['title']
        category = patch['categories'][0]['slug'] if patch['categories'] else 'uncategorized'
        first_tag = patch['tags'][0]['slug'] if patch['tags'] else 'untagged'

        category_dir = os.path.join(BASE_DOWNLOAD_DIR, category)
        os.makedirs(category_dir, exist_ok=True)

        tag_dir = os.path.join(category_dir, first_tag)
        os.makedirs(tag_dir, exist_ok=True)

        patch_detail = fetch_patch_detail(patch_id)
        if patch_detail:
            for file_obj in patch_detail.get('files', []):
                download_url = file_obj['url']
                file_name = file_obj['filename']
                save_path = os.path.join(tag_dir, file_name)
                download_patch_file(download_url, save_path)

# CLI setup with argparse
def main():
    parser = argparse.ArgumentParser(description="Download and export Organelle patches from Patchstorage")
    
    parser.add_argument('--full', action='store_true', help="Fetch all patches from the Organelle platform")
    parser.add_argument('--category', type=str, help="Filter patches by category (e.g., Synthesizer, Effect)")
    parser.add_argument('--tag', type=str, help="Filter patches by tag")
    parser.add_argument('--org', action='store_true', help="Export patches to Org-mode format")
    
    args = parser.parse_args()

    if args.full:
        print("Fetching all patches for Organelle platform...")
        patches = fetch_patches()
    elif args.category:
        print(f"Fetching patches in the category: {args.category}")
        patches = fetch_patches(category=args.category)
    elif args.tag:
        print(f"Fetching patches with the tag: {args.tag}")
        patches = fetch_patches(tag=args.tag)
    else:
        print("No valid option provided, fetching all patches by default...")
        patches = fetch_patches()

    if args.org:
        print("Exporting patches to Org mode...")
        export_patches_to_org(patches)
        print("Patches exported to patches.org")
    else:
        print("Downloading patches...")
        process_and_download_patches(patches)

if __name__ == '__main__':
    main()

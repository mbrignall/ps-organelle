import re
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch the API token from .env
API_TOKEN = os.getenv('PATCHSTORAGE_API_TOKEN')

# API URL
BASE_PATCHES_URL = 'https://patchstorage.com/api/beta'
PATCH_DETAIL_URL_TEMPLATE = 'https://patchstorage.com/api/beta/patches/{patch_id}'

# Headers for API requests, including User-Agent
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (compatible; PatchstorageClient/1.0)'  # Set the User-Agent header
}

# Directory to save the org file
OUTPUT_ORG_FILE = 'patches.org'

# Function to sanitize tags (remove spaces, replace special characters)
def sanitize_tag(tag):
    """Sanitize a tag by removing spaces and replacing special characters."""
    sanitized_tag = re.sub(r'[^a-zA-Z0-9]', '_', tag.replace(' ', ''))
    return sanitized_tag

# Function to sanitize headers (replace underscores with spaces)
def sanitize_header(text):
    """Sanitize text for org-mode headers by replacing underscores with spaces."""
    return text.replace('_', ' ')

# Function to fetch patches from the API
def fetch_patches(platform_id=154):
    """Fetches patches for the Organelle platform using the beta API."""
    url = f'{BASE_PATCHES_URL}/patches'
    params = {
        'platforms': platform_id,
        'page': 1,
        'per_page': 100  # Adjust as needed
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

# Function to write the patches data into an org-mode file
def export_patches_to_org(patches):
    """Export patches data from the API into an org-mode file."""
    max_title_length = 50  # Define a max length for the title before the tags start
    with open(OUTPUT_ORG_FILE, 'w') as f:
        f.write('#+TITLE: Patchstorage Patches\n\n')

        # Dictionary to store patches by category
        patches_by_category = {}

        # Organize patches by category
        for patch in patches:
            categories = patch['categories']
            if categories:
                category_name = sanitize_header(categories[0]['name'])  # Sanitize category
            else:
                category_name = 'Uncategorized'

            if category_name not in patches_by_category:
                patches_by_category[category_name] = []
            
            patches_by_category[category_name].append(patch)

        # Write patches to org file, grouped by category
        for category, patches in patches_by_category.items():
            f.write(f'* {category}\n')  # Header 1 for category

            for patch in patches:
                title = sanitize_header(patch['title'])  # Sanitize title for header
                author = patch['author']['name']
                # Sanitize tags (remove spaces, hyphens, and other special characters)
                tags = ':' + ':'.join([sanitize_tag(tag['name']) for tag in patch['tags']]) + ':'
                description = patch['excerpt']
                url = patch['url']

                # Calculate padding to align the tags
                padding = max_title_length - len(title)
                if padding < 1:
                    padding = 1
                padded_title = title + ' ' * padding  # Add padding between title and tags

                # Write patch details
                f.write(f'** {padded_title}{tags}\n')  # Header 2 with org-mode tags aligned
                f.write(f'- Author: {author}\n')
                f.write(f'- URL: {url}\n')
                f.write(f'- Description:\n  {description}\n\n')

def main():
    """Main function to fetch patches and export them to an org-mode file."""
    patches = fetch_patches()
    export_patches_to_org(patches)
    print(f"Exported {len(patches)} patches to {OUTPUT_ORG_FILE}")

if __name__ == '__main__':
    main()

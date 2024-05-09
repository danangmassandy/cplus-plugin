import os
import math
import json
import requests
import concurrent.futures

from ..utils import (
    log
)

BASE_URL = 'http://0.0.0.0:9999/api/v1'
API_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3MTUyMzkyMDQsImlhdCI6MTcxNTE1MjgwNCwibmJmIjoxNzE1MTUyODA0LCJpZGVudGl0eSI6IjQzMDBmZDdiNGZmYzRjMGQ5YmViYzExOTNkOGQzMzM5In0.44K5SuNbkcFz38yIHubseUbOo5G8-Hlhy0QVP7k0ODM'
FILE_PATH = '/home/web/media/test/Final_Avoided_Wetland_priority_norm.tif'
FILES_TO_UPLOAD = {
    FILE_PATH: 'ncs_pathway'
}
# chunk_size must be greater than 5MB, for now use 100MB
CHUNK_SIZE = 100 * 1024 * 1024


final_result = []

def start_upload(fp, component_type):
    file_size = os.stat(fp).st_size
    payload = {
        "layer_type": 0,
        # "component_type": "ncs_pathway",
        "component_type": component_type,
        "privacy_type": "private",
        "name": os.path.basename(fp),
        "size": file_size,
        "number_of_parts": math.ceil(file_size / CHUNK_SIZE)
    }
    url = f'{BASE_URL}/layer/upload/start/'
    log(f'***REQUEST: {url}')
    log(json.dumps(payload))
    response = requests.post(url, json=payload, headers={
            "Authorization": f"Bearer {API_TOKEN}",
    })
    result = response.json()
    # log(json.dumps(result))
    return result


def upload_part(signed_url, file_data, file_part_number, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            # ref: https://github.com/aws-samples/amazon-s3-multipart-upload-
            # transfer-acceleration/blob/main/frontendV2/src/utils/upload.js#L119
            if signed_url.startswith('http://'):
                response = requests.put(signed_url, data=file_data, headers={'Host': 'minio:9000'})
            else:
                response = requests.put(signed_url, data=file_data)
            log(json.dumps(dict(response.headers)))
            return {
                'part_number': file_part_number,
                'etag': response.headers['ETag']
            }
            return response
        except requests.exceptions.RequestException as e:
            log(f"Request failed: {e}")
            retries += 1
            if retries < max_retries:
                # Calculate the exponential backoff delay
                delay = 2 ** retries
                log(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                log("Max retries exceeded.")
                raise


# def upload_part(signed_url, file_data, file_part_number):
#     # TODO: use exponential backoff for retry
#     # ref: https://github.com/aws-samples/amazon-s3-multipart-upload-
#     # transfer-acceleration/blob/main/frontendV2/src/utils/upload.js#L119
#     res = requests.put(signed_url, data=file_data)
#     return {
#         'part_number': file_part_number,
#         'etag': res.headers['ETag']
#     }


def finish_upload(layer_uuid, upload_id, items):
    payload = {
        "multipart_upload_id": upload_id,
        "items": items
    }
    url = f'{BASE_URL}/layer/upload/{layer_uuid}/finish/'
    log(f'***REQUEST: {url}')
    log(json.dumps(payload))
    response = requests.post(url, json=payload, headers={
            "Authorization": f"Bearer {API_TOKEN}",
    })
    result = response.json()
    log(json.dumps(result))
    final_result.append(result)
    return result


def run_upload(file_path, component_type):
    # start upload
    upload_params = start_upload(file_path, component_type)
    upload_id = upload_params['multipart_upload_id']
    layer_uuid = upload_params['uuid']
    upload_urls = upload_params['upload_urls']
    # do upload by chunks
    items = []
    idx = 0
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            url_item = upload_urls[idx]
            log(f"starting upload part {url_item['part_number']}")
            part_item = upload_part(
                url_item['url'], chunk, url_item['part_number'])
            items.append(part_item)
            log(f"finished upload part {url_item['part_number']}")
            idx += 1
    log(f'***Total upload_urls: {len(upload_urls)}')
    log(f'***Total chunks: {idx}')
    # finish upload
    finish_upload(layer_uuid, upload_id, items)


def run_parallel_upload(upload_dict):
    file_paths = list(upload_dict.keys())
    component_types = list(upload_dict.values())

    with concurrent.futures.ThreadPoolExecutor(
            max_workers=3 if os.cpu_count() > 3 else 1
    ) as executor:
        executor.map(
            run_upload,
            file_paths,
            component_types
        )
    return final_result




def main():
    run_parallel_upload(FILES_TO_UPLOAD)


if __name__ == "__main__":
    main()

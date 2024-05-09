import json

import requests

from ..utils import (
    log
)

BASE_URL = 'http://0.0.0.0:9999/api/v1'
# chunk_size must be greater than 5MB, for now use 100MB
CHUNK_SIZE = 100 * 1024 * 1024


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

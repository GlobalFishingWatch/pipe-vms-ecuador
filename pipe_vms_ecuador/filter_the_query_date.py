"""
Filters from original Ecuador API output the query date.
The data comming from the API brings lot of date in one request
This utility will filter the query date that we need to upload in the DB.

This script will do:
1- Read the file downloaded from the Ecuatorian API.
2- Decompress the GZIP, read and filter the query date.
3- Compress again with suffix `filtered`.
"""

from datetime import datetime

from google.cloud import storage

from shutil import rmtree

from pathlib import Path

import argparse, gzip, json, os, re, time


# FORMATS
FORMAT_DT = '%Y-%m-%d'

# FOLDER
FILTER_PATH = "filtered"

def copy_blob(gcs_path, blob_name, original_file):
    """
    Copies a blob from one bucket to another with a new name.
    :param gcs_path: The gcs path to the original file.
    :type gcs_path: str
    :param blob_name: The name of the file.
    :type blob_name: str
    :param original_file: The file to download.
    :type original_file: str
    """
    storage_client = storage.Client()

    prefix = ''
    bucket_name = ''
    if gcs_path.startswith("gs:"):
        bucket_name = re.search('(?<=gs://)[^/]*', gcs_path).group(0)
        prefix = re.search('(?<=gs://)[^/]*/(.*)', gcs_path).group(1)

    print(f'bucket {bucket_name}, prefix: {prefix}')

    source_bucket = storage_client.bucket(bucket_name)
    source_blob = source_bucket.blob(f'{prefix}{blob_name}')

    source_blob.download_to_filename(original_file.name)


def create_directory(name):
    """
    Creates a directory in the filesystem.
    :param name: The name of the directory.
    :type name: str
    """
    if not os.path.exists(name):
        os.makedirs(name)

def gcs_transfer(pattern_file, gcs_path):
    """
    Uploads the files from file system to a GCS destination.
    :param pattern_file: The pattern file without wildcard.
    :type pattern_file: str
    :param gcs_path: The absolute path of GCS.
    :type gcs_path: str
    """
    storage_client = storage.Client()
    gcs_search = re.search('gs://([^/]*)/(.*)', gcs_path)
    bucket = storage_client.bucket(gcs_search.group(1))
    pattern_path = Path(pattern_file)
    for filename in pattern_path.parent.glob(pattern_path.name + '*'):
        blob = bucket.blob(gcs_search.group(2) + filename.name)
        blob.upload_from_filename(filename)
        print("File from file system <{}> uploaded to <{}>.".format(filename, gcs_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Filter the content by query date and generate a new GZIP to compress.')
    parser.add_argument('-d','--query_date', help='The date to be queried. Expects a str in format YYYY-MM-DD',
                        required=True)
    parser.add_argument('-i','--input_directory', help='The GCS directory'
                        'where the data is stored. Expected with slash at'
                        'the end.', required=True)
    parser.add_argument('-o','--output_directory', help='The GCS directory'
                        'where the data will be stored. Expected with slash at'
                        'the end.', required=True)
    args = parser.parse_args()
    query_date = datetime.strptime(args.query_date, FORMAT_DT)
    input_directory= args.input_directory
    output_directory= args.output_directory

    original_name = f'{query_date.strftime(FORMAT_DT)}.json.gz'
    filtered_name = f'{query_date.strftime(FORMAT_DT)}_filtered.json.gz'

    start_time = time.time()

    create_directory(FILTER_PATH)

    # Copies the original GZIP file to local.
    print('Copies the original GZIP file to local.')
    with open(f'{FILTER_PATH}/{original_name}', 'wb') as original_file:
        copy_blob(input_directory, original_name, original_file)

    # Decompresses the GZIP.
    print(f'Decompresses the original GZIP file {FILTER_PATH}/{original_name}')
    print(f'Filters only by query date {query_date.strftime(FORMAT_DT)}')
    out=[]
    with gzip.open(f'{FILTER_PATH}/{original_name}','rb') as original:
        for line in original:
            content = json.loads(line.decode())
            if content['fechaqth'].startswith(f'{query_date.strftime(FORMAT_DT)}'):
                out.append(content)

    # Compress
    print(f'Saves the filtered file {FILTER_PATH}/{filtered_name} and compress with GZIP.')
    with gzip.open(f'{FILTER_PATH}/{filtered_name}','wt', compresslevel=9) as filtered:
        for message in out:
            json.dump(message, filtered)
            filtered.write("\n")

    # Saves to GCS
    gcs_transfer(f'{FILTER_PATH}/{filtered_name}', output_directory)

    rmtree(FILTER_PATH)

    ### ALL DONE
    print("All done, you can find the output file here: {0}".format(output_directory))
    print("Execution time {0} minutes".format((time.time()-start_time)/60))

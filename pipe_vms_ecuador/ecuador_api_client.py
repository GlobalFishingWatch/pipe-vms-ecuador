from google.cloud import storage

from pathlib import Path

import argparse, requests, json, os, re, time


# ECUADOR ENDPOINT
ENDPOINT = 'http://190.95.163.5:8080/GeoPosicionFinal/webresources/entidadestabla.nvqths/'

# FORMATS
FORMAT_DT = '%Y-%m-%d'

# FOLDER
DOWNLOAD_PATH = "download"

def query_data(query_date, wait_time_between_api_calls):
    """
    Queries the Ecuador API.
    :param query_date: The date to be queried.
    :type query_date: str
    :param wait_time_between_api_calls: Time between API calls, seconds.
    :type wait_time_between_api_calls: int
    """
    ecuador_positions_date_url = ENDPOINT + query_date
    parameters={
    }
    headers = {
      'Accept': 'application/json'
    }
    positions_list_request = requests.get(ecuador_positions_date_url, data=parameters, headers=headers)
    print(positions_list_request.json())
    time.sleep(wait_time_between_api_calls)
    #TODO need to continue because cannot get response yet.


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
    print("All files from file system <{}> uploaded to <{}>.".format(pattern_file+'*', gcs_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download all positional data of Ecuador Vessels for a given day.')
    parser.add_argument('-d','--query_date', help='The date to be Queried.',
                        required=True)
    parser.add_argument('-o','--output_directory', help='The directory where'
                        'the data will be stored.', required=True)
    parser.add_argument('-wt','--wait_time_between_api_calls', help='Time
                        'between calls to their API for vessel positions. Measured in'
                        'seconds.', required=False, default=5.0, type=float)
    args = parser.parse_args()
    query_date = args.query_date
    output_directory= args.output_directory
    wait_time_between_api_calls = args.wait_time_between_api_calls
    file_path = "%s/ecuador_positions_%s" % (DOWNLOAD_PATH, query_date)

    start_time = time.time()

    create_directory(DOWNLOAD_PATH)

    # Executes the query
    query_data(query_date, wait_time_between_api_calls, file_path)

    # Saves to GCS
    gcs_json_path = '%s/ecuador_positions_%s' % (output_directory, query_date.strftime(FORMAT_DT))
    gcs_transfer(file_path, gcs_json_path)


    ### ALL DONE
    print("All done, you can find the output file here: {0}".format(output_directory))
    print("Execution time {0} minutes".format((time.time()-start_time)/60))

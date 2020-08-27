#!/usr/bin/env bash

THIS_SCRIPT_DIR="$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P  )"

display_usage() {
  echo "Available Commands"
  echo "  fetch_ecuador_vms_data        Download ECUADOR VMS data to GCS"
  echo "  load_ecuador_vms_data         Load ECUADOR VMS data from GCS to BQ"
}


if [[ $# -le 0 ]]
then
    display_usage
    exit 1
fi

case $1 in

  fetch_ecuador_vms_data)
    echo "Running python -m pipe_vms_ecuador.ecuador_api_client ${@:2}"
    python -m pipe_vms_ecuador.ecuador_api_client ${@:2}
    echo "Fetch DONE."
    ;;

  load_ecuador_vms_data)
    ${THIS_SCRIPT_DIR}/gcs2bq.sh "${@:2}"
    ;;

  *)
    display_usage
    exit 1
    ;;
esac

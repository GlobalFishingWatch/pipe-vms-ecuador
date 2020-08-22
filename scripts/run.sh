#!/usr/bin/env bash

display_usage() {
  echo "Available Commands"
  echo "  fetch_ecuador_vms_data        Download ECUADOR VMS data to GCS"
}


if [[ $# -le 0 ]]
then
    display_usage
    exit 1
fi

case $1 in

  fetch_ecuador_vms_data)
    python -m pipe_vms_ecuador.ecuador_api_client "${@:2}"
    ;;

  *)
    display_usage
    exit 1
    ;;
esac

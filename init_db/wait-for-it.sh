#!/usr/bin/env bash
# wait-for-it.sh

TIMEOUT=5
QUIET=0
PROTOCOL=tcp

while getopts ":t:q" option; do
    case "${option}" in
        t) TIMEOUT=${OPTARG} ;;
        q) QUIET=1 ;;
    esac
done

shift $((OPTIND-1))

if [ $# -eq 0 ]; then
    echo "Usage: wait-for-it.sh [-t timeout] host:port"
    exit 1
fi

host=$(echo $1 | cut -d : -f 1)
port=$(echo $1 | cut -d : -f 2)

if ! [[ $port =~ ^[0-9]+$ ]]; then
    echo "Invalid port"
    exit 1
fi

if [[ $QUIET -eq 1 ]]; then
    exec 3>&2
    exec 2>/dev/null
fi

echo "Waiting for $host:$port... "

i=0
until nc -z -w 1 $host $port; do
    i=$((i+1))
    if [[ $i -ge $TIMEOUT ]]; then
        echo "timeout"
        exit 1
    fi
    sleep 1
done

echo "done"

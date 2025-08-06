#!/bin/bash

sleep_for_port() {
    local port=$1
    while true; do
        output=$(netstat -anpe | grep "$port")
        if [[ -n "$output" ]]; then
            echo "Found $port in command output"
            break
        fi
        sleep 1
    done
}


JOERN_PORT=8000
SERVER_PORT=9000

joern --server --server-port $JOERN_PORT &> /crs_scratch/server.log 2>&1 &

sleep_for_port $JOERN_PORT

run-joern.py &

sleep_for_port $SERVER_PORT

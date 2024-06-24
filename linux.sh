#!/bin/bash

set -e

# Function to get proxies
get_proxies() {
    if [ ! -f "proxies.txt" ]; then
        echo "Downloading proxies..."
        curl -s "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&limit=5000" -o proxies.txt
    fi
}

# Function to get user agents
get_user_agents() {
    if [ ! -f "useragents.txt" ]; then
        echo "User agents file not found!"
        exit 1
    fi
    mapfile -t user_agents < useragents.txt
}

# Function to test a proxy
test_proxy() {
    local proxy=$1
    local user_agent=$2
    response=$(curl -s --proxy "$proxy" -A "$user_agent" --max-time 3 -o /dev/null -w "%{http_code}" https://bing.com)
    if [ "$response" == "200" ]; then
        echo "$proxy"
    fi
}

# Function to filter working proxies
filter_working_proxies() {
    local user_agent="${user_agents[$RANDOM % ${#user_agents[@]}]}"
    while read -r proxy; do
        test_proxy "$proxy" "$user_agent" &
    done < proxies.txt
    wait
}

# Function to perform Google search
google_search() {
    local query=$1
    local user_agent=$2
    local proxy=$3
    curl -s --proxy "$proxy" -A "$user_agent" --max-time 10 "https://www.google.com/search?q=$query" | grep -oP '(?<=<a href="/url\?q=).*?(?=&amp;)'
}

# Function to search for a dork
search_dork() {
    local dork=$1
    local retries=0
    local max_retries=3
    local backoff_factor=1.0

    echo "Searching for dork: $dork"
    while [ $retries -le $max_retries ]; do
        proxy="${proxies[$RANDOM % ${#proxies[@]}]}"
        user_agent="${user_agents[$RANDOM % ${#user_agents[@]}]}"
        results=$(google_search "$dork" "$user_agent" "$proxy")
        
        if [ -n "$results" ]; then
            echo "$results" | head -n 20 > "results/${dork}_results.txt"
            echo "Saved top 20 results for dork '$dork'"
            break
        fi

        retries=$((retries + 1))
        sleep "$(echo "$backoff_factor * (2 ^ (retries - 1)) + ($RANDOM % 5) + 1" | bc)"
    done
}

# Main script execution
main() {
    verbose=0
    while getopts ":v" opt; do
        case ${opt} in
            v ) verbose=1
                ;;
            \? ) echo "Usage: cmd [-v]"
                ;;
        esac
    done

    get_proxies
    get_user_agents

    mapfile -t proxies < <(filter_working_proxies)
    mkdir -p results

    mapfile -t dorks < dorks.txt
    for dork in "${dorks[@]}"; do
        search_dork "$dork" &
    done
    wait
}

main "$@"

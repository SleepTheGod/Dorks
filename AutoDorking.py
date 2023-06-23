#!/usr/bin/env python3

import os
import time
import random
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import requests
from termcolor import colored


def get_proxies():
    proxies = []
    if not os.path.exists("proxies.txt"):
        url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&limit=5000"
        proxies = requests.get(url).text.split("\n")
        with open("proxies.txt", "w") as f:
            f.write("\n".join(proxies))
    else:
        with open("proxies.txt", "r") as f:
            proxies = f.read().split("\n")
    return proxies


def test_proxy(proxy, user_agent, verbose):
    test_url = "https://bing.com"
    headers = {"User-Agent": user_agent}
    try:
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        response = requests.get(test_url, headers=headers, proxies=proxies, timeout=3)
        print(colored(f"Scraping good proxies...", "blue"))
        if response.status_code == 200:
            print(colored(f"Good proxy found: {proxy}", "green"))
            return True
    except requests.exceptions.ConnectTimeout:
        if verbose:
            print(colored(f"Connection timeout for proxy: {proxy}", "red"))
    except requests.exceptions.ProxyError:
        if verbose:
            print(colored(f"Proxy error for proxy: {proxy}", "red"))
    except requests.exceptions.RequestException as e:
        if verbose:
            print(colored(f"Request exception for proxy: {proxy}, error: {e}", "red"))
    return False


def filter_working_proxies(proxies, user_agents, verbose):
    working_proxies = []
    user_agent = random.choice(user_agents)
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures_to_proxies = {executor.submit(test_proxy, proxy, user_agent, verbose): proxy for proxy in proxies}
        for future in as_completed(futures_to_proxies):
            if future.result():
                working_proxies.append(futures_to_proxies[future])
    return working_proxies


def get_user_agents():
    with open("useragents.txt", "r") as f:
        return f.read().split("\n")


def google_search(query, user_agent, proxy):
    url = f"https://www.google.com/search?q={query}"
    headers = {"User-Agent": user_agent}
    proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    return [result["href"] for result in soup.select(".yuRUbf a")]
       

def search_dork(dork, proxies, user_agents, verbose, max_retries=3, backoff_factor=1.0):
    print(colored(f"Searching for dork: {dork}", "yellow"))

    def try_search_dork(dork, proxy, user_agent):
        try:
            results = google_search(dork, user_agent, proxy)
            return results
        except requests.exceptions.RequestException as e:
            if verbose:
                print(colored(f"Error with proxy {proxy}: {e}, rotating proxy...", "magenta"))
            return None

    retries = 0
    while retries <= max_retries:
        proxy = random.choice(proxies)
        user_agent = random.choice(user_agents)
        results = try_search_dork(dork, proxy, user_agent)

        if results is not None:
            if results:
                with open(f"results/{dork}_results.txt", "w") as f:
                    f.write("\n".join(results[:20]))
                print(colored(f"Saved top 20 results for dork '{dork}'", "green"))
            else:
                print(colored(f"No results found for dork '{dork}'", "red"))
            break

        retries += 1
        time.sleep(backoff_factor * (2 ** (retries - 1)) + random.uniform(1, 5))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Display errors with proxies.", action="store_true")
    args = parser.parse_args()

    dorks = []
    with open("dorks.txt", "r") as f:
        dorks = f.read().split("\n")

    user_agents = get_user_agents()
    proxies = filter_working_proxies(get_proxies(), user_agents, args.verbose)

    if not os.path.exists("results"):
        os.makedirs("results")

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(search_dork, dork, proxies, user_agents, args.verbose): dork for dork in dorks}
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()

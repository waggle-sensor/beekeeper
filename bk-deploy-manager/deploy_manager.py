#!/usr/bin/env python3

import datetime
import logging
import os
import sys
import time

import dateutil.parser
import requests

logging.basicConfig(level=logging.INFO)

BEEKEEPER_URL = os.getenv("BEEKEEPER_URL", "http://localhost:5000")


# example input 2021-11-19T02:07:22
# returns datetime.datetime
def parseTime(timestamp):
    # dateutil.parser.isoparse('2008-09-03T20:56:35.450686')
    return dateutil.parser.isoparse(timestamp)


def get_candidates():

    if BEEKEEPER_URL == "":
        logging.error(f"BEEKEEPER_URL not defined")
        sys.exit(1)

    logging.info(f"BEEKEEPER_URL: {BEEKEEPER_URL}")
    url = f"{BEEKEEPER_URL}/state"
    logging.info(f"url: {url}")

    try:
        resp = requests.get(url)
    except Exception as e:
        raise Exception(f"GET request to {url} failed: {str(e)}")

    if resp.status_code != 200:
        raise Exception(f"status_code: {resp.status_code} body: {resp.text}")

    nodes = resp.json()

    candidates = []

    if not "data" in nodes:
        raise Exception("Field data missing")

    for n in nodes["data"]:
        node_id = n["id"]
        registration_event = n.get("registration_event")
        wes_deploy_event = n.get("wes_deploy_event")
        # print("id: "+node_id)
        # print("wes_deploy_event: "+n["wes_deploy_event"])
        if registration_event in ["", None]:
            logging.info("node %s is not registered", node_id)
            continue

        if n.get("beehive") in ["", None]:
            logging.info(f"node {node_id} does not belong to a beehive")
            continue

        if wes_deploy_event in ["", None] or parseTime(registration_event) >= parseTime(wes_deploy_event):
            logging.info(
                f"scheduling node {node_id} for wes deployment (reason: no previous deployment or re-registered node)"
            )
            candidates.append(n)
            continue

        logging.info(f"node {node_id} needs no deployment")

    return candidates


def try_wes_deployment(candidates):
    success_count = 0

    for candidate in candidates:
        try:
            deploy_wes_to_candidate(candidate)
            success_count += 1
        except KeyboardInterrupt:
            return
        except Exception:
            logging.exception("deploy_wes_to_candidate failed")
        time.sleep(2)

    logging.info(f"{success_count} out of {len(candidates)} successful.")
    logging.info("done")


def deploy_wes_to_candidate(candidate):
    node_id = candidate["id"]
    url = f"{BEEKEEPER_URL}/node/{node_id}"
    resp = requests.post(url, json={"deploy_wes": True})
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise ValueError(f"Something went wrong: url: {url} status_code: {resp.status_code} body: {resp.text}")


def main():
    logging.info("Starting...")
    while True:

        candidates = []
        try:
            candidates = get_candidates()
        except Exception as e:
            logging.error(f"error: get_candidates returned: {str(e)}")

        if len(candidates) == 0:
            logging.info("no candidates for wes deployment found")
        else:
            logging.info("candidates:")
            logging.info(candidates)
            try_wes_deployment(candidates)

        logging.info("waiting 5 minutes...")
        time.sleep(5 * 60)


if __name__ == "__main__":
    main()

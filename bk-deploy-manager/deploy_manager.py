#!/usr/bin/env python3
import datetime
import logging
import os
import time
import dateutil.parser
import requests
from datetime import datetime, timedelta

BEEKEEPER_URL = os.getenv("BEEKEEPER_URL", "http://localhost:5000")
BEEKEEPER_RENEW_DAYS = int(os.getenv("BEEKEEPER_RENEW_DAYS", "7"))


# example input 2021-11-19T02:07:22
# returns datetime.datetime
def parseTime(s: str):
    if s in [None, ""]:
        return None
    # dateutil.parser.isoparse('2008-09-03T20:56:35.450686')
    return dateutil.parser.isoparse(s)


def age(t: datetime) -> timedelta:
    return datetime.now() - t


def get_node_list_from_beekeeper():
    logging.info("BEEKEEPER_URL: %s", BEEKEEPER_URL)
    url = f"{BEEKEEPER_URL}/state"
    logging.info("url: %s", url)
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()["data"]


def get_deploy_wes_candidates():
    nodes = get_node_list_from_beekeeper()

    candidates = []

    for node in nodes:
        registration_time = parseTime(node.get("registration_event"))
        wes_deploy_time = parseTime(node.get("wes_deploy_event"))

        if registration_time is None:
            logging.info("node %s is not registered", node["id"])
        elif node.get("beehive") in ["", None]:
            logging.info("node %s does not belong to a beehive", node["id"])
        elif wes_deploy_time is None:
            logging.info("scheduling node %s for wes deployment: no existing deployment", node["id"])
            candidates.append((node, False))
        elif registration_time >= wes_deploy_time:
            logging.info("scheduling node %s for wes deployment: node reregistered", node["id"])
            candidates.append((node, False))
        elif age(wes_deploy_time) >= timedelta(days=BEEKEEPER_RENEW_DAYS):
            logging.info("scheduling node %s for wes deployment: renewing node credentials", node["id"])
            candidates.append((node, True))
        else:
            logging.info("node %s needs no deployment", node["id"])

    return candidates


def try_wes_deployment(candidates):
    if len(candidates) == 0:
        logging.info("no candidates required deployment")
        return

    success_count = 0

    for candidate, force in candidates:
        try:
            deploy_wes_to_candidate(candidate, force=force)
            success_count += 1
        except KeyboardInterrupt:
            return
        except Exception:
            logging.exception("deploy_wes_to_candidate failed")
        time.sleep(2)

    logging.info(f"{success_count} out of {len(candidates)} successful.")
    logging.info("done")


def deploy_wes_to_candidate(candidate, force):
    node_id = candidate["id"]

    if force:
        url = f"{BEEKEEPER_URL}/node/{node_id}?force=true"
    else:
        url = f"{BEEKEEPER_URL}/node/{node_id}"

    resp = requests.post(url, json={"deploy_wes": True})
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise ValueError(f"Something went wrong: url: {url} status_code: {resp.status_code} body: {resp.text}")


def main():
    logging.basicConfig(level=logging.INFO)

    logging.info("Starting...")

    while True:
        try:
            candidates = get_deploy_wes_candidates()
        except Exception:
            logging.exception("get_deploy_wes_candidates raised an exception. will retry in 10s")
            time.sleep(10)
            continue

        try_wes_deployment(candidates)

        logging.info("done. will recheck in 5min...")
        time.sleep(5*60)


if __name__ == "__main__":
    main()

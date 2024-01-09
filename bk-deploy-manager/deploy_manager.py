#!/usr/bin/env python3

import argparse
import datetime
import logging
import os
import sys
import time

import dateutil.parser
import requests
from dataclasses import dataclass
from typing import Optional


@dataclass
class Node:
    id: str
    beehive: Optional[str]
    registered_at: Optional[datetime.datetime]
    deployed_wes_at: Optional[datetime.datetime]


@dataclass
class Candidate:
    node: dict
    renew_credentials: bool


BEEKEEPER_URL = os.getenv("BEEKEEPER_URL", "http://localhost:5000")


# example input 2021-11-19T02:07:22
# returns datetime.datetime
def parse_datetime(timestamp: Optional[str]) -> Optional[datetime.datetime]:
    if timestamp == None:
        return None
    if timestamp == "":
        return None
    # dateutil.parser.isoparse('2008-09-03T20:56:35.450686')
    return dateutil.parser.isoparse(timestamp)


def get_nodes() -> list[Node]:
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

    items = resp.json()["data"]

    nodes = []

    for item in items:
        node_id = item["id"]
        beehive = item.get("beehive")
        if beehive == "":
            beehive = None
        registered_at = parse_datetime(item.get("registration_event"))
        deployed_wes_at = parse_datetime(item.get("wes_deploy_event"))
        nodes.append(
            Node(
                id=node_id,
                beehive=beehive,
                registered_at=registered_at,
                deployed_wes_at=deployed_wes_at,
            )
        )

    return nodes


def get_candidates() -> list[Candidate]:
    nodes = get_nodes()

    candidates = []

    for node in nodes:
        if node.registered_at is None:
            logging.info("node %s is not registered", node.id)
            continue

        if node.beehive is None:
            logging.info("node %s does not belong to a beehive", node.id)
            continue

        if node.deployed_wes_at is None:
            logging.info(
                "scheduling node %s for wes deployment (reason: no previous deployment)",
                node.id,
            )
            candidates.append(Candidate(node=node, renew_credentials=False))
            continue

        # reregistered nodes also need wes redeployed
        if node.registered_at >= node.deployed_wes_at:
            logging.info(
                "scheduling node %s for wes deployment (reason: node reregistered)",
                node.id,
            )
            candidates.append(Candidate(node=node, renew_credentials=True))
            continue

        # automatically redeploy with renewed credentials periodically
        deployed_wes_age = datetime.datetime.now() - node.deployed_wes_at

        if deployed_wes_age >= datetime.timedelta(days=90):
            logging.info(
                "scheduling node %s for wes deployment (reason: renew certificates - %d days old)",
                node.id,
                deployed_wes_age.days,
            )
            candidates.append(Candidate(node=node, renew_credentials=True))
            continue

        logging.info("node %s needs no deployment", node.id)

    # Q(sean) Is there ever a time where we wouldn't want to renew credentials? As long as
    # there's some rate limit on how fast we're generating them, it seems like just renewing
    # is a much simpler management strategy.

    return candidates


def try_wes_deployment(candidates: list[Candidate], dry_run: bool):
    success_count = 0

    for candidate in candidates:
        try:
            deploy_wes_to_candidate(candidate, dry_run)
            success_count += 1
        except KeyboardInterrupt:
            return
        except Exception:
            logging.exception("deploy_wes_to_candidate failed")

    logging.info(f"{success_count} out of {len(candidates)} successful.")
    logging.info("done")


def deploy_wes_to_candidate(candidate: Candidate, dry_run: bool):
    node = candidate.node

    if candidate.renew_credentials:
        logging.info("deploying to candidate %s with renewed credentials", node.id)
        url = f"{BEEKEEPER_URL}/node/{node.id}?force=true"
    else:
        logging.info("deploying to candidate %s", node.id)
        url = f"{BEEKEEPER_URL}/node/{node.id}"

    if dry_run:
        return

    resp = requests.post(url, json={"deploy_wes": True})
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise ValueError(
            f"Something went wrong: url: {url} status_code: {resp.status_code} body: {resp.text}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable verbose logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="get and log candidates but do not deploy wes",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )

    while True:
        candidates = []

        try:
            logging.info("getting candidates")
            candidates = get_candidates()
        except Exception as e:
            logging.error(f"error: get_candidates returned: {str(e)}")

        if len(candidates) == 0:
            logging.info("no candidates for wes deployment found")
        else:
            logging.info("deploying to candidates")
            try_wes_deployment(candidates, args.dry_run)

        logging.info("waiting 5 minutes...")
        time.sleep(5 * 60)


if __name__ == "__main__":
    main()

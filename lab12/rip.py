import argparse
import json
import random
from pathlib import Path

INFINITY = 16


def random_ip():
    return ".".join(str(random.randint(1, 255)) for _ in range(4))


def make_random_network(size):
    routers = []
    while len(routers) < size:
        ip = random_ip()
        if ip not in routers:
            routers.append(ip)

    links = []
    for i in range(1, size):
        links.append([routers[i - 1], routers[i]])

    for i in range(size):
        for j in range(i + 2, size):
            if random.random() < 0.3:
                links.append([routers[i], routers[j]])

    return routers, links


def read_link(link):
    if len(link) == 2:
        first, second = link
        return first, second, 1

    first, second, metric = link
    return first, second, metric


def read_config(path):
    with open(path, "r") as src:
        data = json.load(src)

    routers = data["routers"]
    links = data["links"]
    return routers, links


def make_neighbors(routers, links):
    neighbors = {router: {} for router in routers}

    for link in links:
        first, second, metric = read_link(link)
        if first not in neighbors or second not in neighbors:
            raise ValueError(f"unknown router in link {first} - {second}")

        neighbors[first][second] = metric
        neighbors[second][first] = metric

    return neighbors


def make_tables(routers, neighbors):
    tables = {}

    for router in routers:
        table = {}
        for dest in routers:
            if dest == router:
                table[dest] = {"next_hop": router, "metric": 0}
            elif dest in neighbors[router]:
                table[dest] = {
                    "next_hop": dest,
                    "metric": neighbors[router][dest],
                }
            else:
                table[dest] = {"next_hop": None, "metric": INFINITY}
        tables[router] = table

    return tables


def copy_tables(tables):
    result = {}
    for router, table in tables.items():
        result[router] = {}
        for dest, route in table.items():
            result[router][dest] = route.copy()
    return result


def update_table(router, neighbor, link_metric, old_tables, new_tables):
    changed = False

    for dest, route in old_tables[neighbor].items():
        if dest == router:
            continue

        metric = min(INFINITY, link_metric + route["metric"])
        current = new_tables[router][dest]

        if metric < current["metric"]:
            current["metric"] = metric
            current["next_hop"] = neighbor
            changed = True

    return changed


def run_rip(routers, neighbors):
    tables = make_tables(routers, neighbors)
    step = 0

    while True:
        step += 1
        old_tables = copy_tables(tables)
        changed = False

        for router in routers:
            for neighbor, metric in neighbors[router].items():
                changed = update_table(router, neighbor, metric, old_tables, tables)
            print_table(router, tables[router], step)

        if not changed:
            return tables, step


def print_table(router, table, step):
    print(f"Simulation step {step} of router {router}")
    print(
        f"{'[Source IP]':16s} {'[Destination IP]':19s} {'[Next Hop]':16s} {'[Metric]':>8s}"
    )

    for dest, route in table.items():
        if dest == router:
            continue

        next_hop = route["next_hop"] or "-"
        print(f"{router:16s} {dest:19s} {next_hop:16s} {route['metric']:8d}")

    print()


def main():
    default_config = Path(__file__).with_name("rip_config.json")

    parser = argparse.ArgumentParser(description="RIP protocol emulator")
    parser.add_argument("--config", default=default_config)
    parser.add_argument("--random", action="store_true")
    parser.add_argument("--size", type=int, default=5)
    args = parser.parse_args()

    try:
        if args.random:
            routers, links = make_random_network(args.size)
        else:
            routers, links = read_config(args.config)

        neighbors = make_neighbors(routers, links)
        tables, steps = run_rip(routers, neighbors)

        print()
        print(f"RIP simulation finished in {steps} steps")
    except Exception as error:
        print(f"error: {error}")


if __name__ == "__main__":
    main()

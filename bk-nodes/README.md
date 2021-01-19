
```bash
docker exec -ti beekeeper_bk-nodes_1 pytest -rP ./test_bk_nodes.py
```
`-rP` shows more output

debug db
```bash
docker exec -ti beekeeper_db_1 mysql -u root -p -D Beekeeper
```
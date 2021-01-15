
```bash
docker exec -ti beekeeper_bk-nodes_1 pytest  ./test_bk_nodes.py
```


debug db
```bash
docker exec -ti beekeeper_db_1 mysql -u root -p -D Beekeeper
```
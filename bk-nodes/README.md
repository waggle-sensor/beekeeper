
```bash
docker exec -ti beekeeper_bk-nodes_1 /bin/ash -c 'coverage run -m pytest -v  &&  coverage report -m'
```
`-rP` shows more output

debug db
```bash
docker exec -ti beekeeper_db_1 mysql -u root -p -D Beekeeper
```
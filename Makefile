all:

.PHONY: test
test:
	docker-compose exec bk-api pytest test_bk_api.py

.PHONY: svc-up
svc-up:
	./create-keys.sh init --nopassword
	./create-keys.sh cert untilforever forever
	docker-compose up -d --build

.PHONY: svc-down
svc-down:
	docker-compose down --volumes

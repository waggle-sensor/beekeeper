all:

.PHONY: test
test:
	docker-compose exec bk-api pytest test_bk_api.py

.PHONY: svc-up
svc-up:
	docker-compose up -d

.PHONY: svc-down
svc-down:
	docker-compose down

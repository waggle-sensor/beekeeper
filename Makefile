all:

.PHONY: test
test:
	./unit-tests.sh

.PHONY: svc-up
svc-up:
	./create-keys.sh init --nopassword
	./create-keys.sh cert untilforever forever
	docker-compose up -d --build

.PHONY: svc-down
svc-down:
	docker-compose down --volumes

all:

.PHONY: test
test:
	./unit-tests.sh

.PHONY: svc-up
svc-up:
	docker run --rm \
		-v ${PWD}:/workdir:rw \
		waggle/beekeeper-key-tools:latest \
		create-init-keys.sh -p -o beekeeper-keys
	docker run --rm \
		-v ${PWD}:/workdir:rw \
		waggle/beekeeper-key-tools:latest \
		create-key-cert.sh \
		-b my-beehive \
		-c beekeeper-keys/bk-ca/beekeeper_ca_key \
		-k beekeeper-keys/node-registration-key/registration \
		-o beekeeper-keys/registration_certs/untilforever
	docker-compose up -d --build

.PHONY: svc-down
svc-down:
	docker-compose down --volumes

import unittest
import requests


class TestBeekeeper(unittest.TestCase):

    def test_beehive_tls_credentials_GET(self):
        r = requests.get("http://127.0.0.1:5000/beehives/my-beehive/tls-credentials/rabbitmq")
        self.assertEqual(r.status_code, 405)

    def test_beehive_tls_credentials_POST(self):
        r = requests.post("http://127.0.0.1:5000/beehives/my-beehive/tls-credentials/rabbitmq")
        self.assertEqual(r.status_code, 200)
        resp = r.json()

        self.assertIn("certfile", resp)
        self.assertRegex(resp["certfile"], "^-----BEGIN CERTIFICATE-----(.|\n)+-----END CERTIFICATE-----\n$")

        self.assertIn("keyfile", resp)
        self.assertRegex(resp["keyfile"], "^-----BEGIN PRIVATE KEY-----(.|\n)+-----END PRIVATE KEY-----\n$")


if __name__ == "__main__":
    unittest.main()

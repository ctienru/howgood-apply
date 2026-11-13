"""Tests for submit.py. Run with: python3 -m unittest -v"""

import json
import unittest

from submit import encode_body, sign, validate_payload

VALID = {
    "name": "Test Person",
    "email": "test@example.com",
    "resume": "https://example.com/resume.pdf",
    "location": "Boston, MA, USA",
    "linkedin": "https://www.linkedin.com/in/example",
    "codeLink": "https://github.com/example/howgood-apply",
}


class SignTest(unittest.TestCase):
    def test_rfc4231_vector(self):
        # RFC 4231, test case 2
        self.assertEqual(
            sign(b"what do ya want for nothing?", b"Jefe"),
            "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843",
        )

    def test_signature_changes_with_body(self):
        self.assertNotEqual(sign(b'{"a":1}', b"key"), sign(b'{"a":2}', b"key"))


class EncodeBodyTest(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(json.loads(encode_body(VALID)), VALID)

    def test_compact_and_stable(self):
        self.assertEqual(encode_body({"a": 1, "b": "x"}), b'{"a":1,"b":"x"}')
        self.assertEqual(encode_body(VALID), encode_body(dict(VALID)))


class ValidatePayloadTest(unittest.TestCase):
    def test_valid_payload(self):
        self.assertEqual(validate_payload({**VALID, "yearsPython": 2, "notes": "hi"}), [])

    def test_not_an_object(self):
        self.assertEqual(validate_payload([]), ["Payload must be a JSON object."])

    def test_missing_and_blank_required(self):
        payload = dict(VALID)
        del payload["email"]
        payload["name"] = "  "
        errors = validate_payload(payload)
        self.assertIn("email must be a non-empty string.", errors)
        self.assertIn("name must be a non-empty string.", errors)

    def test_unknown_field(self):
        self.assertEqual(validate_payload({**VALID, "Notes": "x"}), ["Unknown fields: Notes"])

    def test_bool_is_not_an_int(self):
        errors = validate_payload({**VALID, "yearsDjango": True})
        self.assertEqual(errors, ["yearsDjango must be a non-negative integer."])

    def test_negative_years(self):
        errors = validate_payload({**VALID, "yearsPython": -1})
        self.assertEqual(errors, ["yearsPython must be a non-negative integer."])

    def test_url_must_be_https(self):
        errors = validate_payload({**VALID, "resume": "http://example.com/r.pdf"})
        self.assertEqual(errors, ["resume must start with https://."])


if __name__ == "__main__":
    unittest.main()

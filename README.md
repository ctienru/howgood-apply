# howgood-apply

A small script that submits an application to HowGood's signed application API.
It uses only the Python standard library.

## How it works

1. Read the application fields from a JSON file and validate them.
2. Serialize the payload once. The same bytes are signed and sent.
3. Sign the body with HMAC-SHA256 and send the hex digest in `X-HMAC-Signature`.
4. Treat `201 Created` as success. If no response arrives, check before resending,
   because the request may already have been received.

## Usage

```sh
cp application.example.json application.json   # fill in your details; this file is git-ignored
python3 -m unittest -v                         # run the tests
python3 submit.py application.json             # validate and print the body; nothing is sent
python3 submit.py application.json --send      # prompt for the signing key and send
```

The signing key is read with `getpass`, so it is not stored in the code or the shell history.

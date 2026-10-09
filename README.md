# Hackathon Game Day — Setup & Guidelines

Welcome to the Game Day. This document explains everything a team needs to get
set up, use Kiro Pro correctly, and create least-privilege AWS credentials to
call the GenAI services used in the challenge.

Read the **Shared Kiro Pro password** section first — it is the single most
common source of trouble on game day.

---

## 1. What each team receives

Every team is provisioned with its own set of credentials. They typically look
like this:

| Key | Example | Description |
| --- | --- | --- |
| `KiroProUsername` | `kiro` | Username for the Kiro Pro plan |
| `KiroProPassword` | `cTD&M92k2-vFZ>mlkkA^X146>Ex` | Password for the Kiro Pro plan |
| `KiroProStartURL` | `https://d-xxxxxxxxxx.awsapps.com/start` | IAM Identity Center start URL |
| `KiroProRegion` | `us-east-1` | Identity Center region |
| `KiroRDPConnectionURL` | `https://xxxx.cloudfront.net/?authToken=...#console` | One-click URL to the Kiro Ubuntu desktop |
| `KiroRDPCredentials` | `Username: ubuntu  Password: ...` | Desktop credentials (rarely needed; the one-click URL already signs you in) |

Keep these somewhere every teammate can reach them, but do not share them
outside your team.

---

## 2. ⚠️ Shared Kiro Pro password — read this

> **The Kiro Pro login is shared by the whole team.**
> There is **one** `KiroProUsername` / `KiroProPassword` per team, not one per
> person. Everyone on the team signs in with the same credentials.

What this means in practice:

- **Do not change the Kiro Pro password.** If any teammate changes it, it
  changes for **everyone** on the team. Anyone currently signed in — or who
  tries to sign in afterwards with the old password — will be locked out.
- If you are prompted to "set a new password" or "reset your password," **stop**
  and check with your team first. A reset affects all members.
- If the password *does* get changed by mistake, the whole team must switch to
  the new one. Communicate it immediately in your team channel.
- Treat the password as a shared team secret: don't paste it into public chats,
  screenshots, or commits.

If you are ever locked out and nobody changed the password, contact a game day
organizer rather than attempting a reset.

---

## 3. Getting started with Kiro

1. Open the **`KiroRDPConnectionURL`** in a browser tab. This signs you in to
   the Kiro Ubuntu desktop automatically (the `authToken` is in the URL).
2. Launch Kiro on the desktop.
3. When Kiro asks you to sign in to Kiro Pro, choose the **IAM Identity Center
   (SSO)** option and enter:
   - Start URL → `KiroProStartURL`
   - Region → `KiroProRegion`
   - Username → `KiroProUsername`
   - Password → `KiroProPassword`
4. Approve the device authorization in the browser if prompted.

You are now ready to build.

> Reminder: the `KiroRDPCredentials` (ubuntu / password) are rarely needed — the
> one-click URL already logs you into the desktop.

---

## 4. AWS credentials for GenAI services (least privilege)

For the challenge you'll call AWS GenAI and supporting services (Amazon Bedrock,
Transcribe, Textract, S3). To do that from code you need an **access key ID**
and **secret access key** (AK/SK).

**Create a dedicated IAM user for programmatic access.** Do not use root
credentials. The beginner-friendly, step-by-step guide — including prerequisites
(Kiro, AWS CLI, VS Code, Python) and a big warning about never committing
secrets — is in:

➡️ **[`docs/IAM_SETUP.md`](docs/IAM_SETUP.md)**

Quick summary of what that guide does:

1. Install the prerequisites (Kiro, AWS CLI, Python; VS Code is already on the
   workshop desktop).
2. Create an IAM user (programmatic access only).
3. Attach the AWS managed policies for Bedrock, Transcribe, Textract, and S3.
4. Generate the AK/SK and configure the AWS CLI / SDK with the keys.

> 🔒 **Never commit your AK/SK, `.env`, or the Kiro Pro password to any source
> repository.** A leaked key can be abused within seconds. See the warning at
> the top of `docs/IAM_SETUP.md`.

---

## 5. Testing the services

Once your AK/SK are configured, use the ready-made scripts in
**[`samples/`](samples/)** to confirm each service works before you start
building:

- `samples/s3_sample.py` — upload / list / download an object
- `samples/bedrock_sample.py` — invoke a foundation model
- `samples/transcribe_sample.py` — transcribe an audio file
- `samples/textract_sample.py` — extract text from a document/image

See **[`samples/README.md`](samples/README.md)** for setup and usage.

---

## 6. Rules of thumb

- One Kiro Pro login per team — **never change the password.**
- **Never commit secrets** (`.env`, AK/SK, passwords) to any repository — public
  or private.
- Delete your AK/SK and clean up resources when game day ends.
- Clean up S3 objects and any created resources when you're done.

Good luck, and have fun. 🚀

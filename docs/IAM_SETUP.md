# Setting up AWS credentials (AK/SK) for the GenAI services

This guide shows you how to create an AWS user with an **access key ID** +
**secret access key** (AK/SK) so your code can call the game day services:
Amazon Bedrock, Transcribe, Textract, and S3.

It is written for people who have **never used AWS IAM before**. We keep it
simple on purpose and use ready-made **AWS managed policies** instead of
hand-written permissions.

---

## 🔒 READ THIS FIRST — never commit your secrets

> # ⚠️ DO NOT COMMIT CREDENTIALS TO ANY SOURCE REPOSITORY ⚠️
>
> Your **access key ID**, **secret access key**, the `.env` file, and the
> **Kiro Pro password** are secrets.
>
> **Never** push them to GitHub, GitLab, Bitbucket, or any public or shared
> repository — not even a private one you might later make public.
>
> If a secret key is ever committed and pushed, treat it as **leaked**:
> AWS actively scans public repos, bots scrape them within seconds, and a
> leaked key can be used to run up huge bills on the account.
>
> **If you leak a key:** tell an organizer immediately and delete the key
> (see [Clean up](#4-clean-up-end-of-game-day)).
>
> The `.gitignore` in this project already excludes `.env` and key files — do
> not override it.

---

## 1. Prerequisites — install these first

You'll do most of the work on the **Kiro Ubuntu desktop** you were given (via
the `KiroRDPConnectionURL`). The tools below may already be present there; if
not, install them.

### Kiro
Kiro is the AI development environment you'll build in.
- Download: https://kiro.dev/downloads/
- Docs: https://kiro.dev/docs/
- Sign in using your team's IAM Identity Center credentials — see the main
  [`../README.md`](../README.md) (sections 2 and 3). **One shared login per
  team; never change the password.**

> ⚠️ **The Kiro Pro licence is shared across the whole AWS account.** There is
> **one** Kiro Pro user per account, so a team of 4 people in the same account
> all share that single Kiro user. Changing its password changes it for
> everyone. Coordinate as a team and never reset it.

### AWS CLI (v2)
The command-line tool used to configure credentials and run the samples.
- Install guide (all OSes): https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- Direct downloads:
  - Windows: https://awscli.amazonaws.com/AWSCLIV2.msi
  - macOS: https://awscli.amazonaws.com/AWSCLIV2.pkg
  - Linux (x86_64):
    ```bash
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip && sudo ./aws/install
    ```
- Verify it works:
  ```bash
  aws --version
  ```

### A code editor — VS Code
A **VS Code** editor is already available in a couple of places, so you don't
need to install one:
- On the **Kiro Ubuntu desktop** / workshop console — just open it.
- As a **browser-based VS Code** served from the AWS workshop console (AWS
  commonly provides a web IDE you open straight from a browser tab — no install).

If you'd rather install your own copy: https://code.visualstudio.com/download

### Python 3.9+
Needed to run the sample scripts in [`../samples/`](../samples/).
- Download: https://www.python.org/downloads/
- Verify:
  ```bash
  python --version
  ```

---

## 2. Create the IAM user and attach permissions

Because this is a game day and you may not know IAM, we attach **AWS managed
policies** — pre-built permission sets maintained by AWS. They are more
permissive than a hand-tuned policy, but they are simple and reliable, which is
what we want here.

> These policies are broad on purpose. That is exactly why the
> **"never commit your secrets"** warning above matters so much — a broad key
> that leaks is a big problem. Keep it safe and delete it at the end.

### The managed policies we'll attach

| Managed policy | What it covers |
| --- | --- |
| `AmazonBedrockFullAccess` | Amazon Bedrock (list/invoke models, etc.) |
| `AmazonTranscribeFullAccess` | Amazon Transcribe (speech → text) |
| `AmazonTextractFullAccess` | Amazon Textract (document → text) |
| `AmazonS3FullAccess` | Amazon S3 (buckets & objects) |

> **Need another service?** You can attach **any relevant AWS managed policy**
> the same way (e.g. `AmazonRekognitionFullAccess`, `TranslateFullAccess`,
> `ComprehendFullAccess`, `AmazonPollyFullAccess`). Search for the service name
> in the policy list and attach it.
>
> **Avoid `AdministratorAccess` if you possibly can.** It grants everything,
> including the ability to run up large bills or delete the account's resources,
> so a leaked admin key is the worst case. Attach the specific service policies
> you actually need instead.

### Option A — AWS Console (easiest, recommended)

1. Open the **IAM** service in the AWS Console (search "IAM" in the top bar).
2. Go to **Users → Create user**.
3. **User name:** `gameday-user`. Click **Next**.
   - Leave *"Provide user access to the AWS Management Console"* **unchecked** —
     we only need programmatic (key-based) access.
4. On the permissions page choose **Attach policies directly**, then search for
   and tick each of these:
   - `AmazonBedrockFullAccess`
   - `AmazonTranscribeFullAccess`
   - `AmazonTextractFullAccess`
   - `AmazonS3FullAccess`
5. Click **Next → Create user**.
6. Open the new `gameday-user` → **Security credentials** tab →
   **Create access key**.
7. Choose **Application running outside AWS** (or "Command Line Interface"),
   click through, and **Create access key**.
8. **Copy the Access key ID and Secret access key now.** The secret is shown
   **only once**. Download the `.csv` if offered.

> Do not paste these keys into chat, screenshots, or any repo. Keep the window
> open until you've put them into `samples/.env` (next section).

### Option B — AWS CLI (if an organizer runs it)

Run from a machine that already has admin credentials configured:

```bash
# 1. Create the user
aws iam create-user --user-name gameday-user

# 2. Attach the AWS managed policies
aws iam attach-user-policy --user-name gameday-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-user-policy --user-name gameday-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonTranscribeFullAccess
aws iam attach-user-policy --user-name gameday-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonTextractFullAccess
aws iam attach-user-policy --user-name gameday-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# 3. Create the access key (copy the secret immediately — shown once)
aws iam create-access-key --user-name gameday-user
```

---

## 3. Put your credentials into your environment

You have two options. The samples work with either.

### Option A — a `.env` file (what the samples read by default)

Copy the example and fill in your keys:

```bash
# From the samples/ folder
# Windows PowerShell:
Copy-Item .env.example .env
# macOS/Linux:
# cp .env.example .env
```

Then edit `samples/.env`:

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
GAMEDAY_BUCKET=your-bucket-name
```

> `GAMEDAY_BUCKET` is only needed for the S3 sample. Set it to a bucket you have
> access to (create one if needed with `aws s3 mb s3://your-bucket-name`).

> 🔒 `samples/.env` is already git-ignored. **Never remove it from `.gitignore`
> and never commit it.**

### Option B — an AWS CLI profile

```bash
aws configure --profile gameday
# AWS Access Key ID     [None]: AKIA...
# AWS Secret Access Key [None]: ****
# Default region name   [None]: us-east-1
# Default output format [None]: json
```

Then tell the samples to use it:

```bash
# Windows PowerShell:
$env:AWS_PROFILE = "gameday"
# macOS/Linux:
# export AWS_PROFILE=gameday
```

(You still need `GAMEDAY_BUCKET` set if you use the S3 sample.)

### Check it works

```bash
aws sts get-caller-identity
```

You should see your `gameday-user` ARN. If you get an error, your keys aren't
configured correctly.

---

## 4. Clean up (end of game day)

Delete the key so it can never be misused, then remove the user:

```bash
# Delete the access key
aws iam list-access-keys --user-name gameday-user
aws iam delete-access-key --user-name gameday-user --access-key-id AKIA...

# Detach the managed policies
aws iam detach-user-policy --user-name gameday-user --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam detach-user-policy --user-name gameday-user --policy-arn arn:aws:iam::aws:policy/AmazonTranscribeFullAccess
aws iam detach-user-policy --user-name gameday-user --policy-arn arn:aws:iam::aws:policy/AmazonTextractFullAccess
aws iam detach-user-policy --user-name gameday-user --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Delete the user
aws iam delete-user --user-name gameday-user

# Empty + delete the bucket ONLY if you created one for the event
aws s3 rm s3://your-bucket-name --recursive
aws s3 rb s3://your-bucket-name
```

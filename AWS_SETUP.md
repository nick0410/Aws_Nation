# AWS Credentials Setup — Step by Step

## Step 1: Login to AWS Console

Go to: https://console.aws.amazon.com

---

## Step 2: Create an IAM User (DO NOT use root account)

1. Search **"IAM"** in the top search bar → Open IAM
2. Left sidebar → **Users** → Click **"Create user"**
3. Enter username: `aws-autonation-user`
4. Click **Next**

---

## Step 3: Attach Permissions

1. Select **"Attach policies directly"**
2. Search and check: **`AmazonS3FullAccess`**
3. Click **Next** → **Create user**

---

## Step 4: Generate Access Keys

1. Click on the user you just created (`aws-autonation-user`)
2. Go to **"Security credentials"** tab
3. Scroll down to **"Access keys"** → Click **"Create access key"**
4. Select **"Application running outside AWS"** → Next
5. Click **"Create access key"**
6. **COPY BOTH VALUES NOW** (you won't see the secret again):
   - `Access key ID`       → goes in AWS_ACCESS_KEY_ID
   - `Secret access key`   → goes in AWS_SECRET_ACCESS_KEY
7. Click **Download .csv** to save a backup

---

## Step 5: Fill Your .env File

Open `backend/.env` (copy from `.env.example`) and fill:

```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=ap-south-1
```

**Choosing your region:**
| Region Name         | Code           |
|---------------------|----------------|
| US East (Virginia)  | us-east-1      |
| Asia Pacific Mumbai | ap-south-1     |
| Europe (Ireland)    | eu-west-1      |
| US West (Oregon)    | us-west-2      |

---

## Step 6: Test the Connection

```bash
cd backend
python -c "
import boto3, os
from dotenv import load_dotenv
load_dotenv()
client = boto3.client('s3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
buckets = client.list_buckets()
print('Connected! Existing buckets:', len(buckets['Buckets']))
"
```

If you see `Connected! Existing buckets: 0` (or any number) → AWS is working!

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `InvalidClientTokenId` | Wrong Access Key ID | Re-check the key in IAM console |
| `SignatureDoesNotMatch` | Wrong Secret Key | Re-copy the secret access key |
| `AuthFailure` | Keys disabled or deleted | Go to IAM → Regenerate keys |
| `BucketAlreadyExists` | Name taken globally | Use a more unique name (add your initials or date) |
| `AccessDenied` | Missing S3 permission | Add `AmazonS3FullAccess` policy to IAM user |
| `NoCredentialsError` | .env not loaded | Make sure file is named `.env` not `.env.example` |

---

## S3 Bucket Naming Rules (Important!)

- **3–63 characters** long
- **Lowercase** letters, numbers, hyphens only
- Cannot start or end with a hyphen
- Must be **globally unique** across ALL AWS accounts
- Examples: `john-products-2026`, `my-app-storage-01`

---

## Security Best Practices

- Never commit `.env` to GitHub (it's in `.gitignore`)
- Use IAM roles instead of access keys in production
- Enable MFA on your AWS root account
- Rotate access keys every 90 days

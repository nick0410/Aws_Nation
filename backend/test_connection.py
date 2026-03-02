"""
AWS AutoNation — Connection Test Script
Run this to verify all services are configured correctly.

Usage:
    python test_connection.py
"""

import os
import sys

# ─────────────────────────────────────────────────────────────
# Load .env
# ─────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env file loaded")
except ImportError:
    print("❌ python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)

print()
print("=" * 55)
print("  AWS AutoNation — Connection Diagnostic")
print("=" * 55)

# ─────────────────────────────────────────────────────────────
# 1. Check AWS Credentials
# ─────────────────────────────────────────────────────────────
print("\n📦 [1/3] Testing AWS S3 Connection...")
print("-" * 40)

key    = os.getenv("AWS_ACCESS_KEY_ID",    "")
secret = os.getenv("AWS_SECRET_ACCESS_KEY","")
region = os.getenv("AWS_DEFAULT_REGION",   "us-east-1")

if not key or key == "AKIAIOSFODNN7EXAMPLE":
    print("❌ AWS_ACCESS_KEY_ID not set in .env")
    print("   → See AWS_SETUP.md for instructions")
elif not secret or secret.startswith("wJalrXUtn"):
    print("❌ AWS_SECRET_ACCESS_KEY not set in .env")
    print("   → See AWS_SETUP.md for instructions")
else:
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        print("❌ boto3 not installed. Run: pip install boto3")
        aws_ok = False
        boto3 = None

    if boto3:
        try:
            client = boto3.client(
                "s3",
                region_name=region,
                aws_access_key_id=key,
                aws_secret_access_key=secret
            )
            response = client.list_buckets()
            count    = len(response.get("Buckets", []))
            print(f"✅ AWS Connected!")
            print(f"   Region:  {region}")
            print(f"   Buckets: {count} existing bucket(s)")
            if count > 0:
                for b in response["Buckets"][:5]:
                    print(f"   - {b['Name']}")
            aws_ok = True
        except NoCredentialsError:
            print("❌ Invalid credentials — check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            aws_ok = False
        except ClientError as e:
            code = e.response["Error"]["Code"]
            print(f"❌ AWS Error ({code}): {e.response['Error']['Message']}")
            hints = {
                "InvalidClientTokenId": "Your Access Key ID is wrong. Re-copy from IAM console.",
                "SignatureDoesNotMatch": "Your Secret Key is wrong. Re-copy from IAM console.",
                "AccessDenied":         "Add AmazonS3FullAccess policy to your IAM user.",
            }
            if code in hints:
                print(f"   → {hints[code]}")
            aws_ok = False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            aws_ok = False

# ─────────────────────────────────────────────────────────────
# 2. Check ML (HuggingFace)
# ─────────────────────────────────────────────────────────────
print("\n🤖 [2/3] Testing ML (HuggingFace)...")
print("-" * 40)
try:
    import transformers
    print(f"✅ transformers installed (version {transformers.__version__})")
    try:
        import torch
        print(f"✅ torch installed (version {torch.__version__})")
        print("   Note: First summarization will download ~1.5GB model (cached after)")
        ml_ok = True
    except ImportError:
        print("❌ torch not installed. Run: pip install torch")
        ml_ok = False
except ImportError:
    print("❌ transformers not installed. Run: pip install transformers")
    ml_ok = False

# ─────────────────────────────────────────────────────────────
# 3. Check Blockchain (Web3)
# ─────────────────────────────────────────────────────────────
print("\n⛓️  [3/3] Testing Blockchain (Web3)...")
print("-" * 40)

rpc      = os.getenv("BLOCKCHAIN_RPC_URL",          "")
priv_key = os.getenv("BLOCKCHAIN_PRIVATE_KEY",      "")
contract = os.getenv("BLOCKCHAIN_CONTRACT_ADDRESS", "")

if not rpc or "YOUR_INFURA" in rpc:
    print("⚠️  BLOCKCHAIN_RPC_URL not configured (optional)")
    print("   → Blockchain logging will be skipped")
    bc_ok = None
else:
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc))
        if w3.is_connected():
            print(f"✅ Blockchain connected!")
            print(f"   Network: Sepolia Testnet")
            chain_id = w3.eth.chain_id
            print(f"   Chain ID: {chain_id} (11155111 = Sepolia ✓)" if chain_id == 11155111 else f"   Chain ID: {chain_id}")

            if priv_key and priv_key != "your_metamask_testnet_private_key_here":
                account = w3.eth.account.from_key(priv_key)
                balance = w3.eth.get_balance(account.address)
                eth_bal = w3.from_wei(balance, "ether")
                print(f"   Wallet:  {account.address[:12]}...{account.address[-6:]}")
                print(f"   Balance: {eth_bal:.4f} ETH")
                if eth_bal == 0:
                    print("   ⚠️  Balance is 0! Get free Sepolia ETH: https://sepoliafaucet.com")
            else:
                print("   ⚠️  BLOCKCHAIN_PRIVATE_KEY not set")

            if contract and not contract.startswith("0xYOUR"):
                print(f"   Contract: {contract[:12]}...{contract[-6:]}")
            else:
                print("   ⚠️  CONTRACT_ADDRESS not set — deploy BucketLogger.sol first")
            bc_ok = True
        else:
            print("❌ Cannot connect to RPC endpoint")
            print("   → Check your Infura/Alchemy project ID in .env")
            bc_ok = False
    except ImportError:
        print("❌ web3 not installed. Run: pip install web3")
        bc_ok = False
    except Exception as e:
        print(f"❌ Blockchain error: {e}")
        bc_ok = False

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
print()
print("=" * 55)
print("  SUMMARY")
print("=" * 55)
print(f"  AWS S3:      {'✅ Ready' if aws_ok else '❌ Not configured'}")
print(f"  ML (BART):   {'✅ Ready' if ml_ok  else '❌ Missing packages'}")
bc_status = "✅ Ready" if bc_ok else ("⚠️  Skipped (optional)" if bc_ok is None else "❌ Error")
print(f"  Blockchain:  {bc_status}")
print()

if aws_ok and ml_ok:
    print("🚀 Core features ready! Start the backend:")
    print("   python main.py")
    print()
    print("   Then open http://localhost:8000/docs to test the API")
else:
    print("⚠️  Fix the issues above, then re-run this script.")
print("=" * 55)

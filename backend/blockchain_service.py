"""
Blockchain Service
Logs S3 bucket creation events to Ethereum (Sepolia testnet) via Web3.py.
Each bucket creation is an immutable on-chain record.

Setup:
  1. Deploy the smart contract in ../smart_contract/BucketLogger.sol
  2. Set BLOCKCHAIN_RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS in .env
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RPC_URL          = os.getenv("BLOCKCHAIN_RPC_URL")        # e.g. Infura / Alchemy Sepolia URL
PRIVATE_KEY      = os.getenv("BLOCKCHAIN_PRIVATE_KEY")    # Wallet private key (no 0x prefix needed)
CONTRACT_ADDRESS = os.getenv("BLOCKCHAIN_CONTRACT_ADDRESS")

# ABI matches BucketLogger.sol
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "bucketName",  "type": "string"},
            {"internalType": "string", "name": "ownerEmail",  "type": "string"},
            {"internalType": "string", "name": "region",      "type": "string"}
        ],
        "name": "logBucket",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getLogs",
        "outputs": [
            {
                "components": [
                    {"internalType": "string",  "name": "bucketName",  "type": "string"},
                    {"internalType": "string",  "name": "ownerEmail",  "type": "string"},
                    {"internalType": "string",  "name": "region",      "type": "string"},
                    {"internalType": "uint256", "name": "timestamp",   "type": "uint256"},
                    {"internalType": "address", "name": "creator",     "type": "address"}
                ],
                "internalType": "struct BucketLogger.BucketLog[]",
                "name": "",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getLogCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def _get_web3():
    """Return a connected Web3 instance or None."""
    try:
        from web3 import Web3
        if not RPC_URL:
            return None, "BLOCKCHAIN_RPC_URL not set in .env"
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not w3.is_connected():
            return None, "Cannot connect to blockchain RPC endpoint."
        return w3, None
    except ImportError:
        return None, "web3 package not installed. Run: pip install web3"
    except Exception as e:
        return None, str(e)


def _get_contract(w3):
    """Return the contract instance."""
    from web3 import Web3
    if not CONTRACT_ADDRESS:
        return None, "BLOCKCHAIN_CONTRACT_ADDRESS not set in .env"
    checksum_addr = Web3.to_checksum_address(CONTRACT_ADDRESS)
    contract = w3.eth.contract(address=checksum_addr, abi=CONTRACT_ABI)
    return contract, None


def log_bucket_creation(bucket_name: str, owner_email: str, region: str) -> dict:
    """
    Write a bucket creation event to the blockchain.
    Returns tx hash and block number on success.
    """
    w3, err = _get_web3()
    if not w3:
        return {"success": False, "error": err, "mode": "blockchain-disabled"}

    contract, err = _get_contract(w3)
    if not contract:
        return {"success": False, "error": err, "mode": "blockchain-disabled"}

    if not PRIVATE_KEY:
        return {"success": False, "error": "BLOCKCHAIN_PRIVATE_KEY not set.", "mode": "blockchain-disabled"}

    try:
        from web3 import Web3

        account = w3.eth.account.from_key(PRIVATE_KEY)
        nonce   = w3.eth.get_transaction_count(account.address)

        txn = contract.functions.logBucket(
            bucket_name, owner_email, region
        ).build_transaction({
            "from":     account.address,
            "nonce":    nonce,
            "gas":      200_000,
            "gasPrice": w3.to_wei("20", "gwei"),
        })

        signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        tx_hash    = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt    = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "success": True,
            "tx_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "network": "Sepolia Testnet",
            "explorer_url": f"https://sepolia.etherscan.io/tx/{receipt.transactionHash.hex()}"
        }

    except Exception as e:
        return {"success": False, "error": str(e), "mode": "blockchain-error"}


def get_bucket_logs() -> dict:
    """
    Fetch all bucket creation logs from the blockchain smart contract.
    """
    w3, err = _get_web3()
    if not w3:
        return {
            "success": False,
            "error": err,
            "logs": [],
            "note": "Configure .env to enable blockchain logging"
        }

    contract, err = _get_contract(w3)
    if not contract:
        return {"success": False, "error": err, "logs": []}

    try:
        raw_logs = contract.functions.getLogs().call()
        logs = []
        for entry in raw_logs:
            logs.append({
                "bucket_name":  entry[0],
                "owner_email":  entry[1],
                "region":       entry[2],
                "timestamp":    datetime.utcfromtimestamp(entry[3]).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "creator_addr": entry[4],
            })
        return {
            "success": True,
            "count": len(logs),
            "logs": logs,
            "network": "Sepolia Testnet"
        }
    except Exception as e:
        return {"success": False, "error": str(e), "logs": []}


def get_contract_info() -> dict:
    """Return basic info about the configured smart contract."""
    w3, err = _get_web3()
    connected = w3 is not None

    return {
        "contract_address": CONTRACT_ADDRESS or "Not configured",
        "network":          "Sepolia Testnet (Ethereum)",
        "rpc_configured":   bool(RPC_URL),
        "key_configured":   bool(PRIVATE_KEY),
        "connected":        connected,
        "connection_error": err if not connected else None,
        "explorer":         f"https://sepolia.etherscan.io/address/{CONTRACT_ADDRESS}"
                            if CONTRACT_ADDRESS else None
    }

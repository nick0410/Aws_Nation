// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BucketLogger
 * @notice Immutably records every S3 bucket creation event on-chain.
 *         Deployed on Ethereum Sepolia testnet.
 *
 * Deploy via Remix IDE (https://remix.ethereum.org):
 *   1. Paste this file into Remix
 *   2. Compile with Solidity 0.8.20
 *   3. Deploy to Injected Provider (MetaMask → Sepolia)
 *   4. Copy the contract address → BLOCKCHAIN_CONTRACT_ADDRESS in .env
 */

contract BucketLogger {

    // ─────────────────────────────────────────────────
    // Structs & State
    // ─────────────────────────────────────────────────

    struct BucketLog {
        string  bucketName;
        string  ownerEmail;
        string  region;
        uint256 timestamp;
        address creator;
    }

    BucketLog[] private logs;

    // ─────────────────────────────────────────────────
    // Events
    // ─────────────────────────────────────────────────

    event BucketCreated(
        string  indexed bucketName,
        string          ownerEmail,
        string          region,
        uint256         timestamp,
        address indexed creator
    );

    // ─────────────────────────────────────────────────
    // Write
    // ─────────────────────────────────────────────────

    /**
     * @notice Log an S3 bucket creation.
     * @param bucketName  AWS S3 bucket name
     * @param ownerEmail  Owner's email address
     * @param region      AWS region (e.g. "us-east-1")
     */
    function logBucket(
        string calldata bucketName,
        string calldata ownerEmail,
        string calldata region
    ) external {
        require(bytes(bucketName).length > 0,  "Bucket name required");
        require(bytes(ownerEmail).length  > 0,  "Owner email required");
        require(bytes(region).length      > 0,  "Region required");

        BucketLog memory entry = BucketLog({
            bucketName: bucketName,
            ownerEmail: ownerEmail,
            region:     region,
            timestamp:  block.timestamp,
            creator:    msg.sender
        });

        logs.push(entry);

        emit BucketCreated(bucketName, ownerEmail, region, block.timestamp, msg.sender);
    }

    // ─────────────────────────────────────────────────
    // Read
    // ─────────────────────────────────────────────────

    /// @notice Return all logged bucket events
    function getLogs() external view returns (BucketLog[] memory) {
        return logs;
    }

    /// @notice Return number of bucket events logged
    function getLogCount() external view returns (uint256) {
        return logs.length;
    }

    /// @notice Return a single log entry by index
    function getLog(uint256 index) external view returns (BucketLog memory) {
        require(index < logs.length, "Index out of bounds");
        return logs[index];
    }
}

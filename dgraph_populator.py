# dgraph_populator.py
# Step 2: Populate DGraph with data from MySQL/Qdrant

import pydgraph
import json
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
import os
from operator_data import country_data, TECH_KEYWORDS

# Load environment
load_dotenv()

# ============================================================================
# Configuration
# ============================================================================
DGRAPH_HOST = os.getenv("DGRAPH_HOST", "localhost:9080")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

BATCH_SIZE = 100  # Process emails in batches


# ============================================================================
# DGraph Connection
# ============================================================================
def create_dgraph_client():
    """Create DGraph client."""
    client_stub = pydgraph.DgraphClientStub(DGRAPH_HOST)
    return pydgraph.DgraphClient(client_stub)


# ============================================================================
# MySQL Connection
# ============================================================================
def connect_mysql():
    """Connect to MySQL."""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        print(f"✅ Connected to MySQL at {MYSQL_HOST}:{MYSQL_PORT}")
        return conn
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        return None


# ============================================================================
# Step 1: Create Subsidiary Nodes
# ============================================================================
def create_subsidiaries(dgraph_client):
    """Create subsidiary nodes."""
    print("\n" + "=" * 80)
    print("STEP 1: Creating Subsidiaries")
    print("=" * 80)

    # Get unique subsidiaries
    subsidiaries = {}
    for country_name, data in country_data.items():
        for sub in data.get("subsidiaries", []):
            if sub not in subsidiaries:
                subsidiaries[sub] = {
                    "name": sub,
                    "countries": []
                }
            subsidiaries[sub]["countries"].append(country_name)

    sub_uids = {}

    for sub_name, sub_data in subsidiaries.items():
        txn = dgraph_client.txn()
        try:
            mutation = {
                "dgraph.type": "Subsidiary",
                "name": sub_name,
                "region": "METO"  # Adjust if you have region data
            }

            response = txn.mutate(set_obj=mutation)
            txn.commit()

            uid = list(response.uids.values())[0] if response.uids else None
            sub_uids[sub_name] = uid
            print(f"  Created: {sub_name} (UID: {uid})")

        except Exception as e:
            print(f"  ⚠️  Failed to create {sub_name}: {e}")
        finally:
            txn.discard()

    print(f"\n✅ Created {len(sub_uids)} subsidiaries")
    return sub_uids


# ============================================================================
# Step 2: Create Country Nodes
# ============================================================================
def create_countries(dgraph_client, sub_uids):
    """Create country nodes linked to subsidiaries."""
    print("\n" + "=" * 80)
    print("STEP 2: Creating Countries")
    print("=" * 80)

    country_uids = {}

    for country_name, data in country_data.items():
        # Get subsidiary UID
        sub_name = data.get("subsidiaries", ["Unknown"])[0]
        sub_uid = sub_uids.get(sub_name)

        txn = dgraph_client.txn()
        try:
            mutation = {
                "dgraph.type": "Country",
                "name": country_name,
                "aliases": data.get("aliases", []),
            }

            if sub_uid:
                mutation["subsidiary"] = {"uid": sub_uid}

            response = txn.mutate(set_obj=mutation)
            txn.commit()

            uid = list(response.uids.values())[0] if response.uids else None
            country_uids[country_name] = uid
            print(f"  Created: {country_name} → {sub_name} (UID: {uid})")

        except Exception as e:
            print(f"  ⚠️  Failed to create {country_name}: {e}")
        finally:
            txn.discard()

    print(f"\n✅ Created {len(country_uids)} countries")
    return country_uids


# ============================================================================
# Step 3: Create Operator Nodes
# ============================================================================
def create_operators(dgraph_client, country_uids):
    """Create operator nodes linked to countries."""
    print("\n" + "=" * 80)
    print("STEP 3: Creating Operators")
    print("=" * 80)

    operator_uids = {}

    for country_name, data in country_data.items():
        country_uid = country_uids.get(country_name)

        for op_name in data.get("operators", []):
            # Check if operator already exists (for duplicate operators across countries)
            if op_name in operator_uids:
                print(f"  Skipped: {op_name} → {country_name} (already exists)")
                continue

            txn = dgraph_client.txn()
            try:
                mutation = {
                    "dgraph.type": "Operator",
                    "name": op_name,
                }

                if country_uid:
                    mutation["country"] = {"uid": country_uid}

                response = txn.mutate(set_obj=mutation)
                txn.commit()

                # Get UID from uids map
                uid = list(response.uids.values())[0] if response.uids else None
                operator_uids[op_name] = uid
                print(f"  Created: {op_name} → {country_name} (UID: {uid})")

            except Exception as e:
                print(f"  ⚠️  Failed to create {op_name}: {e}")
            finally:
                txn.discard()

    print(f"\n✅ Created {len(operator_uids)} operators")
    return operator_uids


# ============================================================================
# Step 4: Create Tech Term Nodes
# ============================================================================
def create_tech_terms(dgraph_client):
    """Create technical term nodes."""
    print("\n" + "=" * 80)
    print("STEP 4: Creating Tech Terms")
    print("=" * 80)

    txn = dgraph_client.txn()
    try:
        term_uids = {}

        for term in TECH_KEYWORDS:
            # Categorize terms (basic categorization)
            category = "general"
            if term in ["5g", "nr", "nsa", "sa", "volte", "vowifi", "vonr"]:
                category = "network"
            elif term in ["s25", "s936b", "z8", "sm-"]:
                category = "device"
            elif term in ["firmware", "binary", "modem", "cp", "ap"]:
                category = "software"
            elif term in ["log", "dump", "pcap", "wireshark"]:
                category = "debugging"

            mutation = {
                "dgraph.type": "TechTerm",
                "name": term,
                "category": category
            }

            response = txn.mutate(set_obj=mutation, commit_now=False)
            uid = response.uids.get('blank-0')
            term_uids[term] = uid

        txn.commit()
        print(f"\n✅ Created {len(term_uids)} tech terms")
        return term_uids

    except Exception as e:
        print(f"❌ Failed to create tech terms: {e}")
        return {}
    finally:
        txn.discard()


# ============================================================================
# Step 5: Load Emails from MySQL
# ============================================================================
def load_emails(dgraph_client, mysql_conn, operator_uids, term_uids):
    """Load emails from MySQL and create relationships."""
    print("\n" + "=" * 80)
    print("STEP 5: Loading Emails")
    print("=" * 80)

    cursor = mysql_conn.cursor(dictionary=True)

    try:
        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM emailcontent")
        total = cursor.fetchone()['count']
        print(f"Total emails to process: {total}")

        offset = 0
        processed = 0

        while offset < total:
            # Fetch batch
            cursor.execute("""
                SELECT UID, subject, plaintext, email_date, operator, country
                FROM emailcontent
                ORDER BY UID
                LIMIT %s OFFSET %s
            """, (BATCH_SIZE, offset))

            emails = cursor.fetchall()
            if not emails:
                break

            # Create mutations for this batch
            txn = dgraph_client.txn()
            try:
                for email in emails:
                    operator_name = email.get('operator')

                    # Build mutation
                    mutation = {
                        "dgraph.type": "Email",
                        "uid_original": str(email['UID']),
                        "subject": email.get('subject', 'No Subject'),
                        "body": (email.get('plaintext', '') or '')[:5000],  # Limit body size
                        "email_date": email.get('email_date').isoformat() if email.get('email_date') else None
                    }

                    # Link to operator
                    if operator_name and operator_name in operator_uids:
                        mutation["operators"] = [{"uid": operator_uids[operator_name]}]

                    # Link to tech terms (simple text matching)
                    body_lower = (email.get('plaintext', '') or '').lower()
                    subject_lower = (email.get('subject', '') or '').lower()

                    linked_terms = []
                    for term, term_uid in term_uids.items():
                        if term in body_lower or term in subject_lower:
                            linked_terms.append({"uid": term_uid})

                    if linked_terms:
                        mutation["tech_terms"] = linked_terms

                    txn.mutate(set_obj=mutation, commit_now=False)
                    processed += 1

                txn.commit()
                print(f"  Processed: {processed}/{total} emails")

            except Exception as e:
                print(f"  ⚠️  Batch error: {e}")
            finally:
                txn.discard()

            offset += BATCH_SIZE

        print(f"\n✅ Loaded {processed} emails")
        return processed

    except Exception as e:
        print(f"❌ Failed to load emails: {e}")
        return 0
    finally:
        cursor.close()


# ============================================================================
# Main Execution
# ============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("DGRAPH DATA POPULATION FOR RAG2")
    print("=" * 80)

    # Connect to DGraph
    print("\n1. Connecting to DGraph...")
    try:
        dgraph_client = create_dgraph_client()
        print("✅ Connected to DGraph")
    except Exception as e:
        print(f"❌ DGraph connection failed: {e}")
        exit(1)

    # Connect to MySQL
    print("\n2. Connecting to MySQL...")
    mysql_conn = connect_mysql()
    if not mysql_conn:
        exit(1)

    # Create entities
    sub_uids = create_subsidiaries(dgraph_client)
    country_uids = create_countries(dgraph_client, sub_uids)
    operator_uids = create_operators(dgraph_client, country_uids)
    term_uids = create_tech_terms(dgraph_client)

    # Load emails
    email_count = load_emails(dgraph_client, mysql_conn, operator_uids, term_uids)

    # Summary
    print("\n" + "=" * 80)
    print("✅ DATA POPULATION COMPLETE")
    print("=" * 80)
    print(f"  Subsidiaries: {len(sub_uids)}")
    print(f"  Countries: {len(country_uids)}")
    print(f"  Operators: {len(operator_uids)}")
    print(f"  Tech Terms: {len(term_uids)}")
    print(f"  Emails: {email_count}")
    print("=" * 80)
    print("\nNext step: Run dgraph_client.py to test queries")

    # Cleanup
    mysql_conn.close()
    dgraph_client.close()

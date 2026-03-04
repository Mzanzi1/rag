# dgraph_client.py
# Step 3: Query interface for DGraph

import pydgraph
import json
from typing import List, Dict, Any


# ============================================================================
# DGraph Connection
# ============================================================================
class DGraphClient:
    def __init__(self, host="localhost:9080"):
        """Initialize DGraph client."""
        self.stub = pydgraph.DgraphClientStub(host)
        self.client = pydgraph.DgraphClient(self.stub)

    def close(self):
        """Close connection."""
        self.stub.close()

    # ========================================================================
    # Entity Queries
    # ========================================================================

    def get_operator_info(self, operator_name: str) -> Dict:
        """Get operator information including country and related entities."""
        query = """
        query operator_info($name: string) {
            operator(func: eq(name, $name)) @filter(type(Operator) AND has(country)) {
                uid
                name
                country {
                    name
                    subsidiary {
                        name
                        region
                    }
                }
                emails: ~operators {
                    count(uid)
                }
                tech_terms {
                    name
                    category
                }
            }
        }
        """

        variables = {"$name": operator_name}
        txn = self.client.txn(read_only=True)
        try:
            res = txn.query(query, variables=variables)
            data = json.loads(res.json)
            # Return only the first valid result
            if data.get('operator') and len(data['operator']) > 0:
                return {'operator': [data['operator'][0]]}
            return data
        finally:
            txn.discard()

    def get_country_operators(self, country_name: str) -> List[str]:
        """Get all operators in a country."""
        query = """
        {
            country(func: eq(name, "%s")) @filter(type(Country)) {
                ~country @filter(type(Operator)) {
                    name
                }
            }
        }
        """ % country_name

        txn = self.client.txn(read_only=True)
        try:
            res = txn.query(query)
            data = json.loads(res.json)
            if data.get('country') and len(data['country']) > 0:
                operators = data['country'][0].get('~country', [])
                return [op['name'] for op in operators if op.get('name')]
            return []
        finally:
            txn.discard()

    def find_related_operators(self, operator_name: str, max_depth=2) -> List[str]:
        """
        Find operators related through:
        - Same country
        - Same subsidiary
        """
        query = """
        query related_ops($name: string) {
            operator(func: eq(name, $name)) @filter(type(Operator)) {
                name

                # Same country operators
                country {
                    name
                    ~country @filter(type(Operator)) {
                        name
                    }
                }
            }
        }
        """

        variables = {"$name": operator_name}
        txn = self.client.txn(read_only=True)
        try:
            res = txn.query(query, variables=variables)
            data = json.loads(res.json)

            related = set()
            if data.get('operator') and len(data['operator']) > 0:
                op = data['operator'][0]

                # Same country
                if op.get('country') and len(op['country']) > 0:
                    country = op['country'][0]
                    same_country_ops = country.get('~country', [])
                    for op_data in same_country_ops:
                        if op_data.get('name'):
                            related.add(op_data['name'])

                # Remove self
                related.discard(operator_name)

            return list(related)
        finally:
            txn.discard()

    def expand_tech_query(self, terms: List[str]) -> List[str]:
        """
        Expand technical terms with related terms.
        Example: "5g" → ["5g", "nr", "nsa", "sa"]
        """
        if not terms:
            return []

        # Use eq or anyofterms instead of anyoftext
        query = """
        query expand_terms($term: string) {
            tech(func: eq(name, $term)) @filter(type(TechTerm)) {
                name
                category
            }
        }
        """

        expanded = set(terms)
        txn = self.client.txn(read_only=True)
        try:
            for term in terms:
                variables = {"$term": term}
                res = txn.query(query, variables=variables)
                data = json.loads(res.json)

                if data.get('tech'):
                    for term_obj in data['tech']:
                        expanded.add(term_obj['name'])
                        # Add related terms by category
                        category = term_obj.get('category')
                        if category:
                            # Query for other terms in same category
                            cat_query = """
                            query cat_terms($cat: string) {
                                terms(func: eq(category, $cat)) @filter(type(TechTerm)) {
                                    name
                                }
                            }
                            """
                            cat_res = txn.query(cat_query, variables={"$cat": category})
                            cat_data = json.loads(cat_res.json)
                            if cat_data.get('terms'):
                                for t in cat_data['terms'][:3]:  # Limit to 3
                                    expanded.add(t['name'])

            return list(expanded)
        finally:
            txn.discard()

    def find_emails_by_operator_and_tech(self, operator: str, tech_terms: List[str], limit=10) -> List[Dict]:
        """Find emails matching operator and tech terms."""
        query = """
        query emails($op: string, $terms: string) {
            var(func: eq(name, $op)) @filter(type(Operator)) {
                op_emails as ~operators
            }

            var(func: anyoftext(name, $terms)) @filter(type(TechTerm)) {
                term_emails as ~tech_terms
            }

            emails(func: uid(op_emails)) @filter(uid(term_emails)) {
                uid
                subject
                email_date
                body
            }
        }
        """

        variables = {
            "$op": operator,
            "$terms": " ".join(tech_terms)
        }

        txn = self.client.txn(read_only=True)
        try:
            res = txn.query(query, variables=variables)
            data = json.loads(res.json)
            return data.get('emails', [])[:limit]
        finally:
            txn.discard()

    # ========================================================================
    # Analytics Queries
    # ========================================================================

    def get_operator_stats(self) -> List[Dict]:
        """Get email count per operator."""
        query = """
        {
            operators(func: type(Operator)) {
                name
                email_count: count(~operators)
                country {
                    name
                }
            }
        }
        """

        txn = self.client.txn(read_only=True)
        try:
            res = txn.query(query)
            data = json.loads(res.json)
            return sorted(data.get('operators', []),
                          key=lambda x: x.get('email_count', 0),
                          reverse=True)
        finally:
            txn.discard()

    def get_popular_tech_terms(self, limit=20) -> List[Dict]:
        """Get most mentioned tech terms."""
        query = """
        {
            terms(func: type(TechTerm), orderdesc: count(~tech_terms), first: 20) {
                name
                category
                mention_count: count(~tech_terms)
            }
        }
        """

        txn = self.client.txn(read_only=True)
        try:
            res = txn.query(query)
            data = json.loads(res.json)
            return data.get('terms', [])[:limit]
        finally:
            txn.discard()


# ============================================================================
# CLI Interface for Testing
# ============================================================================
def test_queries():
    """Interactive CLI to test DGraph queries."""
    print("=" * 80)
    print("DGRAPH QUERY TESTER")
    print("=" * 80)

    client = DGraphClient()

    while True:
        print("\n" + "=" * 80)
        print("COMMANDS:")
        print("  1. Get operator info")
        print("  2. Find related operators")
        print("  3. Expand tech query")
        print("  4. Get operator stats")
        print("  5. Get popular tech terms")
        print("  6. Exit")
        print("=" * 80)

        choice = input("\nChoice: ").strip()

        if choice == "1":
            op_name = input("Operator name: ").strip()
            info = client.get_operator_info(op_name)
            print(json.dumps(info, indent=2))

        elif choice == "2":
            op_name = input("Operator name: ").strip()
            related = client.find_related_operators(op_name)
            print(f"\nRelated operators: {', '.join(related)}")

        elif choice == "3":
            terms = input("Tech terms (comma-separated): ").strip().split(',')
            terms = [t.strip() for t in terms]
            expanded = client.expand_tech_query(terms)
            print(f"\nExpanded: {', '.join(expanded)}")

        elif choice == "4":
            stats = client.get_operator_stats()
            print("\nOperator Email Counts:")
            for stat in stats[:10]:
                country = stat.get('country', [{}])[0].get('name', 'Unknown')
                print(f"  {stat['name']} ({country}): {stat.get('email_count', 0)} emails")

        elif choice == "5":
            terms = client.get_popular_tech_terms()
            print("\nTop Tech Terms:")
            for term in terms:
                print(f"  {term['name']} ({term['category']}): {term.get('mention_count', 0)} mentions")

        elif choice == "6":
            break

        else:
            print("Invalid choice")

    client.close()
    print("\n👋 Goodbye!")


# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    test_queries()

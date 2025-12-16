import psycopg2

def test_connection(port, version):
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",  # Default database
            user="postgres",
            password="Qir@t_S2eed123",
            port=port
        )
        print(f"✓ PostgreSQL {version} (port {port}) - Connection successful!")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ PostgreSQL {version} (port {port}) - Failed: {e}")
        return False

# Test both versions
print("Testing PostgreSQL connections...\n")
test_connection(5432, "13")
test_connection(5433, "18")
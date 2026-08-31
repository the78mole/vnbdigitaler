"""Simple PostgreSQL connection test for VNB Digitaler."""

import os

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_connection():
    """Test PostgreSQL connection."""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=os.getenv("DATABASE_HOST", "localhost"),
            port=os.getenv("DATABASE_PORT", "5432"),
            database=os.getenv("DATABASE_NAME", "vnb_digitaler"),
            user=os.getenv("DATABASE_USER", "vnb_admin"),
            password=os.getenv("DATABASE_PASSWORD"),
        )

        print("✅ Database connection successful!")

        # Test basic query
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"📊 PostgreSQL Version: {version[0]}")

            # Test schema exists
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'vnb_digitaler';"
            )
            schema = cursor.fetchone()
            if schema:
                print("✅ Schema 'vnb_digitaler' exists")
            else:
                print("❌ Schema 'vnb_digitaler' not found")

            # Count tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'vnb_digitaler'
            """)
            tables = cursor.fetchall()
            print(f"📋 Found {len(tables)} tables in vnb_digitaler schema:")
            for table in tables:
                print(f"   - {table[0]}")

            # Test sample data
            cursor.execute("SELECT COUNT(*) FROM vnb_digitaler.bdew_grid_operators;")
            count = cursor.fetchone()
            print(f"📊 BDEW Grid Operators: {count[0]} records")

        conn.close()
        print("✅ Connection test completed successfully!")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("🚀 VNB Digitaler - PostgreSQL Connection Test")
    print("=" * 50)
    test_connection()

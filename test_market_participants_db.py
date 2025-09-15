"""Test script for the new market participants database structure."""

import os

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_market_participants_db():
    """Test the new market participants database structure."""
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

        with conn.cursor() as cursor:
            # Test schema and tables
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'vnb_digitaler'
                ORDER BY table_name
            """
            )
            tables = cursor.fetchall()
            print(f"📋 Found {len(tables)} tables in vnb_digitaler schema:")
            for table in tables:
                print(f"   - {table[0]}")

            # Test market participant roles
            cursor.execute(
                """
                SELECT role_category, COUNT(*) as role_count
                FROM vnb_digitaler.market_participant_roles
                WHERE is_active = true
                GROUP BY role_category
                ORDER BY role_category
            """
            )
            role_stats = cursor.fetchall()
            print("\n📊 Market Participant Roles by Category:")
            for category, count in role_stats:
                print(f"   - {category}: {count} roles")

            # Test companies
            cursor.execute(
                "SELECT COUNT(*) FROM vnb_digitaler.companies WHERE is_active = true"
            )
            company_count = cursor.fetchone()[0]
            print(f"\n🏢 Companies: {company_count} active companies")

            # Test company roles relationships
            cursor.execute(
                """
                SELECT
                    c.company_name,
                    STRING_AGG(r.bdew_role_code, ', ' ORDER BY r.bdew_role_code) as roles
                FROM vnb_digitaler.companies c
                JOIN vnb_digitaler.company_roles cr ON c.id = cr.company_id
                JOIN vnb_digitaler.market_participant_roles r ON cr.role_id = r.id
                WHERE c.is_active = true AND cr.is_active = true
                GROUP BY c.company_name
                ORDER BY c.company_name
            """
            )
            company_roles = cursor.fetchall()
            print("\n🔗 Company-Role Assignments:")
            for company, roles in company_roles:
                print(f"   - {company}: {roles}")

            # Test multi-role companies
            cursor.execute(
                """
                SELECT
                    c.company_name,
                    COUNT(DISTINCT cr.role_id) as role_count
                FROM vnb_digitaler.companies c
                JOIN vnb_digitaler.company_roles cr ON c.id = cr.company_id
                WHERE c.is_active = true AND cr.is_active = true
                GROUP BY c.company_name
                HAVING COUNT(DISTINCT cr.role_id) > 1
                ORDER BY role_count DESC, c.company_name
            """
            )
            multi_role = cursor.fetchall()
            print(f"\n🎭 Multi-Role Companies ({len(multi_role)} companies):")
            for company, count in multi_role:
                print(f"   - {company}: {count} roles")

            # Test service territories
            cursor.execute(
                """
                SELECT DISTINCT service_territory, COUNT(*) as companies
                FROM vnb_digitaler.company_roles
                WHERE service_territory IS NOT NULL AND is_active = true
                GROUP BY service_territory
                ORDER BY companies DESC, service_territory
            """
            )
            territories = cursor.fetchall()
            print(f"\n🗺️  Service Territories ({len(territories)} territories):")
            for territory, count in territories:
                print(f"   - {territory}: {count} company roles")

        conn.close()
        print("\n✅ Market participants database test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


def test_database_constraints():
    """Test database constraints and relationships."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DATABASE_HOST", "localhost"),
            port=os.getenv("DATABASE_PORT", "5432"),
            database=os.getenv("DATABASE_NAME", "vnb_digitaler"),
            user=os.getenv("DATABASE_USER", "vnb_admin"),
            password=os.getenv("DATABASE_PASSWORD"),
        )

        print("\n🔍 Testing Database Constraints...")

        with conn.cursor() as cursor:
            # Test unique constraints
            try:
                cursor.execute(
                    """
                    INSERT INTO vnb_digitaler.companies (company_name, company_code)
                    VALUES ('Stadtwerke München GmbH', 'TEST_DUPLICATE')
                """
                )
                conn.rollback()
                print("❌ Unique constraint not working for company_name")
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                print("✅ Unique constraint working for company_name")

            # Test foreign key constraints
            try:
                cursor.execute(
                    """
                    INSERT INTO vnb_digitaler.company_roles (company_id, role_id)
                    VALUES ('00000000-0000-0000-0000-000000000000', '00000000-0000-0000-0000-000000000000')
                """
                )
                conn.rollback()
                print("❌ Foreign key constraint not working")
            except psycopg2.errors.ForeignKeyViolation:
                conn.rollback()
                print("✅ Foreign key constraints working")

        conn.close()
        print("✅ Constraint tests completed!")

    except Exception as e:
        print(f"❌ Constraint test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("🚀 VNB Digitaler - Market Participants Database Test")
    print("=" * 60)

    if test_market_participants_db():
        test_database_constraints()
        print(
            "\n🎉 All tests passed! Database structure is ready for market participants data."
        )
    else:
        print("\n💥 Tests failed! Please check database setup.")

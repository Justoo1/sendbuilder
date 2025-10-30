"""
Migration Helper Script for Custom User Model Transition

This script helps migrate from Django's default User model to the custom User model
with role-based access control.

IMPORTANT: This script assumes you're in development and can afford to reset the database.
For production, a more complex data migration would be required.

Usage:
    python migrate_to_custom_user.py --fresh-start

Options:
    --fresh-start: Drops all tables and recreates from scratch (DEVELOPMENT ONLY)
    --backup-first: Creates a database backup before migration
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendbuilder.settings')
django.setup()

from django.core.management import call_command
from django.db import connection
from django.contrib.auth import get_user_model
import argparse


def backup_database():
    """Create a backup of the current database"""
    print("\n========================================")
    print("DATABASE BACKUP")
    print("========================================")
    print("\nFor PostgreSQL, run this command manually:")
    print("pg_dump -U postgres -d builder > backup_$(date +%Y%m%d_%H%M%S).sql")
    print("\nPress Enter when backup is complete, or Ctrl+C to cancel...")
    input()


def fresh_start_migration():
    """
    Fresh start migration - drops all tables and recreates.
    WARNING: This will DELETE ALL DATA!
    """
    print("\n========================================")
    print("FRESH START MIGRATION")
    print("========================================")
    print("\nWARNING: This will DELETE ALL DATA in the database!")
    print("This includes:")
    print("  - All users")
    print("  - All studies")
    print("  - All extracted data")
    print("  - All domains")
    print("  - All AI configurations")
    print("\nAre you sure you want to continue? Type 'YES' to confirm:")

    confirmation = input().strip()
    if confirmation != 'YES':
        print("\nMigration cancelled.")
        return False

    print("\n1. Dropping all tables...")
    with connection.cursor() as cursor:
        # Get all table names
        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """)
        tables = cursor.fetchall()

        if tables:
            # Drop all tables
            for table in tables:
                print(f"   Dropping table: {table[0]}")
                cursor.execute(f'DROP TABLE IF EXISTS "{table[0]}" CASCADE')

            print("   ✓ All tables dropped")
        else:
            print("   ✓ No tables to drop")

    print("\n2. Removing migration files...")
    apps_to_clean = ['builder', 'ai', 'invividualdomain']
    for app in apps_to_clean:
        migrations_dir = BASE_DIR / app / 'migrations'
        if migrations_dir.exists():
            for file in migrations_dir.glob('*.py'):
                if file.name != '__init__.py':
                    print(f"   Removing: {file.name}")
                    file.unlink()
            print(f"   ✓ Cleaned {app} migrations")

    print("\n3. Creating fresh migrations...")
    call_command('makemigrations')

    print("\n4. Applying all migrations...")
    call_command('migrate')

    print("\n5. Creating superuser...")
    create_superuser()

    print("\n========================================")
    print("MIGRATION COMPLETE!")
    print("========================================")
    print("\nNext steps:")
    print("1. Log in with your superuser account")
    print("2. Create additional users with appropriate roles")
    print("3. Upload study PDFs to test the workflow")

    return True


def create_superuser():
    """Create a superuser with admin role"""
    User = get_user_model()

    print("\nCreate superuser account:")
    username = input("Username [admin]: ").strip() or "admin"
    email = input("Email [admin@example.com]: ").strip() or "admin@example.com"

    # Check if user exists
    if User.objects.filter(username=username).exists():
        print(f"User '{username}' already exists. Skipping...")
        return

    # Create superuser
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password='admin123',  # Default password
        role='ADMIN',
        first_name='System',
        last_name='Administrator'
    )

    print(f"\n✓ Superuser created successfully!")
    print(f"  Username: {username}")
    print(f"  Password: admin123")
    print(f"  Email: {email}")
    print(f"  Role: Administrator")
    print("\n  IMPORTANT: Change the password immediately after first login!")


def status_check():
    """Check current migration status"""
    print("\n========================================")
    print("MIGRATION STATUS CHECK")
    print("========================================")

    print("\n1. Checking database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"   ✓ PostgreSQL connected: {version[:50]}...")
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        return False

    print("\n2. Checking AUTH_USER_MODEL setting...")
    from django.conf import settings
    auth_user_model = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')
    print(f"   Current AUTH_USER_MODEL: {auth_user_model}")
    if auth_user_model == 'builder.User':
        print("   ✓ Custom user model configured")
    else:
        print("   ✗ Still using default Django user model")

    print("\n3. Checking applied migrations...")
    try:
        call_command('showmigrations', '--list')
    except Exception as e:
        print(f"   Error showing migrations: {e}")

    return True


def main():
    parser = argparse.ArgumentParser(description='Migrate to custom User model')
    parser.add_argument('--fresh-start', action='store_true',
                       help='Drop all tables and start fresh (DEVELOPMENT ONLY)')
    parser.add_argument('--backup-first', action='store_true',
                       help='Create database backup before migration')
    parser.add_argument('--status', action='store_true',
                       help='Check current migration status')

    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     SEND Builder - Custom User Model Migration Tool         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    if args.status:
        status_check()
        return

    if args.backup_first:
        backup_database()

    if args.fresh_start:
        success = fresh_start_migration()
        if success:
            print("\n✓ Migration completed successfully!")
        else:
            print("\n✗ Migration was cancelled or failed.")
            sys.exit(1)
    else:
        print("\nNo action specified. Use --help to see available options.")
        print("\nFor development, use: python migrate_to_custom_user.py --fresh-start")
        print("For status check, use: python migrate_to_custom_user.py --status")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Database setup script for Chat2Fill conversational interface
"""

import os
import sys
import logging
from pathlib import Path

# Add the server directory to the Python path
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_database():
    """Setup database with initial configuration"""
    try:
        print("Setting up database...")

        # Import database components
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from database_manager import DatabaseManager
        from utils.database_config import DatabaseConfig

        # Initialize database configuration
        db_config = DatabaseConfig()

        # Create database manager
        db_manager = DatabaseManager(db_config)

        # Database is automatically initialized in the constructor
        logger.info("Database tables created successfully")

        # Test database connection
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

        logger.info(f"Database setup completed. Created {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table[0]}")

        return True

    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_data():
    """Create sample data for testing"""
    try:
        print("Creating sample data...")

        from database_manager import DatabaseManager
        from utils.database_config import DatabaseConfig
        import json

        # Initialize components
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)

        # Create a sample user session
        session_id = db_manager.create_user_session(
            ip_address="127.0.0.1",
            user_agent="Test Setup Agent",
            preferred_language="en"
        )

        user_id = db_manager.get_user_by_session(session_id)["id"]
        logger.info(f"Created sample user session: {session_id}")

        # Create a sample form
        sample_form_schema = {
            "forms": [{
                "title": "Sample Contact Form",
                "fields": [
                    {
                        "id": "name",
                        "name": "full_name",
                        "type": "text",
                        "label": "Full Name",
                        "required": True
                    },
                    {
                        "id": "email",
                        "name": "email_address",
                        "type": "email",
                        "label": "Email Address",
                        "required": True
                    }
                ]
            }]
        }

        form_id = db_manager.create_form(
            user_id=user_id,
            form_url="https://example.com/sample-form",
            form_type="custom",
            form_title="Sample Contact Form",
            form_schema=json.dumps(sample_form_schema)
        )

        logger.info(f"Created sample form: {form_id}")

        # Create sample form fields
        for field in sample_form_schema["forms"][0]["fields"]:
            field_id = db_manager.create_form_field(
                form_id=form_id,
                field_name=field["name"],
                field_type=field["type"],
                field_label=field["label"],
                field_required=field["required"]
            )
            logger.info(f"Created sample field: {field['label']} (ID: {field_id})")

        logger.info("Sample data created successfully")
        return True

    except Exception as e:
        logger.error(f"Error creating sample data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database functionality"""
    try:
        print("Testing database functionality...")

        from database_manager import DatabaseManager
        from utils.database_config import DatabaseConfig

        # Initialize components
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)

        # Test database info
        db_info = db_manager.get_database_info()
        logger.info(f"Database path: {db_info['database_path']}")
        logger.info(f"Database size: {db_info['database_size_bytes']} bytes")

        # Test table counts
        table_sizes = db_info['table_sizes']
        for table, count in table_sizes.items():
            logger.info(f"Table {table}: {count} records")

        # Test session creation
        session_id = db_manager.create_user_session(
            ip_address="127.0.0.1",
            user_agent="Test Agent",
            preferred_language="en"
        )

        # Test session retrieval
        user_data = db_manager.get_user_by_session(session_id)
        if user_data:
            logger.info(f"Session test passed: {session_id}")
        else:
            logger.error("Session test failed")
            return False

        logger.info("Database tests completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error testing database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_environment():
    """Check if environment is properly set up"""
    try:
        print("Checking environment...")

        # Check if .env file exists
        env_file = os.path.join(server_dir, '.env')
        if not os.path.exists(env_file):
            logger.warning(".env file not found. Creating template...")

            env_template = """# Chat2Fill Environment Configuration
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./database/chat2fill.db
DEBUG=True
LOG_LEVEL=INFO
SESSION_TIMEOUT=24
MAX_BACKUPS=5
"""

            with open(env_file, 'w') as f:
                f.write(env_template)

            logger.info("Created .env template. Please add your GEMINI_API_KEY")

        # Check database directory
        db_dir = os.path.join(server_dir, 'database')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info("Created database directory")

        logger.info("Environment check completed")
        return True

    except Exception as e:
        logger.error(f"Error checking environment: {str(e)}")
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("CHAT2FILL DATABASE SETUP")
    print("=" * 60)

    steps = [
        ("Checking Environment", check_environment),
        ("Setting up Database", setup_database),
        ("Creating Sample Data", create_sample_data),
        ("Testing Database", test_database)
    ]

    success_count = 0

    for step_name, step_func in steps:
        print(f"\n--- {step_name} ---")
        try:
            success = step_func()
            if success:
                print(f"✅ {step_name} completed successfully")
                success_count += 1
            else:
                print(f"❌ {step_name} failed")
                if step_name == "Setting up Database":
                    print("Critical step failed. Exiting.")
                    sys.exit(1)
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {str(e)}")
            if step_name == "Setting up Database":
                print("Critical step failed. Exiting.")
                sys.exit(1)

    print("\n" + "=" * 60)
    print("SETUP COMPLETED")
    print("=" * 60)
    print(f"✅ {success_count}/{len(steps)} steps completed successfully")

    if success_count == len(steps):
        print("\n🎉 Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Add your GEMINI_API_KEY to the .env file")
        print("2. Run: python server.py")
        print("3. Run: python bridge.py")
        print("4. Start frontend: cd ../client && npm run dev")
        print("\nYour conversational interface is ready!")
    else:
        print("\n⚠️  Some steps failed. Please check the errors above.")

    print("\nDatabase file location: database/chat2fill.db")
    print("Log files: Check console output for any errors")

if __name__ == "__main__":
    main()

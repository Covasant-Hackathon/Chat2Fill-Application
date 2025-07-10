import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add the server directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import User, Form, FormField, Prompt, MultilingualContent, UserResponse, ConversationHistory, SystemLog
from database.services import DatabaseService, DatabaseContext
from database.config import db_config, initialize_database, check_database_health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseAdmin:
    """Database administration utility"""

    def __init__(self):
        self.db_config = db_config

    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            with DatabaseContext() as db_service:
                # Count all records
                stats = {
                    "users": db_service.db.query(User).count(),
                    "active_users": db_service.db.query(User).filter(User.is_active == True).count(),
                    "forms": db_service.db.query(Form).count(),
                    "active_forms": db_service.db.query(Form).filter(Form.is_active == True).count(),
                    "form_fields": db_service.db.query(FormField).count(),
                    "prompts": db_service.db.query(Prompt).count(),
                    "multilingual_content": db_service.db.query(MultilingualContent).count(),
                    "user_responses": db_service.db.query(UserResponse).count(),
                    "final_responses": db_service.db.query(UserResponse).filter(UserResponse.is_final == True).count(),
                    "conversation_messages": db_service.db.query(ConversationHistory).count(),
                    "system_logs": db_service.db.query(SystemLog).count()
                }

                # Get database file info
                db_info = self.db_config.get_database_info()
                stats.update(db_info)

                # Get language statistics
                language_stats = {}
                languages = db_service.db.query(MultilingualContent.language_code).distinct().all()
                for (lang,) in languages:
                    language_stats[lang] = db_service.db.query(MultilingualContent).filter(
                        MultilingualContent.language_code == lang
                    ).count()

                stats["languages"] = language_stats

                # Get recent activity
                recent_users = db_service.db.query(User).filter(
                    User.last_active >= datetime.now(timezone.utc) - timedelta(hours=24)
                ).count()
                stats["recent_active_users"] = recent_users

                return stats

        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {"error": str(e)}

    def list_users(self, active_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
        """List users with their details"""
        try:
            with DatabaseContext() as db_service:
                query = db_service.db.query(User)

                if active_only:
                    query = query.filter(User.is_active == True)

                users = query.order_by(User.created_at.desc()).limit(limit).all()

                return [
                    {
                        "id": user.id,
                        "session_id": user.session_id,
                        "preferred_language": user.preferred_language,
                        "created_at": user.created_at.isoformat(),
                        "last_active": user.last_active.isoformat(),
                        "is_active": user.is_active,
                        "forms_count": len(user.forms),
                        "responses_count": len(user.responses),
                        "conversations_count": len(user.conversations)
                    }
                    for user in users
                ]

        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return []

    def get_user_details(self, session_id: str) -> Dict[str, Any]:
        """Get detailed information about a user"""
        try:
            with DatabaseContext() as db_service:
                user = db_service.get_user_by_session(session_id)

                if not user:
                    return {"error": "User not found"}

                # Get user's forms
                forms = db_service.get_user_forms(user.id)

                # Get user's responses
                responses = db_service.get_user_responses(user.id)

                # Get conversation history
                conversations = db_service.get_conversation_history(user.id)

                return {
                    "user": {
                        "id": user.id,
                        "session_id": user.session_id,
                        "preferred_language": user.preferred_language,
                        "created_at": user.created_at.isoformat(),
                        "last_active": user.last_active.isoformat(),
                        "is_active": user.is_active
                    },
                    "forms": [
                        {
                            "id": form.id,
                            "url": form.url,
                            "form_type": form.form_type,
                            "title": form.title,
                            "parsed_at": form.parsed_at.isoformat(),
                            "is_active": form.is_active,
                            "fields_count": len(form.fields)
                        }
                        for form in forms
                    ],
                    "responses": [
                        {
                            "id": resp.id,
                            "form_id": resp.form_id,
                            "field_id": resp.field_id,
                            "response_text": resp.response_text,
                            "language_code": resp.language_code,
                            "confidence_score": resp.confidence_score,
                            "is_final": resp.is_final,
                            "responded_at": resp.responded_at.isoformat()
                        }
                        for resp in responses
                    ],
                    "conversations": [
                        {
                            "id": conv.id,
                            "message_type": conv.message_type,
                            "message_content": conv.message_content[:100] + "..." if len(conv.message_content) > 100 else conv.message_content,
                            "language_code": conv.language_code,
                            "timestamp": conv.timestamp.isoformat()
                        }
                        for conv in conversations
                    ]
                }

        except Exception as e:
            logger.error(f"Error getting user details: {str(e)}")
            return {"error": str(e)}

    def list_forms(self, user_session_id: str = None, form_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List forms with optional filtering"""
        try:
            with DatabaseContext() as db_service:
                query = db_service.db.query(Form)

                if user_session_id:
                    user = db_service.get_user_by_session(user_session_id)
                    if user:
                        query = query.filter(Form.user_id == user.id)

                if form_type:
                    query = query.filter(Form.form_type == form_type)

                forms = query.order_by(Form.parsed_at.desc()).limit(limit).all()

                return [
                    {
                        "id": form.id,
                        "user_id": form.user_id,
                        "url": form.url,
                        "form_type": form.form_type,
                        "title": form.title,
                        "description": form.description,
                        "parsed_at": form.parsed_at.isoformat(),
                        "is_active": form.is_active,
                        "fields_count": len(form.fields),
                        "responses_count": len(form.responses)
                    }
                    for form in forms
                ]

        except Exception as e:
            logger.error(f"Error listing forms: {str(e)}")
            return []

    def get_form_details(self, form_id: int) -> Dict[str, Any]:
        """Get detailed information about a form"""
        try:
            with DatabaseContext() as db_service:
                form = db_service.get_form_by_id(form_id)

                if not form:
                    return {"error": "Form not found"}

                # Get form fields
                fields = db_service.get_form_fields(form_id)

                # Get form responses
                responses = db_service.db.query(UserResponse).filter(
                    UserResponse.form_id == form_id
                ).all()

                return {
                    "form": {
                        "id": form.id,
                        "user_id": form.user_id,
                        "url": form.url,
                        "form_type": form.form_type,
                        "title": form.title,
                        "description": form.description,
                        "parsed_at": form.parsed_at.isoformat(),
                        "is_active": form.is_active,
                        "original_schema": form.original_schema
                    },
                    "fields": [
                        {
                            "id": field.id,
                            "name": field.field_name,
                            "type": field.field_type,
                            "label": field.field_label,
                            "placeholder": field.field_placeholder,
                            "required": field.is_required,
                            "options": field.field_options,
                            "order": field.field_order,
                            "prompts_count": len(field.prompts),
                            "responses_count": len(field.responses)
                        }
                        for field in fields
                    ],
                    "responses": [
                        {
                            "id": resp.id,
                            "user_id": resp.user_id,
                            "field_id": resp.field_id,
                            "response_text": resp.response_text,
                            "language_code": resp.language_code,
                            "confidence_score": resp.confidence_score,
                            "is_final": resp.is_final,
                            "responded_at": resp.responded_at.isoformat()
                        }
                        for resp in responses
                    ]
                }

        except Exception as e:
            logger.error(f"Error getting form details: {str(e)}")
            return {"error": str(e)}

    def cleanup_old_data(self, days: int = 30) -> Dict[str, Any]:
        """Clean up old data from the database"""
        try:
            with DatabaseContext() as db_service:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                # Count records to be deleted
                old_conversations = db_service.db.query(ConversationHistory).filter(
                    ConversationHistory.timestamp < cutoff_date
                ).count()

                old_logs = db_service.db.query(SystemLog).filter(
                    SystemLog.created_at < cutoff_date
                ).count()

                # Delete old records
                db_service.cleanup_old_data(days)

                return {
                    "status": "success",
                    "deleted_conversations": old_conversations,
                    "deleted_logs": old_logs,
                    "cutoff_date": cutoff_date.isoformat()
                }

        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
            return {"error": str(e)}

    def deactivate_inactive_users(self, hours: int = 24) -> Dict[str, Any]:
        """Deactivate users who have been inactive for specified hours"""
        try:
            with DatabaseContext() as db_service:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

                # Count users to be deactivated
                inactive_users = db_service.db.query(User).filter(
                    User.last_active < cutoff_time,
                    User.is_active == True
                ).count()

                # Deactivate users
                db_service.deactivate_inactive_users(hours)

                return {
                    "status": "success",
                    "deactivated_users": inactive_users,
                    "cutoff_time": cutoff_time.isoformat()
                }

        except Exception as e:
            logger.error(f"Error deactivating inactive users: {str(e)}")
            return {"error": str(e)}

    def export_user_data(self, session_id: str, output_file: str = None) -> Dict[str, Any]:
        """Export all data for a specific user"""
        try:
            user_data = self.get_user_details(session_id)

            if "error" in user_data:
                return user_data

            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"user_data_{session_id}_{timestamp}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)

            return {
                "status": "success",
                "output_file": output_file,
                "user_id": user_data["user"]["id"],
                "forms_count": len(user_data["forms"]),
                "responses_count": len(user_data["responses"]),
                "conversations_count": len(user_data["conversations"])
            }

        except Exception as e:
            logger.error(f"Error exporting user data: {str(e)}")
            return {"error": str(e)}

    def backup_database(self, backup_path: str = None) -> Dict[str, Any]:
        """Create a backup of the database"""
        try:
            backup_file = self.db_config.backup_database(backup_path)

            return {
                "status": "success",
                "backup_file": backup_file,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error backing up database: {str(e)}")
            return {"error": str(e)}

    def restore_database(self, backup_path: str) -> Dict[str, Any]:
        """Restore database from backup"""
        try:
            self.db_config.restore_database(backup_path)

            return {
                "status": "success",
                "restored_from": backup_path,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error restoring database: {str(e)}")
            return {"error": str(e)}

    def get_system_logs(self, level: str = None, user_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get system logs with optional filtering"""
        try:
            with DatabaseContext() as db_service:
                query = db_service.db.query(SystemLog)

                if level:
                    query = query.filter(SystemLog.log_level == level.upper())

                if user_id:
                    query = query.filter(SystemLog.user_id == user_id)

                logs = query.order_by(SystemLog.created_at.desc()).limit(limit).all()

                return [
                    {
                        "id": log.id,
                        "user_id": log.user_id,
                        "log_level": log.log_level,
                        "log_message": log.log_message,
                        "log_data": log.log_data,
                        "created_at": log.created_at.isoformat()
                    }
                    for log in logs
                ]

        except Exception as e:
            logger.error(f"Error getting system logs: {str(e)}")
            return []

def print_menu():
    """Print the admin menu"""
    print("\n" + "="*60)
    print("DATABASE ADMINISTRATION MENU")
    print("="*60)
    print("1. Database Statistics")
    print("2. List Users")
    print("3. Get User Details")
    print("4. List Forms")
    print("5. Get Form Details")
    print("6. Cleanup Old Data")
    print("7. Deactivate Inactive Users")
    print("8. Export User Data")
    print("9. Backup Database")
    print("10. Restore Database")
    print("11. View System Logs")
    print("12. Database Health Check")
    print("0. Exit")
    print("="*60)

def main():
    """Main admin interface"""
    admin = DatabaseAdmin()

    print("Database Administration Utility")
    print("Initializing database...")

    # Check database health
    health = check_database_health()
    if health["status"] != "healthy":
        print(f"Database health check failed: {health}")
        return

    while True:
        print_menu()
        choice = input("\nEnter your choice (0-12): ").strip()

        try:
            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                stats = admin.get_database_stats()
                print(f"\nDatabase Statistics:")
                print(json.dumps(stats, indent=2))
            elif choice == "2":
                active_only = input("Show only active users? (y/n): ").lower() == 'y'
                users = admin.list_users(active_only=active_only)
                print(f"\nUsers ({len(users)}):")
                for user in users:
                    print(f"  {user['session_id']}: {user['preferred_language']} - {user['created_at']}")
            elif choice == "3":
                session_id = input("Enter session ID: ").strip()
                details = admin.get_user_details(session_id)
                print(f"\nUser Details:")
                print(json.dumps(details, indent=2))
            elif choice == "4":
                user_session = input("Filter by user session ID (or press Enter): ").strip() or None
                form_type = input("Filter by form type (or press Enter): ").strip() or None
                forms = admin.list_forms(user_session_id=user_session, form_type=form_type)
                print(f"\nForms ({len(forms)}):")
                for form in forms:
                    print(f"  {form['id']}: {form['title']} - {form['form_type']}")
            elif choice == "5":
                form_id = int(input("Enter form ID: ").strip())
                details = admin.get_form_details(form_id)
                print(f"\nForm Details:")
                print(json.dumps(details, indent=2))
            elif choice == "6":
                days = int(input("Delete data older than how many days? (default: 30): ").strip() or "30")
                result = admin.cleanup_old_data(days)
                print(f"\nCleanup Result:")
                print(json.dumps(result, indent=2))
            elif choice == "7":
                hours = int(input("Deactivate users inactive for how many hours? (default: 24): ").strip() or "24")
                result = admin.deactivate_inactive_users(hours)
                print(f"\nDeactivation Result:")
                print(json.dumps(result, indent=2))
            elif choice == "8":
                session_id = input("Enter session ID to export: ").strip()
                output_file = input("Output file (or press Enter for auto-generated): ").strip() or None
                result = admin.export_user_data(session_id, output_file)
                print(f"\nExport Result:")
                print(json.dumps(result, indent=2))
            elif choice == "9":
                backup_path = input("Backup file path (or press Enter for auto-generated): ").strip() or None
                result = admin.backup_database(backup_path)
                print(f"\nBackup Result:")
                print(json.dumps(result, indent=2))
            elif choice == "10":
                backup_path = input("Enter backup file path: ").strip()
                result = admin.restore_database(backup_path)
                print(f"\nRestore Result:")
                print(json.dumps(result, indent=2))
            elif choice == "11":
                level = input("Log level (INFO, WARNING, ERROR, or press Enter for all): ").strip() or None
                logs = admin.get_system_logs(level=level)
                print(f"\nSystem Logs ({len(logs)}):")
                for log in logs[-10:]:  # Show last 10 logs
                    print(f"  [{log['log_level']}] {log['created_at']}: {log['log_message']}")
            elif choice == "12":
                health = check_database_health()
                print(f"\nDatabase Health:")
                print(json.dumps(health, indent=2))
            else:
                print("Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()

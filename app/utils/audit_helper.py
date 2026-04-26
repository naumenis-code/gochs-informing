import logging
import os
from datetime import datetime

# Set up logging configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO

# Create a directory for logs if it doesn't exist
log_directory = 'logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

log_file = os.path.join(log_directory, 'audit.log')
logging.basicConfig(filename=log_file, level=LOG_LEVEL, format=LOG_FORMAT)

# Audit log class for tracking actions
class AuditLogger:
    @staticmethod
    def log_action(user: str, action: str, details: str = ''):
        """
        Log a user action.
        :param user: Username of the user performing the action
        :param action: Description of the action
        :param details: Additional details about the action
        """
        logging.info(f'User: {user}, Action: {action}, Details: {details}')

    @staticmethod
    def log_system_change(change: str, details: str = ''):
        """
        Log a system change.
        :param change: Description of the system change
        :param details: Additional details about the change
        """
        logging.info(f'System Change: {change}, Details: {details}')

    @staticmethod
    def log_security_event(event: str, details: str = ''):
        """
        Log a security event.
        :param event: Description of the security event
        :param details: Additional details about the event
        """
        logging.warning(f'Security Event: {event}, Details: {details}')

# Example usage
if __name__ == '__main__':
    logger = AuditLogger()
    logger.log_action('naumenis-code', 'user_login', 'User logged in successfully.')
    logger.log_system_change('config_update', 'Updated the max login attempts setting.')
    logger.log_security_event('unauthorized_access_attempt', 'User: test_user tried to access admin panel.');

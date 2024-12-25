import subprocess
import re
from datetime import datetime, timezone
import time
import os
import urllib.parse
import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

class LogHandler:
    """Handler for managing application logs and error reporting"""
    
    def __init__(self, log_file="nullvad_checker.log", error_file="error_report.log"):
        self.log_file = log_file
        self.error_file = error_file
        
        # Configure main logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # File handler for all logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Error file handler for errors only
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s\n'
            'File: %(pathname)s\n'
            'Line: %(lineno)d\n'
            'Function: %(funcName)s\n'
            '-------------------------\n'
        )
        error_handler.setFormatter(error_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
    
    def get_system_info(self):
        """Gather system information for error reporting"""
        import platform
        import sys
        
        info = [
            "System Information:",
            f"OS: {platform.system()} {platform.version()}",
            f"Python Version: {sys.version}",
            f"Platform: {platform.platform()}",
            f"Machine: {platform.machine()}",
            f"Processor: {platform.processor()}",
            "-------------------------"
        ]
        return "\n".join(info)
    
    def prepare_error_report(self):
        """Prepare error report for email"""
        try:
            with open(self.error_file, 'r') as f:
                error_content = f.read()
            
            report = [
                "NullVad Checker Error Report",
                "=========================",
                "",
                self.get_system_info(),
                "",
                "Error Log:",
                "==========",
                error_content
            ]
            
            return "\n".join(report)
        except Exception as e:
            return f"Failed to prepare error report: {str(e)}"
    
    def clear_error_log(self):
        """Clear the error log file"""
        try:
            with open(self.error_file, 'w') as f:
                f.write("")
            return True
        except Exception:
            return False

class ProxyType(Enum):
    """Enum for supported proxy types"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

@dataclass
class ProxyConfig:
    """Data class for proxy configuration"""
    domain: str
    port: str
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: Optional[ProxyType] = None

    def to_url(self) -> str:
        """Convert proxy config to URL format"""
        if not self.proxy_type:
            raise ValueError("Proxy type must be set")
        
        url = f"{self.proxy_type.value}://"
        if self.username and self.password:
            url += f"{self.username}:{self.password}@"
        url += f"{self.domain}:{self.port}"
        return url

@dataclass
class AccountStatus:
    """Data class for account status information"""
    account_number: str
    is_valid: bool
    expiry_date: Optional[datetime] = None
    error_message: Optional[str] = None
    device_limit_reached: bool = False

class NullVadChecker:
    def __init__(self, data_dir: str = "."):
        """
        Initialize NullVadChecker with configurable data directory
        
        Args:
            data_dir: Directory to store data files (default: current directory)
        """
        self.data_dir = data_dir
        self.input_file = os.path.join(data_dir, 'nullvad_in.txt')
        self.output_file = os.path.join(data_dir, 'nullvad_working.txt')
        self.max_devices_file = os.path.join(data_dir, 'nullvad_max_devices.txt')
        self.proxy_config: Optional[ProxyConfig] = None
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        self._ensure_files_exist()
        
        # Initialize log handler
        self.log_handler = LogHandler()
        self.logger = self.log_handler.logger

    def _ensure_files_exist(self) -> None:
        """Ensure all necessary files exist."""
        files = [self.input_file, self.output_file, self.max_devices_file]
        for file in files:
            if not os.path.exists(file):
                with open(file, 'w') as f:
                    pass
                self.logger.info(f"Created empty file: {file}")

    def set_proxy(self, proxy_string: str, proxy_type: str) -> None:
        """
        Set proxy configuration from string
        
        Args:
            proxy_string: Proxy string in format "domain:port:username:password"
            proxy_type: Type of proxy (http, https, socks4, socks5)
        
        Raises:
            ValueError: If proxy format is invalid
        """
        if not proxy_string or not proxy_type:
            self.proxy_config = None
            return

        try:
            # Validate proxy type
            try:
                proxy_type_enum = ProxyType(proxy_type.lower())
            except ValueError:
                raise ValueError(f"Unsupported proxy type: {proxy_type}")

            # Parse proxy string
            parts = proxy_string.split(':')
            if len(parts) < 2:
                raise ValueError("Proxy must at least contain Domain:Port")
            
            self.proxy_config = ProxyConfig(
                domain=parts[0],
                port=parts[1],
                username=parts[2] if len(parts) > 2 else None,
                password=parts[3] if len(parts) > 3 else None,
                proxy_type=proxy_type_enum
            )
            
            self.logger.info(f"Proxy configured: {proxy_type} proxy at {parts[0]}:{parts[1]}")
                
        except Exception as e:
            self.logger.error(f"Failed to set proxy: {str(e)}")
            raise ValueError(f"Invalid proxy format: {str(e)}")

    def execute_command(self, command: str) -> Optional[str]:
        """
        Execute a command with proxy settings if configured
        
        Args:
            command: Command to execute
            
        Returns:
            Command output or None if execution failed
        """
        try:
            env = os.environ.copy()
            if self.proxy_config:
                proxy_url = self.proxy_config.to_url()
                if self.proxy_config.proxy_type in [ProxyType.HTTP, ProxyType.HTTPS]:
                    env['HTTP_PROXY'] = proxy_url
                    env['HTTPS_PROXY'] = proxy_url
                else:  # socks4 or socks5
                    env['ALL_PROXY'] = proxy_url
                    env['all_proxy'] = proxy_url
            
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                env=env
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command execution failed: {e.stderr}")
            return None

    def check_account_set(self, account: str) -> Tuple[bool, Optional[str]]:
        """
        Check if account can be logged in
        
        Args:
            account: Account number to check
            
        Returns:
            Tuple of (success, error_message)
        """
        if not account.strip():
            return False, "Empty account number"
            
        command = f'mullvad account login {account}'
        output = self.execute_command(command)
        
        if not output:
            return False, "Command execution failed"

        if f'Mullvad account "{account}" set' in output:
            self.logger.info(f"Account {account} set successfully")
            return True, None
        elif 'There are too many devices on the account.' in output:
            self.logger.warning(f"Account {account} has too many devices")
            with open(self.max_devices_file, 'a') as file:
                file.write(f"{account}\n")
            return False, "Too many devices"
        elif 'The account does not exist' in output:
            self.logger.info(f"Account {account} is invalid")
            return False, "Account does not exist"
            
        return False, "Unknown error"

    def check_account_validity(self, account: str) -> AccountStatus:
        """
        Check account validity and expiration
        
        Args:
            account: Account number to check
            
        Returns:
            AccountStatus object with validity information
        """
        command = 'mullvad account get'
        output = self.execute_command(command)
        
        if not output:
            return AccountStatus(account, False, error_message="Failed to get account info")

        # Extract expiration date
        match = re.search(r'Expires at:\s+(\d{4}-\d{2}-\d{2})', output)
        if not match:
            return AccountStatus(account, False, error_message="Could not find expiry date")

        expires_at = match.group(1)
        try:
            # Parse expiry date and set it to end of day in UTC
            expires_date = datetime.strptime(expires_at, '%Y-%m-%d')
            expires_date = expires_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
            
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            
            is_valid = expires_date >= now
            
            if is_valid:
                self.logger.info(f"Valid account found: {account}, expires {expires_at}")
                with open(self.output_file, 'a') as file:
                    file.write(f"{account} (Expires at: {expires_at})\n")
            else:
                self.logger.info(f"Expired account: {account}, expired {expires_at}")

            return AccountStatus(account, is_valid, expires_date)
            
        except Exception as e:
            self.logger.error(f"Error parsing expiry date: {e}")
            return AccountStatus(account, False, error_message=f"Error parsing expiry date: {e}")

    def logout_account(self) -> bool:
        """
        Logout current account
        
        Returns:
            True if logout successful, False otherwise
        """
        command = 'mullvad account logout'
        output = self.execute_command(command)
        if output:
            self.logger.info("Logged out successfully")
            return True
        self.logger.warning("Logout failed")
        return False

    def process_accounts(self) -> List[str]:
        """
        Read accounts from input file
        
        Returns:
            List of account numbers
        """
        try:
            if not os.path.exists(self.input_file):
                self.logger.warning(f"Input file {self.input_file} does not exist")
                return []

            with open(self.input_file, 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]
                self.logger.info(f"Loaded {len(accounts)} accounts from {self.input_file}")
                return accounts
                
        except Exception as e:
            self.logger.error(f"Error reading input file: {e}")
            return []

def main():
    checker = NullVadChecker()
    accounts = checker.process_accounts()
    
    if not accounts:
        logging.warning(f"No accounts found in {checker.input_file}")
        return

    for account in accounts:
        time.sleep(2)  # Rate limiting
        success, error = checker.check_account_set(account)
        if success:
            status = checker.check_account_validity(account)
            if status.is_valid:
                logging.info(f"Valid account: {account}, expires {status.expiry_date}")
            checker.logout_account()
        else:
            logging.info(f"Account check failed: {account}, error: {error}")
        time.sleep(1)  # Additional cooldown

if __name__ == '__main__':
    main()

# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
import utils

try:
    import requests
except Exception as exc:
    utils.fatal("Unable to import 'requests'.  "
                "You must install the 'requests' module.")

# Try to import keyring - make it optional
_keyring_available = False
try:
    import keyring
    _keyring_available = True
except ImportError:
    pass

from requests.auth import HTTPBasicAuth
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPushButton, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt

# Module-level credential cache - persists for the session only
_cached_username = None
_cached_password = None

# Module-level flag for certificate verification
_verify_ssl = True  # Start with verification enabled

# Module-level flag to disable keyring even if available
_keyring_disabled = False

# Keyring service identifier
KEYRING_SERVICE = "diff-review-http-auth"


def set_keyring_disabled(disabled):
    """
    Disable keyring usage even if available.
    
    Args:
        disabled: True to disable keyring, False to enable
    """
    global _keyring_disabled
    _keyring_disabled = disabled


def is_keyring_enabled():
    """
    Check if keyring is available and enabled.
    
    Returns:
        True if keyring can be used, False otherwise
    """
    return _keyring_available and not _keyring_disabled


class SSLVerificationDialog(QDialog):
    """Dialog to ask user whether to accept unverified SSL certificate"""

    def __init__(self, url, error_msg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SSL Certificate Verification Failed")
        self.setModal(True)
        self.accept_unverified = False

        layout = QVBoxLayout(self)

        # Warning icon and message
        warning_label = QLabel(
            f"WARNING: SSL Certificate verification failed for:\n{url}\n\n"
            f"Error: {error_msg}\n\n"
            "This could indicate:\n"
            "  * A self-signed certificate\n"
            "  * An expired certificate\n"
            "  * A man-in-the-middle attack\n\n"
            "Do you want to proceed without verification?\n"
            "(Not recommended for untrusted networks)"
        )
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        # Buttons
        button_layout = QHBoxLayout()

        accept_button = QPushButton("Accept and Continue (Insecure)")
        accept_button.clicked.connect(self.on_accept)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setDefault(True)  # Make cancel the default

        button_layout.addWidget(accept_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setMinimumWidth(500)

    def on_accept(self):
        """User chose to accept unverified certificate"""
        self.accept_unverified = True
        self.accept()


class BasicAuthDialog(QDialog):
    """Dialog for securely prompting for HTTP Basic Auth credentials"""

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Authentication Required")
        self.setModal(True)
        self.username = None
        self.password = None

        layout = QVBoxLayout(self)

        # Info label
        info_label = QLabel(f"Authentication required for:\n{url}")
        layout.addWidget(info_label)

        # Username field
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.username_field = QLineEdit()
        username_layout.addWidget(self.username_field)
        layout.addLayout(username_layout)

        # Password field
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.password_field)
        layout.addLayout(password_layout)

        # Remember credentials checkbox - only enable if keyring is available
        if is_keyring_enabled():
            self.remember_checkbox = QCheckBox("Remember credentials (stored securely in OS keyring)")
            self.remember_checkbox.setChecked(True)
        else:
            self.remember_checkbox = QCheckBox("Remember credentials (keyring unavailable - disabled)")
            self.remember_checkbox.setChecked(False)
            self.remember_checkbox.setEnabled(False)
        layout.addWidget(self.remember_checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Focus on username field
        self.username_field.setFocus()

        self.setMinimumWidth(400)

    def accept(self):
        """Store credentials when OK is clicked"""
        self.username = self.username_field.text()
        self.password = self.password_field.text()
        self.remember = self.remember_checkbox.isChecked()
        super().accept()


class FetchDesc(object):
    def __init__(self, url,
                 ack_insecure_cert,
                 require_auth=False,
                 parent_widget=None):
        """
        Initialize fetch descriptor

        Args:
            url: URL to fetch
            require_auth: If True, always prompt for credentials before fetching.
                         If False, only prompt if 401 response is received.
            parent_widget: Parent widget for auth dialog (optional)
        """
        self.url_               = url
        self.body_              = None
        self.http_code_         = None
        self.require_auth_      = require_auth
        self.parent_widget_     = parent_widget
        self.ack_insecure_cert_ = ack_insecure_cert

    def _get_cached_credentials(self):
        """Get cached credentials if available"""
        global _cached_username, _cached_password
        if _cached_username and _cached_password:
            return (_cached_username, _cached_password)
        return None

    def _get_keyring_credentials(self):
        """Retrieve credentials from OS keyring"""
        if not is_keyring_enabled():
            return None
        try:
            username = keyring.get_password(KEYRING_SERVICE, "username")
            if username:
                password = keyring.get_password(KEYRING_SERVICE, username)
                if password:
                    return (username, password)
        except Exception:
            pass
        return None

    def _store_keyring_credentials(self, username, password):
        """Store credentials in OS keyring"""
        if not is_keyring_enabled():
            return
        try:
            keyring.set_password(KEYRING_SERVICE, "username", username)
            keyring.set_password(KEYRING_SERVICE, username, password)
        except Exception:
            pass

    def _clear_keyring_credentials(self):
        """Clear credentials from OS keyring"""
        if not is_keyring_enabled():
            return
        try:
            username = keyring.get_password(KEYRING_SERVICE, "username")
            if username:
                keyring.delete_password(KEYRING_SERVICE, username)
                keyring.delete_password(KEYRING_SERVICE, "username")
        except Exception:
            pass

    def _cache_credentials(self, username, password):
        """Cache credentials for the session"""
        global _cached_username, _cached_password
        _cached_username = username
        _cached_password = password

    def _clear_cached_credentials(self):
        """Clear cached credentials"""
        global _cached_username, _cached_password
        _cached_username = None
        _cached_password = None

    def _prompt_for_credentials(self):
        """Prompt user for credentials using PyQt6 dialog"""
        dialog = BasicAuthDialog(self.url_, self.parent_widget_)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            username = dialog.username
            password = dialog.password
            remember = dialog.remember
            
            # Cache the credentials for this session
            self._cache_credentials(username, password)
            
            # Store in OS keyring if user chose to remember
            if remember:
                self._store_keyring_credentials(username, password)
            else:
                # Clear any existing keyring credentials
                self._clear_keyring_credentials()
            
            return (username, password)
        return None

    def fetch(self):
        """
        Fetch content from URL, prompting for auth if needed

        Uses cached credentials if available. Tries unauthenticated request first,
        then prompts for credentials only if server returns 401. Retries 
        authentication until success or user cancels. Tries with SSL verification 
        first, prompts user if verification fails.
        """
        global _verify_ssl

        if not self.ack_insecure_cert_:
            _verify_ssl = False
            # Suppress warnings for the rest of the session, because
            # it was requested.
            import warnings
            import urllib3
            warnings.filterwarnings('ignore', message='.*Unverified HTTPS.*')

        # Keep trying until success or user cancels
        while True:
            auth = None

            # Determine if we should use authentication
            # Check keyring first, then session cache
            cached = self._get_cached_credentials()
            if not cached:
                cached = self._get_keyring_credentials()
                if cached:
                    # Found in keyring, cache for this session
                    self._cache_credentials(*cached)
            
            if self.require_auth_ or cached:
                # Use cached credentials if available, or prompt if require_auth is True
                if cached:
                    auth = HTTPBasicAuth(*cached)
                else:
                    # require_auth is True but no cached credentials - prompt user
                    creds = self._prompt_for_credentials()
                    if not creds:
                        # User cancelled
                        self.body_      = None
                        self.http_code_ = 401
                        return
                    auth = HTTPBasicAuth(*creds)
            # Otherwise auth remains None for unauthenticated request

            # Make the request with current SSL verification setting
            try:
                response = requests.get(self.url_, auth=auth, verify=_verify_ssl)
            except requests.exceptions.SSLError as ssl_err:
                # SSL verification failed - ask user what to do
                if _verify_ssl:  # Only prompt if we haven't already disabled verification
                    dialog = SSLVerificationDialog(self.url_, str(ssl_err), self.parent_widget_)
                    if dialog.exec() == QDialog.DialogCode.Accepted and dialog.accept_unverified:
                        # User chose to accept unverified certificate
                        _verify_ssl = False
                        # Suppress warnings for the rest of the session
                        import warnings
                        import urllib3
                        warnings.filterwarnings('ignore', message='.*Unverified HTTPS.*')
                        # Retry without verification
                        try:
                            response = requests.get(self.url_, auth=auth, verify=False)
                        except requests.RequestException as e:
                            self.body_      = None
                            self.http_code_ = None
                            return
                    else:
                        # User cancelled SSL dialog - treat as cancel
                        self.body_      = None
                        self.http_code_ = 401
                        return
                else:
                    # SSL verification already disabled, but still got SSL error
                    self.body_      = None
                    self.http_code_ = None
                    return
            except requests.RequestException as e:
                self.body_      = None  # None --> Nothing fetched.
                self.http_code_ = None  # None --> Network error.
                return

            # Check response
            if response.status_code == 200:
                # Success!
                try:
                    self.body_ = response.text
                except Exception:
                    self.body_ = response.content.decode(errors="replace")
                finally:
                    self.http_code_ = response.status_code
                return
            elif response.status_code == 401:
                # Auth required or failed
                if auth is None:
                    # First 401 - server requires authentication
                    # Prompt for credentials and loop to retry
                    creds = self._prompt_for_credentials()
                    if not creds:
                        # User cancelled
                        self.body_      = None
                        self.http_code_ = 401
                        return
                    # Credentials cached by _prompt_for_credentials, will be used on retry
                else:
                    # Auth failed - clear cached credentials and keyring, then loop to retry
                    self._clear_cached_credentials()
                    self._clear_keyring_credentials()
                    # Loop will prompt again
            else:
                # Some other HTTP error - return it
                try:
                    self.body_ = response.text
                except Exception:
                    self.body_ = response.content.decode(errors="replace")
                finally:
                    self.http_code_ = response.status_code
                return

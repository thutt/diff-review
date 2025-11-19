# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
import requests
from requests.auth import HTTPBasicAuth
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt


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
        super().accept()


class FetchDesc(object):
    def __init__(self, url, require_auth=False, parent_widget=None):
        """
        Initialize fetch descriptor
        
        Args:
            url: URL to fetch
            require_auth: If True, always prompt for credentials before fetching.
                         If False, only prompt if 401 response is received.
            parent_widget: Parent widget for auth dialog (optional)
        """
        self.url_           = url
        self.body_          = None
        self.http_code_     = None
        self.require_auth_  = require_auth
        self.parent_widget_ = parent_widget
        self.username_      = None
        self.password_      = None

    def _prompt_for_credentials(self):
        """Prompt user for credentials using PyQt6 dialog"""
        dialog = BasicAuthDialog(self.url_, self.parent_widget_)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.username_ = dialog.username
            self.password_ = dialog.password
            return True
        return False

    def fetch(self):
        """
        Fetch content from URL, prompting for auth if needed
        
        If require_auth is True, prompts before first attempt.
        If require_auth is False, attempts fetch, and prompts only on 401.
        """
        auth = None
        
        # If auth is required upfront, prompt now
        if self.require_auth_:
            if not self._prompt_for_credentials():
                self.body_      = None
                self.http_code_ = None
                return
            auth = HTTPBasicAuth(self.username_, self.password_)
        
        # Make the request
        try:
            response = requests.get(self.url_, auth=auth)
        except requests.RequestException as e:
            self.body_      = None  # None --> Nothing fetched.
            self.http_code_ = None  # None --> Network error.
            return

        # If we get 401 and haven't prompted yet, prompt and retry
        if response.status_code == 401 and not self.require_auth_:
            if self._prompt_for_credentials():
                auth = HTTPBasicAuth(self.username_, self.password_)
                try:
                    response = requests.get(self.url_, auth=auth)
                except requests.RequestException as e:
                    self.body_      = None
                    self.http_code_ = None
                    return
            else:
                # User cancelled auth dialog
                self.body_      = None
                self.http_code_ = 401
                return

        try:
            self.body_ = response.text
        except Exception:
            self.body_ = response.content.decode(errors="replace")
        finally:
            self.http_code_ = response.status_code

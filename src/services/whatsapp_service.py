import time
import requests
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from src.core.config import WhatsAppConfig


class BaseWhatsAppProvider(ABC):
    """Abstract interface for WhatsApp delivery providers."""

    @abstractmethod
    def send_message(self, phone: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Send a WhatsApp message to a normalized E.164 phone number.
        Returns: (success, error_message)
        """
        pass

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Test configuration/connectivity for the provider."""
        pass


class MockWhatsAppProvider(BaseWhatsAppProvider):
    """Simulated WhatsApp provider for dry-runs and automated testing."""

    def __init__(self, simulate_failure: bool = False):
        self.simulate_failure = simulate_failure
        self.sent_messages = []

    def send_message(self, phone: str, message: str) -> Tuple[bool, Optional[str]]:
        if self.simulate_failure:
            return False, "Simulated dispatch failure"
        self.sent_messages.append({"phone": phone, "message": message, "timestamp": time.time()})
        return True, None

    def test_connection(self) -> Tuple[bool, str]:
        return True, "Mock WhatsApp provider is active (dry-run mode)."


class PyWhatKitProvider(BaseWhatsAppProvider):
    """WhatsApp Web automation provider using pywhatkit / webbrowser and pyautogui."""

    def __init__(self, wait_time: int = 15, close_time: int = 3):
        self.wait_time = wait_time
        self.close_time = close_time

    def send_message(self, phone: str, message: str) -> Tuple[bool, Optional[str]]:
        try:
            import pyautogui
            from urllib.parse import quote
            import webbrowser

            try:
                import pywhatkit
                # Send with tab_close=False so we can confirm with Enter before closing tab
                pywhatkit.sendwhatmsg_instantly(
                    phone_no=phone,
                    message=message,
                    wait_time=self.wait_time,
                    tab_close=False,
                    close_time=self.close_time
                )
            except ImportError:
                # Direct WhatsApp Web automation fallback (e.g., standalone .exe build)
                url = f"https://web.whatsapp.com/send?phone={phone}&text={quote(message)}"
                webbrowser.open(url)
                time.sleep(max(4, self.wait_time))
                pyautogui.press("enter")

            # Confirm sending with Enter while tab is still active, then close tab
            time.sleep(1.5)
            pyautogui.press("enter")
            time.sleep(self.close_time)
            pyautogui.hotkey("ctrl", "w")
            return True, None
        except Exception as e:
            return False, f"WhatsApp Web dispatch failed: {str(e)}"

    def test_connection(self) -> Tuple[bool, str]:
        try:
            import pyautogui
            try:
                import pywhatkit
                return True, "PyWhatKit and PyAutoGUI modules are available on this system."
            except ImportError:
                return True, "WhatsApp Web browser automation (PyAutoGUI) is ready."
        except ImportError as e:
            return False, f"WhatsApp Web automation dependency missing: {str(e)}"


class MetaCloudAPIProvider(BaseWhatsAppProvider):
    """Meta WhatsApp Cloud API provider (direct HTTP, zero-browser)."""

    def __init__(self, phone_number_id: str, access_token: str, api_version: str = "v20.0"):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.api_version = api_version
        self.endpoint = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    def send_message(self, phone: str, message: str) -> Tuple[bool, Optional[str]]:
        if not self.phone_number_id or not self.access_token:
            return False, "Meta Cloud API credentials are not set in .env"

        # Remove leading '+' for Meta API
        clean_recipient = phone.lstrip("+")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_recipient,
            "type": "text",
            "text": {"preview_url": False, "body": message}
        }

        try:
            res = requests.post(self.endpoint, headers=headers, json=payload, timeout=20)
            if res.status_code in (200, 201):
                return True, None
            data = res.json()
            err_msg = data.get("error", {}).get("message", res.text)
            return False, f"Meta API Error ({res.status_code}): {err_msg}"
        except Exception as e:
            return False, f"Meta API HTTP request failed: {str(e)}"

    def test_connection(self) -> Tuple[bool, str]:
        if not self.phone_number_id or not self.access_token:
            return False, "Meta Cloud API credentials missing (set META_WA_PHONE_NUMBER_ID and META_WA_ACCESS_TOKEN)."
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                display_phone = data.get("display_phone_number", self.phone_number_id)
                return True, f"Meta Cloud API verified for phone number: {display_phone}"
            return False, f"Meta Cloud API check failed ({res.status_code}): {res.text}"
        except Exception as e:
            return False, f"Meta Cloud API connection error: {str(e)}"


def get_whatsapp_provider(config: WhatsAppConfig, dry_run: bool = False) -> BaseWhatsAppProvider:
    """Factory to create appropriate WhatsApp provider instance."""
    if dry_run:
        return MockWhatsAppProvider()

    provider_name = config.provider.lower()
    if provider_name == "meta":
        return MetaCloudAPIProvider(
            phone_number_id=config.meta_phone_number_id,
            access_token=config.meta_access_token,
            api_version=config.meta_api_version
        )
    elif provider_name == "mock":
        return MockWhatsAppProvider()
    else:
        # Default is PyWhatKit
        return PyWhatKitProvider()

"""
CivicFix AI - SMS Provider Adapter Layer
Implements a pluggable adapter pattern for mobile OTP delivery.
Supports Twilio, Fast2SMS, and a transparent Demo provider for evaluation.
Never simulates fake real SMS delivery.
"""

import logging
import urllib.request
import urllib.parse
import json
from typing import Tuple, Dict, Any
from abc import ABC, abstractmethod
import config

logger = logging.getLogger("civicfix.sms")


def mask_phone_number(phone: str) -> str:
    """Masks phone number for privacy logging: +91 98****3210."""
    clean = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if len(clean) > 6:
        return clean[:4] + "*" * (len(clean) - 6) + clean[-2:]
    return clean[:2] + "****"


class BaseSMSProvider(ABC):
    """Abstract base adapter for SMS gateways."""

    @abstractmethod
    def send_otp(self, phone: str, otp: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Sends the OTP to the specified phone number.
        Returns: (success: bool, message: str, metadata: dict)
        """
        pass

    @abstractmethod
    def is_live_gateway(self) -> bool:
        """Returns True if this provider is connected to a real telecommunications carrier."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns human-readable name of the provider."""
        pass


class DemoSMSProvider(BaseSMSProvider):
    """
    Transparent Demonstration SMS Provider for local evaluation.
    Clearly discloses that it is a demo provider and logs the code securely
    to the server console and debug response without claiming live carrier delivery.
    """

    def is_live_gateway(self) -> bool:
        return False

    def get_provider_name(self) -> str:
        return "Local Demo Mode (No carrier credentials)"

    def send_otp(self, phone: str, otp: str) -> Tuple[bool, str, Dict[str, Any]]:
        masked = mask_phone_number(phone)
        logger.info("[DEMO SMS] Dispatching verification code %s to masked recipient %s", otp, masked)
        print(f"\n[DEMO SMS ADAPTER] Verification code for {masked}: >>> {otp} <<< (Expires in {config.OTP_EXPIRY_SECONDS}s)\n")

        return (
            True,
            f"Demo mode active: Live carrier gateway is unconfigured. For hackathon evaluation, your verification code is {otp}.",
            {"provider": "demo", "demo_otp": otp, "is_demo": True},
        )


class TwilioSMSProvider(BaseSMSProvider):
    """Production Twilio SMS Gateway Adapter."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    def is_live_gateway(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "Twilio Telecommunications"

    def send_otp(self, phone: str, otp: str) -> Tuple[bool, str, Dict[str, Any]]:
        masked = mask_phone_number(phone)
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        msg = f"Your CIVICFIX AI verification code is: {otp}. Valid for 5 minutes. Do not share."

        data = urllib.parse.urlencode({
            "To": phone,
            "From": self.from_number,
            "Body": msg,
        }).encode("utf-8")

        auth_str = f"{self.account_sid}:{self.auth_token}"
        import base64
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {b64_auth}")

        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                logger.info("Twilio SMS dispatched to %s (SID: %s)", masked, resp_data.get("sid"))
                return (True, f"Verification code sent via SMS to {masked}.", {"provider": "twilio", "sid": resp_data.get("sid")})
        except Exception as e:
            logger.error("Twilio SMS transmission failed for %s: %s", masked, e)
            return (False, f"SMS carrier delivery failed: {str(e)}", {"provider": "twilio", "error": str(e)})


class Fast2SMSSMSProvider(BaseSMSProvider):
    """Fast2SMS Gateway Adapter (India National Routes)."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def is_live_gateway(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "Fast2SMS India Gateway"

    def send_otp(self, phone: str, otp: str) -> Tuple[bool, str, Dict[str, Any]]:
        masked = mask_phone_number(phone)
        clean_num = "".join(filter(str.isdigit, phone))
        if clean_num.startswith("91") and len(clean_num) == 12:
            clean_num = clean_num[2:]

        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "route": "otp",
            "variables_values": otp,
            "numbers": clean_num,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "authorization": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                if resp_data.get("return") is True:
                    return (True, f"Verification code sent via SMS to {masked}.", {"provider": "fast2sms"})
                return (False, resp_data.get("message", "Fast2SMS carrier rejected request."), {"provider": "fast2sms"})
        except Exception as e:
            logger.error("Fast2SMS delivery error for %s: %s", masked, e)
            return (False, f"SMS carrier error: {str(e)}", {"provider": "fast2sms", "error": str(e)})


class DisabledSMSProvider(BaseSMSProvider):
    """Fallback when no SMS gateway is configured and demo mode is off."""

    def is_live_gateway(self) -> bool:
        return False

    def get_provider_name(self) -> str:
        return "Unconfigured (Disabled)"

    def send_otp(self, phone: str, otp: str) -> Tuple[bool, str, Dict[str, Any]]:
        return (
            False,
            "Live SMS verification is currently unavailable because telecommunications credentials are unconfigured.",
            {"provider": "disabled"},
        )


def get_sms_provider() -> BaseSMSProvider:
    """Factory creating the configured SMS provider instance."""
    provider_type = config.SMS_PROVIDER.lower().strip()

    if provider_type == "twilio" and config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
        return TwilioSMSProvider(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN, config.TWILIO_FROM_NUMBER)

    if provider_type == "fast2sms" and config.FAST2SMS_API_KEY:
        return Fast2SMSSMSProvider(config.FAST2SMS_API_KEY)

    if provider_type == "demo":
        return DemoSMSProvider()

    return DisabledSMSProvider()


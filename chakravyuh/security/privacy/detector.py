"""PII/PHI detection and masking."""
import re
from typing import List, Dict, Tuple, Optional
from enum import Enum

from chakravyuh.core.logging import logger


class PIIType(str, Enum):
    """Types of PII/PHI."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    DATE_OF_BIRTH = "date_of_birth"
    MEDICAL_RECORD = "medical_record"
    PATIENT_ID = "patient_id"


class PIIDetector:
    """Detect and mask PII/PHI in text."""

    def __init__(self):
        """Initialize PII detector with patterns."""
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )

        # Phone number patterns (US format)
        self.phone_patterns = [
            re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),  # 123-456-7890
            re.compile(r'\b\(\d{3}\)\s*\d{3}-\d{4}\b'),  # (123) 456-7890
            re.compile(r'\b\d{3}\.\d{3}\.\d{4}\b'),  # 123.456.7890
            re.compile(r'\b\d{10}\b'),  # 1234567890
        ]

        # SSN pattern
        self.ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

        # Credit card pattern (simplified)
        self.credit_card_pattern = re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        )

        # IP address pattern
        self.ip_pattern = re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        )

        # MAC address pattern
        self.mac_pattern = re.compile(
            r'\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b'
        )

        # Date of birth patterns
        self.dob_patterns = [
            re.compile(r'\b\d{1,2}/\d{1,2}/\d{4}\b'),  # MM/DD/YYYY
            re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),  # YYYY-MM-DD
        ]

    def detect_email(self, text: str) -> List[Tuple[str, PIIType]]:
        """Detect email addresses."""
        matches = []
        for match in self.email_pattern.finditer(text):
            matches.append((match.group(), PIIType.EMAIL))
        return matches

    def detect_phone(self, text: str) -> List[Tuple[str, PIIType]]:
        """Detect phone numbers."""
        matches = []
        for pattern in self.phone_patterns:
            for match in pattern.finditer(text):
                matches.append((match.group(), PIIType.PHONE))
        return matches

    def detect_ssn(self, text: str) -> List[Tuple[str, PIIType]]:
        """Detect SSN."""
        matches = []
        for match in self.ssn_pattern.finditer(text):
            matches.append((match.group(), PIIType.SSN))
        return matches

    def detect_credit_card(self, text: str) -> List[Tuple[str, PIIType]]:
        """Detect credit card numbers."""
        matches = []
        for match in self.credit_card_pattern.finditer(text):
            # Basic validation (Luhn check would be better)
            card = match.group().replace("-", "").replace(" ", "")
            if len(card) == 16:
                matches.append((match.group(), PIIType.CREDIT_CARD))
        return matches

    def detect_ip(self, text: str) -> List[Tuple[str, PIIType]]:
        """Detect IP addresses."""
        matches = []
        for match in self.ip_pattern.finditer(text):
            # Validate IP range
            parts = match.group().split(".")
            if all(0 <= int(p) <= 255 for p in parts):
                matches.append((match.group(), PIIType.IP_ADDRESS))
        return matches

    def detect_mac(self, text: str) -> List[Tuple[str, PIIType]]:
        """Detect MAC addresses."""
        matches = []
        for match in self.mac_pattern.finditer(text):
            matches.append((match.group(), PIIType.MAC_ADDRESS))
        return matches

    def detect_dob(self, text: str) -> List[Tuple[str, PIIType]]:
        """Detect dates of birth."""
        matches = []
        for pattern in self.dob_patterns:
            for match in pattern.finditer(text):
                matches.append((match.group(), PIIType.DATE_OF_BIRTH))
        return matches

    def detect_all(self, text: str) -> List[Tuple[str, PIIType]]:
        """
        Detect all PII/PHI in text.

        Args:
            text: Text to scan

        Returns:
            List of (value, type) tuples
        """
        all_matches = []
        all_matches.extend(self.detect_email(text))
        all_matches.extend(self.detect_phone(text))
        all_matches.extend(self.detect_ssn(text))
        all_matches.extend(self.detect_credit_card(text))
        all_matches.extend(self.detect_ip(text))
        all_matches.extend(self.detect_mac(text))
        all_matches.extend(self.detect_dob(text))

        # Remove duplicates
        seen = set()
        unique_matches = []
        for value, pii_type in all_matches:
            key = (value, pii_type)
            if key not in seen:
                seen.add(key)
                unique_matches.append((value, pii_type))

        return unique_matches

    def mask_text(self, text: str, mask_char: str = "*") -> Tuple[str, List[Dict[str, str]]]:
        """
        Mask PII/PHI in text.

        Args:
            text: Text to mask
            mask_char: Character to use for masking

        Returns:
            Tuple of (masked_text, list of masked items)
        """
        matches = self.detect_all(text)
        masked_text = text
        masked_items = []

        for value, pii_type in matches:
            # Create mask
            if pii_type == PIIType.EMAIL:
                parts = value.split("@")
                masked = f"{parts[0][0]}{mask_char * (len(parts[0]) - 1)}@{parts[1]}"
            elif pii_type == PIIType.SSN:
                masked = f"XXX-XX-{value[-4:]}"
            elif pii_type == PIIType.CREDIT_CARD:
                masked = f"****-****-****-{value[-4:]}"
            elif pii_type == PIIType.PHONE:
                masked = f"XXX-XXX-{value[-4:]}"
            else:
                masked = mask_char * len(value)

            masked_text = masked_text.replace(value, masked)
            masked_items.append({
                "original": value,
                "masked": masked,
                "type": pii_type.value,
            })

        if masked_items:
            logger.info(f"Masked {len(masked_items)} PII/PHI items in text")

        return masked_text, masked_items

    def should_redact(self, text: str, threshold: int = 3) -> bool:
        """
        Determine if text should be redacted based on PII count.

        Args:
            text: Text to check
            threshold: Minimum number of PII items to trigger redaction

        Returns:
            True if text should be redacted
        """
        matches = self.detect_all(text)
        return len(matches) >= threshold

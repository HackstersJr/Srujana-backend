"""
Utility functions and helper classes for the CareCloud AI system.
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import yaml


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """
    Setup logging configuration.

    Args:
        level: Logging level
        log_file: Optional log file path
        format_string: Optional custom format string
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[
            logging.StreamHandler(),
            *([logging.FileHandler(log_file)] if log_file else []),
        ],
    )


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, "r") as f:
            if config_path.endswith(".json"):
                return json.load(f)
            elif config_path.endswith((".yml", ".yaml")):
                return yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_path}")
    except Exception as e:
        raise ValueError(f"Failed to load config from {config_path}: {str(e)}")


def save_config(config: Dict[str, Any], config_path: str) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary
        config_path: Path to save configuration
    """
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, "w") as f:
            if config_path.endswith(".json"):
                json.dump(config, f, indent=2)
            elif config_path.endswith((".yml", ".yaml")):
                yaml.dump(config, f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported config file format: {config_path}")
    except Exception as e:
        raise ValueError(f"Failed to save config to {config_path}: {str(e)}")


def ensure_directory(directory_path: str) -> None:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        directory_path: Path to directory
    """
    os.makedirs(directory_path, exist_ok=True)


def get_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """
    Get hash of a file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm to use

    Returns:
        File hash
    """
    hash_algo = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_algo.update(chunk)

    return hash_algo.hexdigest()


def generate_unique_id() -> str:
    """
    Generate a unique identifier.

    Returns:
        Unique ID string
    """
    return str(uuid.uuid4())


def timestamp() -> str:
    """
    Get current timestamp as string.

    Returns:
        Current timestamp
    """
    return datetime.now().isoformat()


class FileUtils:
    """Utility class for file operations."""

    @staticmethod
    def read_text_file(file_path: str, encoding: str = "utf-8") -> str:
        """
        Read text file content.

        Args:
            file_path: Path to file
            encoding: File encoding

        Returns:
            File content
        """
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()

    @staticmethod
    def write_text_file(file_path: str, content: str, encoding: str = "utf-8") -> None:
        """
        Write content to text file.

        Args:
            file_path: Path to file
            content: Content to write
            encoding: File encoding
        """
        ensure_directory(os.path.dirname(file_path))
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def read_json_file(file_path: str) -> Dict[str, Any]:
        """
        Read JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            JSON data
        """
        with open(file_path, "r") as f:
            return json.load(f)

    @staticmethod
    def write_json_file(file_path: str, data: Dict[str, Any], indent: int = 2) -> None:
        """
        Write data to JSON file.

        Args:
            file_path: Path to JSON file
            data: Data to write
            indent: JSON indentation
        """
        ensure_directory(os.path.dirname(file_path))
        with open(file_path, "w") as f:
            json.dump(data, f, indent=indent)


class TextUtils:
    """Utility class for text processing."""

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = " ".join(text.split())

        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

        return text.strip()

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text (simple implementation).

        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords

        Returns:
            List of keywords
        """
        # Simple keyword extraction - in practice, you'd use NLP libraries
        words = text.lower().split()

        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
        }

        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        # Count frequency
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:max_keywords]]


class ValidationUtils:
    """Utility class for data validation."""

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
        return re.match(pattern, url) is not None

    @staticmethod
    def validate_required_fields(
        data: Dict[str, Any], required_fields: List[str]
    ) -> List[str]:
        """
        Validate that required fields are present in data.

        Args:
            data: Data dictionary
            required_fields: List of required field names

        Returns:
            List of missing fields
        """
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)
        return missing_fields


class PerformanceTimer:
    """Context manager for measuring execution time."""

    def __init__(self, name: str = "Operation"):
        """
        Initialize timer.

        Args:
            name: Name of the operation being timed
        """
        self.name = name
        self.start_time = None
        self.end_time = None
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        """Start timing."""
        self.start_time = datetime.now()
        self.logger.info(f"Started {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log duration."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        self.logger.info(f"Completed {self.name} in {duration:.2f} seconds")

    def get_duration(self) -> Optional[float]:
        """
        Get duration in seconds.

        Returns:
            Duration in seconds or None if not completed
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

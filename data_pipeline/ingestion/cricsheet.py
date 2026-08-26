"""
Cricsheet Data Ingestion
========================

Downloads and manages historical cricket data from Cricsheet.

Cricsheet provides ball-by-ball cricket data in JSON/YAML format.
Source: https://cricsheet.org/downloads/
Terms: Data is freely available for non-commercial use with attribution.

Data format (JSON):
{
  "info": {
    "teams": ["India", "Australia"],
    "dates": ["2023-01-01"],
    "venue": "Melbourne Cricket Ground",
    "match_type": "T20I",
    "toss": {"winner": "India", "decision": "field"},
    "players": {
      "India": ["Virat Kohli", "Rohit Sharma", ...],
      "Australia": ["Steve Smith", "David Warner", ...]
    }
  },
  "innings": [
    {
      "team": "Australia",
      "overs": [
        {
          "over": 0,
          "deliveries": [
            {
              "batter": "David Warner",
              "bowler": "Jasprit Bumrah",
              "runs": {"batter": 4, "extras": 0, "total": 4},
              "wickets": [...]  // optional
            }
          ]
        }
      ]
    }
  ]
}
"""

import json
import os
import logging
import hashlib
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# Cricsheet download URLs
CRICSHEET_BASE_URL = "https://cricsheet.org/downloads"
CRICSHEET_MATCHES = {
    "t20i": f"{CRICSHEET_BASE_URL}/t20i_json.zip",
    "odi": f"{CRICSHEET_BASE_URL}/odi_json.zip",
    "test": f"{CRICSHEET_BASE_URL}/test_json.zip",
    "ipl": f"{CRICSHEET_BASE_URL}/ipl_json.zip",
    "t20s": f"{CRICSHEET_BASE_URL}/t20s_json.zip",
}


class CricsheetIngestor:
    """
    Downloads and manages Cricsheet data files.
    
    Stores raw ZIP files in data/raw/ and extracts JSON files
    into data/raw/<format>/ for processing.
    """
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.checksums_file = self.data_dir / "checksums.json"
        self._checksums = self._load_checksums()
    
    def _load_checksums(self) -> dict:
        """Load previously recorded file checksums."""
        if self.checksums_file.exists():
            with open(self.checksums_file, "r") as f:
                return json.load(f)
        return {}
    
    def _save_checksums(self):
        """Save checksums to track downloaded files."""
        with open(self.checksums_file, "w") as f:
            json.dump(self._checksums, f, indent=2)
    
    def _file_checksum(self, filepath: Path) -> str:
        """Compute MD5 checksum of a file."""
        hasher = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def download(self, format_type: str, force: bool = False) -> Path:
        """
        Download Cricsheet data for a given format.
        
        Args:
            format_type: One of 't20i', 'odi', 'test', 'ipl', 't20s'
            force: Force re-download even if checksum matches
        
        Returns:
            Path to the downloaded ZIP file
        """
        format_type = format_type.lower()
        if format_type not in CRICSHEET_MATCHES:
            raise ValueError(
                f"Unknown format '{format_type}'. "
                f"Available: {list(CRICSHEET_MATCHES.keys())}"
            )
        
        url = CRICSHEET_MATCHES[format_type]
        zip_path = self.data_dir / f"{format_type}_json.zip"
        
        # Check if already downloaded and checksum matches
        if zip_path.exists() and not force:
            current_checksum = self._file_checksum(zip_path)
            stored_checksum = self._checksums.get(format_type)
            if current_checksum == stored_checksum:
                logger.info(f"Cricsheet {format_type} data already exists (checksum matches)")
                return zip_path
        
        logger.info(f"Downloading Cricsheet {format_type} data from {url}")
        
        try:
            response = requests.get(url, stream=True, timeout=120)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if progress % 10 < 1:
                            logger.info(f"  Progress: {progress:.0f}%")
            
            # Verify it's actually a ZIP file (not HTML)
            with open(zip_path, "rb") as f:
                header = f.read(4)
            if header != b"PK\x03\x04":
                logger.warning(f"Downloaded file is not a valid ZIP for {format_type} (got {header[:4]}). "
                              f"The download may be blocked by the server. "
                              f"Please download manually from https://cricsheet.org/downloads/ "
                              f"and place the ZIP at {zip_path}")
                # Try to use existing JSON files instead
                extract_dir = self.data_dir / format_type
                if extract_dir.exists():
                    json_count = len(list(extract_dir.glob("*.json")))
                    if json_count > 0:
                        logger.info(f"Using {json_count} existing JSON files from {extract_dir}")
                        return extract_dir
                raise RuntimeError(
                    f"Downloaded file is not a valid ZIP. "
                    f"Please download manually from https://cricsheet.org/downloads/ "
                    f"and place at {zip_path}"
                )
            
            # Record checksum
            checksum = self._file_checksum(zip_path)
            self._checksums[format_type] = checksum
            self._save_checksums()
            
            logger.info(f"Downloaded {format_type} data: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
            return zip_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download {format_type} data: {e}")
            raise
    
    def extract(self, format_type: str, force: bool = False) -> Path:
        """
        Extract downloaded ZIP into a directory of JSON files.
        
        Args:
            format_type: One of 't20i', 'odi', 'test', 'ipl', 't20s'
            force: Force re-extraction
        
        Returns:
            Path to the directory containing JSON files
        """
        import zipfile
        
        format_type = format_type.lower()
        zip_path = self.data_dir / f"{format_type}_json.zip"
        extract_dir = self.data_dir / format_type
        
        # Check if already extracted (even without ZIP)
        if extract_dir.exists() and not force:
            json_count = len(list(extract_dir.glob("*.json")))
            if json_count > 0:
                logger.info(f"Cricsheet {format_type} already extracted: {json_count} files")
                return extract_dir
        
        if not zip_path.exists():
            logger.info(f"ZIP not found for {format_type}, downloading...")
            self.download(format_type)
        
        logger.info(f"Extracting {format_type} data...")
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        
        json_count = len(list(extract_dir.glob("*.json")))
        logger.info(f"Extracted {json_count} JSON files to {extract_dir}")
        return extract_dir
    
    def load_match(self, json_path: str | Path) -> dict:
        """
        Load a single match JSON file.
        
        Returns:
            Parsed match data dictionary
        """
        with open(json_path, "r") as f:
            return json.load(f)
    
    def list_matches(self, format_type: str) -> list[Path]:
        """
        List all extracted JSON match files for a format.
        
        Returns:
            List of paths to JSON files
        """
        format_type = format_type.lower()
        extract_dir = self.data_dir / format_type
        
        if not extract_dir.exists():
            return []
        
        return sorted(extract_dir.glob("*.json"))
    
    def get_match_count(self, format_type: str) -> int:
        """Get the number of extracted matches for a format."""
        return len(self.list_matches(format_type))
    
    def summary(self) -> dict:
        """Get a summary of all downloaded data."""
        summary = {}
        for format_type in CRICSHEET_MATCHES:
            zip_path = self.data_dir / f"{format_type}_json.zip"
            extract_dir = self.data_dir / format_type
            
            summary[format_type] = {
                "zip_exists": zip_path.exists(),
                "zip_size_mb": (
                    round(zip_path.stat().st_size / 1024 / 1024, 1)
                    if zip_path.exists() else 0
                ),
                "extracted": extract_dir.exists(),
                "match_count": self.get_match_count(format_type),
            }
        
        return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    ingestor = CricsheetIngestor()
    
    # Example: download and extract T20I data
    # ingestor.download("t20i")
    # ingestor.extract("t20i")
    
    print("Cricsheet Ingestion Summary:")
    print(json.dumps(ingestor.summary(), indent=2))

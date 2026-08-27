"""Entry point: python -m data_pipeline.audit"""
from dotenv import load_dotenv
load_dotenv()
from data_pipeline.audit.runner import run_audit
import sys

if __name__ == "__main__":
    sys.exit(run_audit())

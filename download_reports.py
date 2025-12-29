#!/usr/bin/env python3
"""
Download script for ESG/CSRD reports from banks.

This script provides instructions for downloading the 2024 annual reports for:
- Allied Irish Banks (AIB)
- BBVA
- Groupe BPCE

Since direct download URLs change frequently, this script provides
manual download instructions for each bank.
"""

from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Report details
REPORTS = [
    {
        "company": "AIB",
        "full_name": "Allied Irish Banks",
        "country": "Ireland",
        "report_name": "2024 Annual Financial Report",
        "filename": "AIB_2024_Annual_Report.pdf",
        "url": None,  # Will need to be updated with actual URL
        "investor_page": "https://www.aib.ie/investorrelations/financial-information"
    },
    {
        "company": "BBVA",
        "full_name": "BBVA",
        "country": "Spain",
        "report_name": "2024 Consolidated Management Report",
        "filename": "BBVA_2024_Management_Report.pdf",
        "url": None,  # Will need to be updated with actual URL
        "investor_page": "https://shareholdersandinvestors.bbva.com/financials/financial-reports/"
    },
    {
        "company": "BPCE",
        "full_name": "Groupe BPCE",
        "country": "France",
        "report_name": "2024 Universal Registration Document",
        "filename": "BPCE_2024_Registration_Document.pdf",
        "url": None,  # Will need to be updated with actual URL
        "investor_page": "https://www.groupebpce.com/en/investors/financial-publications"
    }
]


def check_existing_reports(output_dir: Path) -> dict:
    """Check which reports already exist."""
    existing = {}
    for report in REPORTS:
        filepath = output_dir / report["filename"]
        existing[report["company"]] = filepath.exists()
        if filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            existing[f"{report['company']}_size"] = size_mb
    return existing


def main():
    """Main download instruction function."""
    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    logger.info("="*80)
    logger.info("ESG REPORT DOWNLOAD INSTRUCTIONS - 2024 Annual Reports")
    logger.info("="*80)
    logger.info(f"Output directory: {reports_dir.absolute()}\n")
    
    # Check existing reports
    existing = check_existing_reports(reports_dir)
    existing_count = sum(1 for k, v in existing.items() if not k.endswith('_size') and v)
    
    if existing_count > 0:
        logger.info(f"✓ Found {existing_count} existing report(s):\n")
        for report in REPORTS:
            if existing[report["company"]]:
                size = existing.get(f"{report['company']}_size", 0)
                logger.info(f"  ✓ {report['filename']} ({size:.1f} MB)")
        logger.info("")
    
    if existing_count < len(REPORTS):
        logger.info(f"Please download {len(REPORTS) - existing_count} report(s) manually:\n")
        logger.info("="*80)
        
        for i, report in enumerate(REPORTS, 1):
            if not existing[report["company"]]:
                logger.info(f"\n{i}. {report['full_name']} ({report['country']})")
                logger.info(f"   Report: {report['report_name']}")
                logger.info(f"   URL: {report['investor_page']}")
                logger.info(f"   Save as: {reports_dir}/{report['filename']}")
                logger.info(f"   {'-'*76}")
        
        logger.info("\n" + "="*80)
        logger.info("DOWNLOAD INSTRUCTIONS:")
        logger.info("="*80)
        logger.info("\n1. Visit each investor relations page above")
        logger.info("2. Look for '2024 Annual Report' or 'Sustainability Report'")
        logger.info("3. Download the PDF and save with the exact filename shown")
        logger.info("4. Save all reports in the 'reports/' directory")
        
        logger.info("\n⚠ NOTE: Some 2024 reports may not be published yet.")
        logger.info("   You can use 2023 reports for testing if needed.")
    else:
        logger.info("="*80)
        logger.info("✓ ALL REPORTS READY!")
        logger.info("="*80)
    
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS:")
    logger.info("="*80)
    logger.info("\nOnce you have the PDFs, run extraction with:")
    logger.info("\n  # Agent mode (default - autonomous AI with tools)")
    logger.info("  python3 main.py --pdf reports/AIB_2024_Annual_Report.pdf --company AIB --year 2024")
    logger.info("\n  # Simple mode (basic extraction)")
    logger.info("  python3 main.py --pdf reports/AIB_2024_Annual_Report.pdf --company AIB --year 2024 --mode simple")
    logger.info("\n" + "="*80)


if __name__ == "__main__":
    main()

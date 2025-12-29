"""Main execution script for ESG data extraction - Agent Mode by Default."""
import argparse
import sys
from pathlib import Path
import logging
from typing import Optional

# Agent mode is default, simple mode is fallback
from agent_workflow import run_agent_extraction
from extraction_workflow import run_extraction
from database import save_results, export_to_csv
from models import ESG_INDICATORS, get_indicator_by_code
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function - defaults to autonomous agent mode."""
    parser = argparse.ArgumentParser(
        description="Extract ESG indicators from CSRD reports using autonomous AI agent"
    )
    
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to PDF report file"
    )
    
    parser.add_argument(
        "--company",
        required=True,
        help="Company name"
    )
    
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Report year"
    )
    
    parser.add_argument(
        "--indicators",
        nargs="+",
        help="Specific indicator codes to extract (default: all)"
    )
    
    parser.add_argument(
        "--output",
        help="Output CSV path (default: outputs/COMPANY_YEAR_esg_data.csv)"
    )
    
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save to database"
    )
    
    parser.add_argument(
        "--mode",
        choices=["agent", "simple"],
        default="agent",
        help="Extraction mode: 'agent' (autonomous AI with tools, DEFAULT) or 'simple' (basic extraction)"
    )
    
    args = parser.parse_args()
    
    # Validate PDF path
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {args.pdf}")
        sys.exit(1)
    
    # Filter indicators if specified
    indicators_to_extract = None
    if args.indicators:
        indicators_to_extract = []
        for code in args.indicators:
            indicator = get_indicator_by_code(code)
            if not indicator:
                logger.error(f"Invalid indicator code: {code}")
                sys.exit(1)
            indicators_to_extract.append(indicator)
    
    # Log extraction mode
    mode_desc = "🤖 AGENT MODE - Autonomous AI with tools" if args.mode == "agent" else "📋 SIMPLE MODE - Basic extraction"
    logger.info(f"\n{'='*80}")
    logger.info(f"ESG DATA EXTRACTION - {mode_desc}")
    logger.info(f"{'='*80}")
    logger.info(f"Company: {args.company}")
    logger.info(f"Year: {args.year}")
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info(f"{'='*80}\n")
    
    # Run extraction - agent mode by default
    if args.mode == "simple":
        logger.info("Using simple extraction mode (basic workflow)")
        result = run_extraction(
            pdf_path=str(pdf_path),
            company_name=args.company,
            report_year=args.year,
            indicators=indicators_to_extract
        )
    else:
        logger.info("Using agent mode - AI will autonomously decide how to extract data")
        result = run_agent_extraction(
            pdf_path=str(pdf_path),
            company_name=args.company,
            report_year=args.year,
            indicators=indicators_to_extract
        )
    
    if result["status"] == "error":
        logger.error(f"Extraction failed: {result['errors']}")
        sys.exit(1)
    
    # Display results
    extracted_values = result["extracted_values"]
    logger.info(f"\n{'='*80}")
    logger.info(f"EXTRACTION COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Company: {args.company}")
    logger.info(f"Year: {args.year}")
    logger.info(f"Total indicators extracted: {len(extracted_values)}")
    
    # Count by confidence
    high_conf = sum(1 for v in extracted_values if v.confidence > 0.7)
    medium_conf = sum(1 for v in extracted_values if 0.4 <= v.confidence <= 0.7)
    low_conf = sum(1 for v in extracted_values if v.confidence < 0.4)
    
    logger.info(f"High confidence (>0.7): {high_conf}")
    logger.info(f"Medium confidence (0.4-0.7): {medium_conf}")
    logger.info(f"Low confidence (<0.4): {low_conf}")
    logger.info(f"{'='*80}\n")
    
    # Print detailed results
    for value in extracted_values:
        logger.info(f"{value.indicator_code}: {value.value or 'Not found'} "
                   f"(confidence: {value.confidence:.2f})")
    
    # Save to database
    if not args.no_save:
        logger.info("\nSaving to database...")
        save_results(args.company, args.year, extracted_values)
        logger.info("✓ Saved to database")
    
    # Export to CSV
    if args.output:
        output_path = args.output
    else:
        output_path = settings.outputs_dir / f"{args.company.replace(' ', '_')}_{args.year}_esg_data.csv"
    
    logger.info(f"\nExporting to CSV: {output_path}")
    export_to_csv(str(output_path), args.company, args.year)
    logger.info(f"✓ CSV exported to {output_path}")
    
    logger.info(f"\n{'='*80}")
    logger.info("EXTRACTION COMPLETE - SUCCESS")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    main()

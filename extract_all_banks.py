"""Batch extraction script for all three banks (AIB, BBVA, BPCE)."""
import sys
from pathlib import Path
import logging
from datetime import datetime

from extraction_workflow import run_extraction
from database import save_results, export_to_csv, DatabaseManager
from utils import calculate_extraction_quality, create_extraction_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Define the three banks
BANKS = [
    {
        "name": "Allied Irish Banks",
        "short_name": "AIB",
        "filename": "AIB_2024.pdf",
        "year": 2024
    },
    {
        "name": "BBVA",
        "short_name": "BBVA",
        "filename": "BBVA_2024.pdf",
        "year": 2024
    },
    {
        "name": "Groupe BPCE",
        "short_name": "BPCE",
        "filename": "BPCE_2024.pdf",
        "year": 2024
    }
]


def check_reports_exist():
    """Check if all required PDF reports exist."""
    missing = []
    for bank in BANKS:
        pdf_path = Path("reports") / bank["filename"]
        if not pdf_path.exists():
            missing.append(bank["filename"])
    
    return missing


def extract_all_banks():
    """Extract ESG data from all three banks."""
    
    print("\n" + "="*80)
    print("ESG DATA EXTRACTION - BATCH PROCESSING")
    print("Processing 3 banks × 20 indicators = 60 total values")
    print("="*80 + "\n")
    
    # Check if reports exist
    missing = check_reports_exist()
    if missing:
        print("⚠️  Missing PDF reports:")
        for filename in missing:
            print(f"  - reports/{filename}")
        print("\nPlease download these reports first:")
        print("  AIB: https://www.aib.ie (Investor Relations)")
        print("  BBVA: https://shareholdersandinvestors.bbva.com")
        print("  BPCE: https://www.groupebpce.com")
        print("\nSave them to the reports/ directory and try again.")
        return False
    
    results_summary = []
    total_start_time = datetime.now()
    
    # Process each bank
    for i, bank in enumerate(BANKS, 1):
        print(f"\n{'='*80}")
        print(f"BANK {i}/3: {bank['name']}")
        print(f"{'='*80}")
        
        pdf_path = Path("reports") / bank["filename"]
        
        try:
            # Run extraction
            result = run_extraction(
                pdf_path=str(pdf_path),
                company_name=bank["name"],
                report_year=bank["year"]
            )
            
            if result["status"] == "success":
                extracted_values = result["extracted_values"]
                
                # Calculate quality
                quality = calculate_extraction_quality(extracted_values)
                
                # Save to database
                logger.info(f"Saving {bank['name']} results to database...")
                save_results(bank["name"], bank["year"], extracted_values)
                
                # Generate individual CSV
                csv_filename = f"{bank['short_name']}_{bank['year']}_esg_data.csv"
                csv_path = export_to_csv(
                    f"outputs/{csv_filename}",
                    bank["name"],
                    bank["year"]
                )
                
                # Generate report
                report_path = f"outputs/{bank['short_name']}_{bank['year']}_report.txt"
                create_extraction_report(
                    company_name=bank["name"],
                    report_year=bank["year"],
                    extracted_values=extracted_values,
                    output_path=report_path
                )
                
                results_summary.append({
                    "bank": bank["name"],
                    "status": "success",
                    "total": len(extracted_values),
                    "quality": quality,
                    "csv": csv_filename
                })
                
                print(f"\n✓ {bank['name']} completed successfully")
                print(f"  Total indicators: {len(extracted_values)}")
                print(f"  Coverage: {quality['coverage']*100:.1f}%")
                print(f"  Average confidence: {quality['avg_confidence']:.2f}")
                print(f"  Quality score: {quality['quality_score']:.2f}")
                print(f"  CSV: outputs/{csv_filename}")
                print(f"  Report: {report_path}")
            
            else:
                results_summary.append({
                    "bank": bank["name"],
                    "status": "error",
                    "error": result.get("errors", ["Unknown error"])
                })
                print(f"\n✗ {bank['name']} failed")
                print(f"  Errors: {result.get('errors', [])}")
        
        except Exception as e:
            logger.error(f"Error processing {bank['name']}: {e}")
            results_summary.append({
                "bank": bank["name"],
                "status": "error",
                "error": str(e)
            })
            print(f"\n✗ {bank['name']} failed: {e}")
    
    # Generate combined CSV with all 60 values
    print(f"\n{'='*80}")
    print("GENERATING COMBINED OUTPUT")
    print(f"{'='*80}")
    
    combined_csv = export_to_csv("outputs/all_banks_combined_2024.csv")
    print(f"\n✓ Combined CSV exported: {combined_csv}")
    
    # Final summary
    total_time = (datetime.now() - total_start_time).total_seconds()
    
    print(f"\n{'='*80}")
    print("BATCH EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"\nTotal processing time: {total_time/60:.1f} minutes")
    print(f"\nResults Summary:")
    
    success_count = sum(1 for r in results_summary if r["status"] == "success")
    total_indicators = sum(r.get("total", 0) for r in results_summary if r["status"] == "success")
    
    for r in results_summary:
        if r["status"] == "success":
            print(f"  ✓ {r['bank']}: {r['total']} indicators (quality: {r['quality']['quality_score']:.2f})")
        else:
            print(f"  ✗ {r['bank']}: Failed")
    
    print(f"\nTotal: {success_count}/{len(BANKS)} banks successful")
    print(f"Total indicators extracted: {total_indicators}")
    print(f"\nOutput files:")
    print(f"  - Individual CSVs: outputs/AIB_2024_esg_data.csv, etc.")
    print(f"  - Combined CSV: outputs/all_banks_combined_2024.csv")
    print(f"  - Reports: outputs/*_report.txt")
    
    # Database stats
    db = DatabaseManager()
    stats = db.get_summary_stats()
    print(f"\nDatabase statistics:")
    print(f"  Total records: {stats['total_records']}")
    print(f"  Unique companies: {stats['unique_companies']}")
    print(f"  Average confidence: {stats['average_confidence']}")
    
    print(f"\n{'='*80}")
    print("SUCCESS! All extractions complete.")
    print(f"{'='*80}\n")
    
    return True


if __name__ == "__main__":
    success = extract_all_banks()
    sys.exit(0 if success else 1)

"""Example script demonstrating how to use the extraction system."""
from extraction_workflow import run_extraction
from database import save_results, export_to_csv
from models import ESG_INDICATORS, get_indicator_by_code
from utils import calculate_extraction_quality, create_extraction_report

# Example 1: Extract all indicators from a report
def example_full_extraction():
    """Extract all 20 indicators from a report."""
    print("Example 1: Full Extraction")
    print("="*80)
    
    result = run_extraction(
        pdf_path="reports/AIB_2024.pdf",
        company_name="Allied Irish Banks",
        report_year=2024
    )
    
    print(f"Status: {result['status']}")
    print(f"Total indicators: {result['total_indicators']}")
    print(f"Extracted values: {len(result['extracted_values'])}")
    
    # Calculate quality metrics
    quality = calculate_extraction_quality(result['extracted_values'])
    print(f"Quality score: {quality['quality_score']}")
    
    # Save to database
    save_results("Allied Irish Banks", 2024, result["extracted_values"])
    
    # Export to CSV
    csv_path = export_to_csv("outputs/AIB_2024_full.csv", "Allied Irish Banks", 2024)
    print(f"Exported to: {csv_path}")


# Example 2: Extract specific indicators only
def example_selective_extraction():
    """Extract only specific indicators."""
    print("\nExample 2: Selective Extraction")
    print("="*80)
    
    # Select specific indicators
    indicators = [
        get_indicator_by_code("E1-1"),  # Scope 1 emissions
        get_indicator_by_code("E1-2"),  # Scope 2 emissions
        get_indicator_by_code("S1-1"),  # Workforce
    ]
    
    result = run_extraction(
        pdf_path="reports/BBVA_2024.pdf",
        company_name="BBVA",
        report_year=2024,
        indicators=indicators
    )
    
    print(f"Status: {result['status']}")
    print(f"Requested: {len(indicators)} indicators")
    print(f"Extracted: {len(result['extracted_values'])} values")
    
    # Print results
    for value in result['extracted_values']:
        print(f"{value.indicator_code}: {value.value} (confidence: {value.confidence:.2f})")


# Example 3: Process multiple companies
def example_batch_processing():
    """Process multiple companies in batch."""
    print("\nExample 3: Batch Processing")
    print("="*80)
    
    companies = [
        {"name": "Allied Irish Banks", "file": "AIB_2024.pdf", "year": 2024},
        {"name": "BBVA", "file": "BBVA_2024.pdf", "year": 2024},
        {"name": "Groupe BPCE", "file": "BPCE_2024.pdf", "year": 2024},
    ]
    
    all_results = []
    
    for company in companies:
        print(f"\nProcessing {company['name']}...")
        
        result = run_extraction(
            pdf_path=f"reports/{company['file']}",
            company_name=company['name'],
            report_year=company['year']
        )
        
        if result['status'] == 'success':
            # Save to database
            save_results(company['name'], company['year'], result['extracted_values'])
            
            # Track results
            all_results.append({
                'company': company['name'],
                'total': len(result['extracted_values']),
                'quality': calculate_extraction_quality(result['extracted_values'])
            })
            
            print(f"  ✓ Completed: {len(result['extracted_values'])} indicators")
        else:
            print(f"  ✗ Failed: {result.get('errors', [])}")
    
    # Export combined CSV
    csv_path = export_to_csv("outputs/all_banks_2024.csv")
    print(f"\nCombined export: {csv_path}")
    
    # Summary
    print("\nSummary:")
    for r in all_results:
        print(f"  {r['company']}: {r['total']} indicators, quality: {r['quality']['quality_score']}")


# Example 4: Generate detailed report
def example_generate_report():
    """Generate a detailed extraction report."""
    print("\nExample 4: Generate Report")
    print("="*80)
    
    result = run_extraction(
        pdf_path="reports/AIB_2024.pdf",
        company_name="Allied Irish Banks",
        report_year=2024
    )
    
    if result['status'] == 'success':
        # Create detailed report
        report = create_extraction_report(
            company_name="Allied Irish Banks",
            report_year=2024,
            extracted_values=result['extracted_values'],
            output_path="outputs/AIB_2024_report.txt"
        )
        
        print(report)


# Example 5: API usage example
def example_api_usage():
    """Example of using the FastAPI endpoint."""
    print("\nExample 5: API Usage")
    print("="*80)
    
    print("To use the API:")
    print("\n1. Start the server:")
    print("   python api.py")
    print("\n2. Make a POST request:")
    print("""
curl -X POST "http://localhost:8000/extract" \\
  -H "Content-Type: application/json" \\
  -d '{
    "company_name": "Allied Irish Banks",
    "report_year": 2024,
    "report_path": "reports/AIB_2024.pdf"
  }'
    """)
    
    print("\n3. Get results:")
    print("""
curl "http://localhost:8000/results/Allied Irish Banks/2024"
    """)
    
    print("\n4. Export to CSV:")
    print("""
curl "http://localhost:8000/export/csv?company=Allied Irish Banks&year=2024" -o results.csv
    """)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ESG DATA EXTRACTION - USAGE EXAMPLES")
    print("="*80)
    
    print("\nThis file contains example code for using the extraction system.")
    print("Uncomment the examples you want to run.\n")
    
    # Uncomment the examples you want to run:
    
    # example_full_extraction()
    # example_selective_extraction()
    # example_batch_processing()
    # example_generate_report()
    example_api_usage()
    
    print("\n" + "="*80)
    print("For more information, see README.md")
    print("="*80 + "\n")

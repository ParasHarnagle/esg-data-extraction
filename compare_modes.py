"""Compare agent mode vs orchestrated mode on same document."""
import sys
import time
from pathlib import Path

from extraction_workflow import run_extraction
from agent_workflow import run_agent_extraction
from models import get_indicator_by_code
from utils import calculate_extraction_quality


def compare_modes(pdf_path: str, company: str, year: int):
    """Run both modes and compare results."""
    
    print("\n" + "="*80)
    print("AGENT MODE vs ORCHESTRATED MODE COMPARISON")
    print("="*80)
    
    # Test with just 3 indicators for quick comparison
    test_indicators = [
        get_indicator_by_code("E1-1"),  # Scope 1 emissions
        get_indicator_by_code("S1-1"),  # Workforce
        get_indicator_by_code("G1-1"),  # Board size
    ]
    
    print(f"\nTesting with {len(test_indicators)} indicators:")
    for ind in test_indicators:
        print(f"  - {ind.code.value}: {ind.name}")
    
    # Run Orchestrated Mode
    print("\n" + "-"*80)
    print("1️⃣  ORCHESTRATED MODE (Predefined workflow)")
    print("-"*80)
    
    start = time.time()
    orchestrated_result = run_extraction(
        pdf_path=pdf_path,
        company_name=company,
        report_year=year,
        indicators=test_indicators
    )
    orchestrated_time = time.time() - start
    
    orchestrated_quality = calculate_extraction_quality(
        orchestrated_result.get("extracted_values", [])
    )
    
    print(f"\n✓ Orchestrated Mode Complete")
    print(f"  Time: {orchestrated_time:.1f} seconds")
    print(f"  Quality Score: {orchestrated_quality['quality_score']:.2f}")
    print(f"  Average Confidence: {orchestrated_quality['avg_confidence']:.2f}")
    
    # Print results
    print(f"\n  Results:")
    for val in orchestrated_result.get("extracted_values", []):
        print(f"    {val.indicator_code}: {val.value or 'Not found'} (confidence: {val.confidence:.2f})")
    
    # Run Agent Mode
    print("\n" + "-"*80)
    print("2️⃣  AGENT MODE (Autonomous with tools)")
    print("-"*80)
    print("Agent will decide which tools to use...\n")
    
    start = time.time()
    agent_result = run_agent_extraction(
        pdf_path=pdf_path,
        company_name=company,
        report_year=year,
        indicators=test_indicators
    )
    agent_time = time.time() - start
    
    agent_quality = calculate_extraction_quality(
        agent_result.get("extracted_values", [])
    )
    
    print(f"\n✓ Agent Mode Complete")
    print(f"  Time: {agent_time:.1f} seconds")
    print(f"  Quality Score: {agent_quality['quality_score']:.2f}")
    print(f"  Average Confidence: {agent_quality['avg_confidence']:.2f}")
    
    # Print results
    print(f"\n  Results:")
    for val in agent_result.get("extracted_values", []):
        print(f"    {val.indicator_code}: {val.value or 'Not found'} (confidence: {val.confidence:.2f})")
    
    # Comparison
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    print(f"\n{'Metric':<25} {'Orchestrated':<20} {'Agent':<20}")
    print("-"*65)
    print(f"{'Time':<25} {orchestrated_time:.1f}s{'':<15} {agent_time:.1f}s")
    print(f"{'Speed':<25} {'Baseline':<20} {f'{agent_time/orchestrated_time:.1f}x slower':<20}")
    print(f"{'Quality Score':<25} {orchestrated_quality['quality_score']:.2f}{'':<17} {agent_quality['quality_score']:.2f}")
    print(f"{'Avg Confidence':<25} {orchestrated_quality['avg_confidence']:.2f}{'':<17} {agent_quality['avg_confidence']:.2f}")
    print(f"{'Found/Total':<25} {orchestrated_quality['found']}/{orchestrated_quality['total']}{'':<17} {agent_quality['found']}/{agent_quality['total']}")
    
    # Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    if orchestrated_quality['quality_score'] >= agent_quality['quality_score']:
        print("\n✓ Use ORCHESTRATED MODE for this document")
        print("  Reasons:")
        print(f"  - Similar or better quality ({orchestrated_quality['quality_score']:.2f} vs {agent_quality['quality_score']:.2f})")
        print(f"  - {orchestrated_time/agent_time:.1f}x faster")
        print("  - Lower cost (fewer LLM calls)")
    else:
        print("\n✓ Use AGENT MODE for this document")
        print("  Reasons:")
        print(f"  - Better quality ({agent_quality['quality_score']:.2f} vs {orchestrated_quality['quality_score']:.2f})")
        print("  - More adaptive to document structure")
        improvement = (agent_quality['quality_score'] - orchestrated_quality['quality_score']) * 100
        print(f"  - {improvement:.1f}% improvement worth the extra time")
    
    print("\n" + "="*80 + "\n")


def main():
    """Main comparison function."""
    if len(sys.argv) < 4:
        print("Usage: python compare_modes.py <pdf_path> <company> <year>")
        print("\nExample:")
        print("  python compare_modes.py reports/AIB_2024.pdf 'Allied Irish Banks' 2024")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    company = sys.argv[2]
    year = int(sys.argv[3])
    
    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    compare_modes(pdf_path, company, year)


if __name__ == "__main__":
    main()

"""Utility functions for ESG data extraction."""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


def format_number(value: Optional[float], decimals: int = 2) -> str:
    """Format a number with thousand separators.
    
    Args:
        value: Number to format
        decimals: Number of decimal places
    
    Returns:
        Formatted string
    """
    if value is None:
        return "N/A"
    
    return f"{value:,.{decimals}f}"


def normalize_company_name(name: str) -> str:
    """Normalize company name for consistency.
    
    Args:
        name: Company name
    
    Returns:
        Normalized name
    """
    # Remove common suffixes and normalize
    name = name.strip()
    replacements = {
        " plc": "",
        " PLC": "",
        " Ltd": "",
        " Limited": "",
        " Inc.": "",
        " Corporation": ""
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    return name.strip()


def calculate_extraction_quality(extracted_values: List[Any]) -> Dict[str, Any]:
    """Calculate quality metrics for extraction results.
    
    Args:
        extracted_values: List of ExtractedValue objects
    
    Returns:
        Dictionary with quality metrics
    """
    if not extracted_values:
        return {
            "total": 0,
            "found": 0,
            "not_found": 0,
            "avg_confidence": 0.0,
            "quality_score": 0.0
        }
    
    total = len(extracted_values)
    found = sum(1 for v in extracted_values if v.confidence > 0.3)
    not_found = total - found
    
    confidences = [v.confidence for v in extracted_values if v.confidence > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    # Quality score: weighted by confidence and coverage
    coverage = found / total if total > 0 else 0
    quality_score = (coverage * 0.6) + (avg_confidence * 0.4)
    
    return {
        "total": total,
        "found": found,
        "not_found": not_found,
        "coverage": round(coverage, 2),
        "avg_confidence": round(avg_confidence, 2),
        "quality_score": round(quality_score, 2)
    }


def create_extraction_report(
    company_name: str,
    report_year: int,
    extracted_values: List[Any],
    output_path: Optional[str] = None
) -> str:
    """Create a detailed extraction report.
    
    Args:
        company_name: Company name
        report_year: Report year
        extracted_values: List of extracted values
        output_path: Path to save report (optional)
    
    Returns:
        Report text
    """
    quality = calculate_extraction_quality(extracted_values)
    
    report_lines = [
        "="*80,
        f"ESG DATA EXTRACTION REPORT",
        "="*80,
        f"Company: {company_name}",
        f"Report Year: {report_year}",
        f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "QUALITY METRICS",
        "-"*80,
        f"Total Indicators: {quality['total']}",
        f"Successfully Extracted: {quality['found']}",
        f"Not Found: {quality['not_found']}",
        f"Coverage: {quality['coverage']*100:.1f}%",
        f"Average Confidence: {quality['avg_confidence']:.2f}",
        f"Overall Quality Score: {quality['quality_score']:.2f}",
        "",
        "DETAILED RESULTS",
        "-"*80,
    ]
    
    # Group by category
    by_category = {}
    for value in extracted_values:
        code = value.indicator_code
        category = code.split('-')[0]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(value)
    
    for category, values in sorted(by_category.items()):
        report_lines.append(f"\n{category} Indicators:")
        report_lines.append("-"*40)
        
        for value in values:
            status = "✓" if value.confidence > 0.5 else "✗"
            report_lines.append(
                f"{status} {value.indicator_code}: {value.value or 'Not found'} "
                f"({value.confidence:.2f})"
            )
    
    report_lines.append("\n" + "="*80)
    
    report_text = "\n".join(report_lines)
    
    # Save if path provided
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report_text)
        logger.info(f"Report saved to {output_path}")
    
    return report_text


def merge_csv_files(csv_paths: List[str], output_path: str) -> str:
    """Merge multiple CSV files into one.
    
    Args:
        csv_paths: List of CSV file paths
        output_path: Output path for merged CSV
    
    Returns:
        Path to merged CSV
    """
    dfs = []
    
    for path in csv_paths:
        if Path(path).exists():
            df = pd.read_csv(path)
            dfs.append(df)
        else:
            logger.warning(f"CSV file not found: {path}")
    
    if not dfs:
        raise ValueError("No valid CSV files found")
    
    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df.to_csv(output_path, index=False)
    
    logger.info(f"Merged {len(dfs)} CSV files into {output_path}")
    return output_path


def validate_pdf_report(pdf_path: str) -> Dict[str, Any]:
    """Validate if a PDF is suitable for extraction.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Validation results
    """
    from pdf_parser import PDFParser
    
    path = Path(pdf_path)
    
    if not path.exists():
        return {
            "valid": False,
            "error": "File not found"
        }
    
    if not path.suffix.lower() == '.pdf':
        return {
            "valid": False,
            "error": "Not a PDF file"
        }
    
    try:
        with PDFParser(pdf_path) as parser:
            metadata = parser.metadata
            
            # Check if PDF has text
            sample_text = parser.extract_text_by_page(0)
            has_text = len(sample_text.strip()) > 100
            
            # Check page count
            reasonable_pages = 50 <= metadata.total_pages <= 1000
            
            return {
                "valid": has_text and reasonable_pages,
                "total_pages": metadata.total_pages,
                "has_text": has_text,
                "reasonable_size": reasonable_pages,
                "title": metadata.title,
                "warnings": [] if (has_text and reasonable_pages) else [
                    "No text content" if not has_text else "",
                    f"Unusual page count: {metadata.total_pages}" if not reasonable_pages else ""
                ]
            }
    
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


def export_to_json(
    data: Dict[str, Any],
    output_path: str,
    pretty: bool = True
) -> str:
    """Export data to JSON file.
    
    Args:
        data: Data to export
        output_path: Output file path
        pretty: Whether to format JSON prettily
    
    Returns:
        Path to JSON file
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        if pretty:
            json.dump(data, f, indent=2, default=str)
        else:
            json.dump(data, f, default=str)
    
    logger.info(f"Exported JSON to {output_path}")
    return output_path


def get_company_info() -> Dict[str, Dict[str, str]]:
    """Get information about supported companies.
    
    Returns:
        Dictionary with company information
    """
    return {
        "AIB": {
            "full_name": "Allied Irish Banks",
            "url": "https://www.aib.ie",
            "report_location": "Investor Relations → Reports & Presentations → Annual Report 2024"
        },
        "BBVA": {
            "full_name": "BBVA",
            "url": "https://shareholdersandinvestors.bbva.com",
            "report_location": "Reports → Annual Reports → 2024 Management Report"
        },
        "BPCE": {
            "full_name": "Groupe BPCE",
            "url": "https://www.groupebpce.com",
            "report_location": "Publications → Universal registration documents"
        }
    }

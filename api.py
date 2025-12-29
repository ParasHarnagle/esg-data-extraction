"""FastAPI application for ESG data extraction."""
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional, List
import time
import logging
import json
import shutil
from datetime import datetime

from models import (
    ExtractionRequest,
    ExtractionResponse,
    ExtractedValue,
    ESG_INDICATORS,
    get_indicator_by_code
)
from extraction_workflow import run_extraction
from agent_workflow import run_agent_extraction  # Agent-based extraction
from fast_extractor import FastVectorExtractor  # NEW: Fast vector-based extraction
from database import DatabaseManager, save_results, export_to_csv
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ESG Data Extraction API",
    description="AI-powered extraction of ESG indicators from CSRD sustainability reports",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = DatabaseManager()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ESG Data Extraction API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "extraction": "/extract",
            "indicators": "/indicators",
            "results": "/results",
            "export": "/export",
            "stats": "/stats"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected"
    }


@app.get("/indicators")
async def list_indicators():
    """List all available ESG indicators."""
    indicators_list = []
    
    for indicator in ESG_INDICATORS:
        indicators_list.append({
            "code": indicator.code.value,
            "name": indicator.name,
            "category": indicator.category.value,
            "description": indicator.description,
            "expected_unit": indicator.expected_unit,
            "keywords": indicator.keywords
        })
    
    return {
        "total_indicators": len(indicators_list),
        "indicators": indicators_list
    }


@app.post("/api/extract")
async def extract_esg_data_upload(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    report_year: int = Form(...),
    indicators: Optional[str] = Form(None),
    mode: str = Form("agent")
):
    """Extract ESG indicators from uploaded PDF file.
    
    Args:
        file: Uploaded PDF file
        company_name: Company name
        report_year: Report year
        indicators: Optional JSON array of indicator codes
        mode: Extraction mode (agent or simple)
    
    Returns:
        Extraction response with extracted values
    """
    logger.info(f"Received file upload for {company_name} - {report_year}")
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    # Save uploaded file temporarily
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    temp_pdf_path = upload_dir / f"{company_name}_{report_year}_{file.filename}"
    
    try:
        with temp_pdf_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(e)}"
        )
    
    # Parse indicators if provided
    indicators_to_extract = None
    if indicators:
        try:
            indicator_codes = json.loads(indicators)
            indicators_to_extract = []
            for code in indicator_codes:
                indicator = get_indicator_by_code(code)
                if not indicator:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid indicator code: {code}"
                    )
                indicators_to_extract.append(indicator)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid indicators format. Expected JSON array."
            )
    
    # Run extraction
    start_time = time.time()
    
    try:
        if mode == "simple":
            logger.info(f"📋 Using SIMPLE mode - basic extraction workflow")
            result = run_extraction(
                pdf_path=str(temp_pdf_path),
                company_name=company_name,
                report_year=report_year,
                indicators=indicators_to_extract
            )
        elif mode == "fast":
            logger.info(f"⚡ Using FAST mode - vector search + single LLM call per indicator")
            from pdf_parser import PDFParser
            
            # Initialize fast extractor
            fast_extractor = FastVectorExtractor()
            pdf_parser = PDFParser(str(temp_pdf_path))
            
            # Use all indicators if none specified
            indicators_list = indicators_to_extract or ESG_INDICATORS
            
            # Fast batch extraction
            extracted_results = fast_extractor.extract_batch(
                indicators=indicators_list,
                pdf_path=str(temp_pdf_path),
                pdf_parser=pdf_parser
            )
            
            # Format results
            result = {
                "status": "success",
                "extracted_values": [
                    {
                        "indicator_code": r.indicator_code,
                        "value": r.value,
                        "unit": r.unit,
                        "confidence": r.confidence,
                        "source_page": r.source_page,
                        "extraction_method": r.extraction_method
                    }
                    for r in extracted_results
                ],
                "errors": []
            }
        else:
            logger.info(f"🤖 Using AGENT mode - AI will autonomously decide tools to use")
            result = run_agent_extraction(
                pdf_path=str(temp_pdf_path),
                company_name=company_name,
                report_year=report_year,
                indicators=indicators_to_extract
            )
        
        processing_time = time.time() - start_time
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Extraction failed: {result.get('errors', [])}"
            )
        
        # Save to database - use the original ExtractedValue objects
        if mode == "fast":
            # For fast mode, use the original extracted_results objects
            extracted_values = extracted_results
            save_results(company_name, report_year, extracted_values)
        else:
            # For agent mode, extracted_values are already in the correct format
            extracted_values = result["extracted_values"]
            save_results(company_name, report_year, extracted_values)
        
        # Export to CSV - create both a timestamped version and a latest version
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Timestamped version for historical record
        csv_filename_timestamped = f"{company_name.replace(' ', '_')}_{report_year}_esg_data_{timestamp}.csv"
        csv_path_timestamped = settings.outputs_dir / csv_filename_timestamped
        export_to_csv(str(csv_path_timestamped), company_name, report_year)
        
        # Latest version (overwrites previous)
        csv_filename = f"{company_name.replace(' ', '_')}_{report_year}_esg_data_latest.csv"
        csv_path = settings.outputs_dir / csv_filename
        export_to_csv(str(csv_path), company_name, report_year)
        
        # Prepare response
        response = {
            "company_name": company_name,
            "report_year": report_year,
            "total_indicators": len(extracted_values),
            "extracted_values": [
                {
                    "indicator_code": val.indicator_code,
                    "value": val.value,
                    "numeric_value": val.numeric_value,
                    "unit": val.unit,
                    "source_page": val.source_page,
                    "confidence": val.confidence,
                    "explanation": val.explanation
                }
                for val in extracted_values
            ],
            "processing_time": round(processing_time, 2),
            "csv_files": {
                "latest": csv_filename,
                "timestamped": csv_filename_timestamped
            },
            "status": "success",
            "errors": result.get("errors", [])
        }
        
        logger.info(f"Extraction completed in {processing_time:.2f}s")
        
        return response
    
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    finally:
        # Cleanup temporary file
        if temp_pdf_path.exists():
            temp_pdf_path.unlink()


@app.get("/api/download/{filename}")
async def download_csv(filename: str):
    """Download exported CSV file."""
    csv_path = settings.outputs_dir / filename
    
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}"
        )
    
    return FileResponse(
        path=csv_path,
        filename=filename,
        media_type="text/csv"
    )


@app.post("/extract", response_model=ExtractionResponse)
async def extract_esg_data(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks
):
    """Extract ESG indicators from a company report.
    
    Args:
        request: Extraction request with company info and report path/URL
        background_tasks: Background tasks for async processing
    
    Returns:
        Extraction response with extracted values
    """
    logger.info(f"Received extraction request for {request.company_name} - {request.report_year}")
    
    # Validate inputs
    if not request.report_path and not request.report_url:
        raise HTTPException(
            status_code=400,
            detail="Either report_path or report_url must be provided"
        )
    
    # Determine PDF path
    if request.report_path:
        pdf_path = Path(request.report_path)
        if not pdf_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Report file not found: {request.report_path}"
            )
    else:
        # TODO: Implement URL download
        raise HTTPException(
            status_code=501,
            detail="URL download not yet implemented. Please provide report_path."
        )
    
    # Filter indicators if specified
    indicators_to_extract = None
    if request.indicators:
        indicators_to_extract = []
        for code in request.indicators:
            indicator = get_indicator_by_code(code)
            if not indicator:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid indicator code: {code}"
                )
            indicators_to_extract.append(indicator)
    
    # Run extraction - agent mode by default
    start_time = time.time()
    
    try:
        if request.mode == "simple":
            logger.info(f"📋 Using SIMPLE mode - basic extraction workflow")
            result = run_extraction(
                pdf_path=str(pdf_path),
                company_name=request.company_name,
                report_year=request.report_year,
                indicators=indicators_to_extract
            )
        else:
            logger.info(f"🤖 Using AGENT mode - AI will autonomously decide tools to use")
            result = run_agent_extraction(
                pdf_path=str(pdf_path),
                company_name=request.company_name,
                report_year=request.report_year,
                indicators=indicators_to_extract
            )
        
        processing_time = time.time() - start_time
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Extraction failed: {result.get('errors', [])}"
            )
        
        # Save to database
        extracted_values = result["extracted_values"]
        save_results(request.company_name, request.report_year, extracted_values)
        
        # Export to CSV
        csv_filename = f"{request.company_name.replace(' ', '_')}_{request.report_year}_esg_data.csv"
        csv_path = settings.outputs_dir / csv_filename
        export_to_csv(str(csv_path), request.company_name, request.report_year)
        
        # Prepare response
        response = ExtractionResponse(
            company_name=request.company_name,
            report_year=request.report_year,
            total_indicators=len(extracted_values),
            extracted_values=extracted_values,
            processing_time=round(processing_time, 2),
            csv_path=str(csv_path),
            status="success",
            errors=result.get("errors", [])
        )
        
        logger.info(f"Extraction completed in {processing_time:.2f}s")
        
        return response
    
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@app.get("/results/{company_name}/{year}")
async def get_results(
    company_name: str,
    year: int,
    min_confidence: Optional[float] = None
):
    """Get extraction results for a specific company and year.
    
    Args:
        company_name: Company name
        year: Report year
        min_confidence: Minimum confidence threshold (optional)
    
    Returns:
        List of extracted values
    """
    records = db.get_records(
        company=company_name,
        year=year,
        min_confidence=min_confidence
    )
    
    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No results found for {company_name} - {year}"
        )
    
    results = []
    for record in records:
        results.append({
            "indicator": record.indicator,
            "value": record.value,
            "numeric_value": record.numeric_value,
            "unit": record.unit,
            "source_page": record.source_page,
            "confidence": record.confidence,
            "notes": record.notes
        })
    
    return {
        "company": company_name,
        "year": year,
        "total_indicators": len(results),
        "results": results
    }


@app.get("/export/csv")
async def export_csv(
    company: Optional[str] = None,
    year: Optional[int] = None
):
    """Export results to CSV file.
    
    Args:
        company: Filter by company (optional)
        year: Filter by year (optional)
    
    Returns:
        CSV file download
    """
    filename = f"esg_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_path = settings.outputs_dir / filename
    
    try:
        export_to_csv(str(csv_path), company, year)
        
        return FileResponse(
            path=csv_path,
            filename=filename,
            media_type="text/csv"
        )
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@app.get("/stats")
async def get_statistics():
    """Get database statistics.
    
    Returns:
        Summary statistics
    """
    stats = db.get_summary_stats()
    return stats


@app.delete("/results/{company_name}/{year}")
async def delete_results(company_name: str, year: int):
    """Delete results for a specific company and year.
    
    Args:
        company_name: Company name
        year: Report year
    
    Returns:
        Deletion confirmation
    """
    try:
        count = db.delete_records(company=company_name, year=year)
        
        return {
            "status": "success",
            "message": f"Deleted {count} records for {company_name} - {year}"
        }
    
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Delete failed: {str(e)}"
        )


@app.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    company_name: Optional[str] = None
):
    """Upload a PDF report for processing.
    
    Args:
        file: PDF file upload
        company_name: Company name (optional)
    
    Returns:
        Upload confirmation with file path
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )
    
    # Save uploaded file
    if company_name:
        filename = f"{company_name.replace(' ', '_')}_{file.filename}"
    else:
        filename = file.filename
    
    file_path = settings.reports_dir / filename
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Uploaded file saved to {file_path}")
        
        return {
            "status": "success",
            "filename": filename,
            "file_path": str(file_path),
            "message": "File uploaded successfully. Use this path in the /extract endpoint."
        }
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )

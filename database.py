"""Database layer for storing ESG extraction results."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
from pathlib import Path
import logging

from config import settings
from models import ExtractedValue, DatabaseRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()


class ESGRecord(Base):
    """SQLAlchemy model for ESG indicator records."""
    __tablename__ = "esg_indicators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(200), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    indicator = Column(String(50), nullable=False, index=True)
    value = Column(String(100), nullable=True)
    numeric_value = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    source_page = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    source_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ESGRecord(company='{self.company}', year={self.year}, indicator='{self.indicator}', value='{self.value}')>"


class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager.
        
        Args:
            database_url: Database URL (defaults to settings)
        """
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified")
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def save_extraction_results(
        self,
        company_name: str,
        report_year: int,
        extracted_values: List[ExtractedValue]
    ) -> int:
        """Save extraction results to database.
        
        Args:
            company_name: Company name
            report_year: Report year
            extracted_values: List of extracted values
        
        Returns:
            Number of records saved
        """
        session = self.get_session()
        try:
            saved_count = 0
            
            for value in extracted_values:
                record = ESGRecord(
                    company=company_name,
                    year=report_year,
                    indicator=value.indicator_code,
                    value=value.value,
                    numeric_value=value.numeric_value,
                    unit=value.unit,
                    source_page=value.source_page,
                    confidence=value.confidence,
                    notes=value.explanation,
                    source_text=value.source_text
                )
                
                session.add(record)
                saved_count += 1
            
            session.commit()
            logger.info(f"Saved {saved_count} records to database")
            
            return saved_count
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving to database: {e}")
            raise
        finally:
            session.close()
    
    def get_records(
        self,
        company: Optional[str] = None,
        year: Optional[int] = None,
        indicator: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[ESGRecord]:
        """Query ESG records with filters.
        
        Args:
            company: Filter by company name
            year: Filter by year
            indicator: Filter by indicator code
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of matching records
        """
        session = self.get_session()
        try:
            query = session.query(ESGRecord)
            
            if company:
                query = query.filter(ESGRecord.company == company)
            if year:
                query = query.filter(ESGRecord.year == year)
            if indicator:
                query = query.filter(ESGRecord.indicator == indicator)
            if min_confidence is not None:
                query = query.filter(ESGRecord.confidence >= min_confidence)
            
            return query.all()
        
        finally:
            session.close()
    
    def delete_records(
        self,
        company: Optional[str] = None,
        year: Optional[int] = None
    ) -> int:
        """Delete records matching criteria.
        
        Args:
            company: Company name to delete
            year: Year to delete
        
        Returns:
            Number of records deleted
        """
        session = self.get_session()
        try:
            query = session.query(ESGRecord)
            
            if company:
                query = query.filter(ESGRecord.company == company)
            if year:
                query = query.filter(ESGRecord.year == year)
            
            count = query.delete()
            session.commit()
            
            logger.info(f"Deleted {count} records from database")
            return count
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting records: {e}")
            raise
        finally:
            session.close()
    
    def export_to_dataframe(
        self,
        company: Optional[str] = None,
        year: Optional[int] = None
    ) -> pd.DataFrame:
        """Export records to pandas DataFrame.
        
        Args:
            company: Filter by company
            year: Filter by year
        
        Returns:
            DataFrame with records
        """
        records = self.get_records(company=company, year=year)
        
        data = []
        for record in records:
            data.append({
                "company": record.company,
                "year": record.year,
                "indicator": record.indicator,
                "value": record.value,
                "numeric_value": record.numeric_value,
                "unit": record.unit,
                "source_page": record.source_page,
                "confidence": record.confidence,
                "notes": record.notes
            })
        
        return pd.DataFrame(data)
    
    def export_to_csv(
        self,
        output_path: str,
        company: Optional[str] = None,
        year: Optional[int] = None
    ) -> str:
        """Export records to CSV file.
        
        Args:
            output_path: Path to output CSV file
            company: Filter by company
            year: Filter by year
        
        Returns:
            Path to created CSV file
        """
        df = self.export_to_dataframe(company=company, year=year)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} records to {output_path}")
        
        return str(output_path)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from database.
        
        Returns:
            Dictionary with summary statistics
        """
        session = self.get_session()
        try:
            total_records = session.query(ESGRecord).count()
            unique_companies = session.query(ESGRecord.company).distinct().count()
            unique_years = session.query(ESGRecord.year).distinct().count()
            unique_indicators = session.query(ESGRecord.indicator).distinct().count()
            
            avg_confidence = session.query(ESGRecord.confidence).filter(
                ESGRecord.confidence > 0
            ).all()
            avg_conf = sum(c[0] for c in avg_confidence) / len(avg_confidence) if avg_confidence else 0
            
            return {
                "total_records": total_records,
                "unique_companies": unique_companies,
                "unique_years": unique_years,
                "unique_indicators": unique_indicators,
                "average_confidence": round(avg_conf, 2)
            }
        
        finally:
            session.close()


# Convenience functions
def save_results(company: str, year: int, values: List[ExtractedValue]) -> int:
    """Convenience function to save extraction results."""
    db = DatabaseManager()
    return db.save_extraction_results(company, year, values)


def export_to_csv(output_path: str, company: Optional[str] = None, year: Optional[int] = None) -> str:
    """Convenience function to export to CSV."""
    db = DatabaseManager()
    return db.export_to_csv(output_path, company, year)


def get_all_records() -> pd.DataFrame:
    """Convenience function to get all records as DataFrame."""
    db = DatabaseManager()
    return db.export_to_dataframe()

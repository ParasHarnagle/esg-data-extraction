"""Data models and schemas for ESG indicator extraction."""
from datetime import datetime
from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ESGCategory(str, Enum):
    """ESG category classification."""
    ENVIRONMENTAL = "E"
    SOCIAL = "S"
    GOVERNANCE = "G"
    ESRS2 = "ESRS2"


class IndicatorCode(str, Enum):
    """Standard ESG indicator codes."""
    # Environmental (E1) - Climate Change
    E1_1 = "E1-1"  # Total Scope 1 GHG Emissions
    E1_2 = "E1-2"  # Total Scope 2 GHG Emissions
    E1_3 = "E1-3"  # Total Scope 3 GHG Emissions
    E1_4 = "E1-4"  # GHG Emissions Intensity
    E1_5 = "E1-5"  # Total Energy Consumption
    E1_6 = "E1-6"  # Renewable Energy Percentage
    E1_7 = "E1-7"  # Net Zero Target Year
    E1_8 = "E1-8"  # Green Financing Volume
    
    # Social (S1) - Own Workforce
    S1_1 = "S1-1"  # Total Employees
    S1_2 = "S1-2"  # Female Employees
    S1_3 = "S1-3"  # Gender Pay Gap
    S1_4 = "S1-4"  # Training Hours per Employee
    S1_5 = "S1-5"  # Employee Turnover Rate
    S1_6 = "S1-6"  # Work-Related Accidents
    S1_7 = "S1-7"  # Collective Bargaining Coverage
    
    # Governance (G1) & ESRS 2
    G1_1 = "G1-1"  # Board Female Representation
    G1_2 = "G1-2"  # Board Meetings
    G1_3 = "G1-3"  # Corruption Incidents
    G1_4 = "G1-4"  # Avg Payment Period to Suppliers
    ESRS2_1 = "ESRS2-1"  # Suppliers Screened for ESG


class ESGIndicator(BaseModel):
    """Definition of an ESG indicator to extract."""
    code: IndicatorCode
    name: str
    category: ESGCategory
    description: str
    expected_unit: str
    keywords: list[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class ExtractedValue(BaseModel):
    """Extracted value from a report."""
    indicator_code: str
    value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    source_page: Optional[int] = None
    source_text: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    explanation: Optional[str] = None
    extraction_method: Optional[str] = None  # NEW: agent, simple, or vector_search
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "indicator_code": "E1-1",
                "value": "1,234,567",
                "numeric_value": 1234567.0,
                "unit": "tCO2e",
                "source_page": 45,
                "confidence": 0.95,
                "explanation": "Found in emissions table on page 45"
            }
        }


class CompanyReport(BaseModel):
    """Company report metadata."""
    company_name: str
    report_year: int
    report_type: str = "CSRD Annual Report"
    file_path: Optional[str] = None
    url: Optional[str] = None
    total_pages: Optional[int] = None
    processed_date: Optional[datetime] = None


class ExtractionRequest(BaseModel):
    """API request for extraction (agent mode by default)."""
    company_name: str
    report_year: int
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    indicators: Optional[list[str]] = None  # If None, extract all
    mode: Literal["agent", "simple"] = "agent"  # agent=autonomous AI with tools, simple=basic extraction


class ExtractionResponse(BaseModel):
    """API response for extraction."""
    company_name: str
    report_year: int
    total_indicators: int
    extracted_values: list[ExtractedValue]
    processing_time: float
    csv_path: Optional[str] = None
    status: str = "success"
    errors: list[str] = Field(default_factory=list)


class DatabaseRecord(BaseModel):
    """Database record structure."""
    id: Optional[int] = None
    company: str
    year: int
    indicator: str
    value: Optional[str] = None
    unit: Optional[str] = None
    source_page: Optional[int] = None
    confidence: float
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Define the 20 ESG indicators to extract (matching target specification)
ESG_INDICATORS = [
    # Environmental Indicators (ESRS E1 - Climate Change) - 8 indicators
    ESGIndicator(
        code=IndicatorCode.E1_1,
        name="Total Scope 1 GHG Emissions",
        category=ESGCategory.ENVIRONMENTAL,
        description="Direct greenhouse gas emissions from owned or controlled sources",
        expected_unit="tCO2e",
        keywords=["scope 1", "direct emissions", "GHG", "greenhouse gas", "tCO2e"]
    ),
    ESGIndicator(
        code=IndicatorCode.E1_2,
        name="Total Scope 2 GHG Emissions",
        category=ESGCategory.ENVIRONMENTAL,
        description="Indirect GHG emissions from purchased electricity, heat, or steam",
        expected_unit="tCO2e",
        keywords=["scope 2", "indirect emissions", "electricity", "purchased energy", "tCO2e"]
    ),
    ESGIndicator(
        code=IndicatorCode.E1_3,
        name="Total Scope 3 GHG Emissions",
        category=ESGCategory.ENVIRONMENTAL,
        description="All other indirect emissions in the value chain",
        expected_unit="tCO2e",
        keywords=["scope 3", "value chain", "indirect emissions", "financed emissions", "tCO2e"]
    ),
    ESGIndicator(
        code=IndicatorCode.E1_4,
        name="GHG Emissions Intensity",
        category=ESGCategory.ENVIRONMENTAL,
        description="GHG emissions per million euros of revenue",
        expected_unit="tCO2e per €M revenue",
        keywords=["emissions intensity", "carbon intensity", "tCO2e per", "emissions per revenue"]
    ),
    ESGIndicator(
        code=IndicatorCode.E1_5,
        name="Total Energy Consumption",
        category=ESGCategory.ENVIRONMENTAL,
        description="Total energy consumption from all sources",
        expected_unit="MWh or GJ",
        keywords=["energy consumption", "total energy", "energy use", "MWh", "GJ"]
    ),
    ESGIndicator(
        code=IndicatorCode.E1_6,
        name="Renewable Energy Percentage",
        category=ESGCategory.ENVIRONMENTAL,
        description="Percentage of energy from renewable sources",
        expected_unit="%",
        keywords=["renewable energy", "green energy", "renewable percentage", "renewable sources"]
    ),
    ESGIndicator(
        code=IndicatorCode.E1_7,
        name="Net Zero Target Year",
        category=ESGCategory.ENVIRONMENTAL,
        description="Target year for achieving net zero emissions",
        expected_unit="year",
        keywords=["net zero", "carbon neutral", "target year", "2030", "2040", "2050"]
    ),
    ESGIndicator(
        code=IndicatorCode.E1_8,
        name="Green Financing Volume",
        category=ESGCategory.ENVIRONMENTAL,
        description="Volume of green financing provided",
        expected_unit="€ millions",
        keywords=["green financing", "sustainable finance", "green bonds", "climate finance", "€M", "million"]
    ),
    
    # Social Indicators (ESRS S1 - Own Workforce) - 7 indicators
    ESGIndicator(
        code=IndicatorCode.S1_1,
        name="Total Employees",
        category=ESGCategory.SOCIAL,
        description="Total number of employees (full-time equivalent)",
        expected_unit="FTE",
        keywords=["workforce", "employees", "headcount", "staff", "FTE", "full-time equivalent"]
    ),
    ESGIndicator(
        code=IndicatorCode.S1_2,
        name="Female Employees",
        category=ESGCategory.SOCIAL,
        description="Percentage of female employees",
        expected_unit="%",
        keywords=["female employees", "women", "gender diversity", "female representation"]
    ),
    ESGIndicator(
        code=IndicatorCode.S1_3,
        name="Gender Pay Gap",
        category=ESGCategory.SOCIAL,
        description="Gender pay gap percentage",
        expected_unit="%",
        keywords=["gender pay gap", "pay gap", "wage gap", "equal pay"]
    ),
    ESGIndicator(
        code=IndicatorCode.S1_4,
        name="Training Hours per Employee",
        category=ESGCategory.SOCIAL,
        description="Average training hours per employee per year",
        expected_unit="hours",
        keywords=["training hours", "development", "learning", "training per employee"]
    ),
    ESGIndicator(
        code=IndicatorCode.S1_5,
        name="Employee Turnover Rate",
        category=ESGCategory.SOCIAL,
        description="Annual employee turnover rate",
        expected_unit="%",
        keywords=["turnover rate", "attrition", "employee retention", "turnover"]
    ),
    ESGIndicator(
        code=IndicatorCode.S1_6,
        name="Work-Related Accidents",
        category=ESGCategory.SOCIAL,
        description="Number of work-related accidents",
        expected_unit="count",
        keywords=["work-related accidents", "workplace accidents", "injuries", "incidents", "safety"]
    ),
    ESGIndicator(
        code=IndicatorCode.S1_7,
        name="Collective Bargaining Coverage",
        category=ESGCategory.SOCIAL,
        description="Percentage of employees covered by collective bargaining agreements",
        expected_unit="%",
        keywords=["collective bargaining", "union coverage", "collective agreements", "trade union"]
    ),
    
    # Governance Indicators (ESRS G1 & ESRS 2) - 5 indicators
    ESGIndicator(
        code=IndicatorCode.G1_1,
        name="Board Female Representation",
        category=ESGCategory.GOVERNANCE,
        description="Percentage of women on the board",
        expected_unit="%",
        keywords=["women directors", "board diversity", "female board members", "women on board"]
    ),
    ESGIndicator(
        code=IndicatorCode.G1_2,
        name="Board Meetings",
        category=ESGCategory.GOVERNANCE,
        description="Number of board meetings held annually",
        expected_unit="count/year",
        keywords=["board meetings", "governance meetings", "meetings per year"]
    ),
    ESGIndicator(
        code=IndicatorCode.G1_3,
        name="Corruption Incidents",
        category=ESGCategory.GOVERNANCE,
        description="Number of corruption incidents reported",
        expected_unit="count",
        keywords=["corruption", "bribery", "anti-corruption", "corruption incidents", "fraud"]
    ),
    ESGIndicator(
        code=IndicatorCode.G1_4,
        name="Avg Payment Period to Suppliers",
        category=ESGCategory.GOVERNANCE,
        description="Average payment period to suppliers in days",
        expected_unit="days",
        keywords=["payment period", "supplier payment", "payment terms", "days payable"]
    ),
    ESGIndicator(
        code=IndicatorCode.ESRS2_1,
        name="Suppliers Screened for ESG",
        category=ESGCategory.ESRS2,
        description="Percentage of suppliers screened for ESG criteria",
        expected_unit="%",
        keywords=["supplier screening", "ESG screening", "supplier assessment", "supply chain ESG"]
    ),
]


def get_indicators_by_category(category: ESGCategory) -> list[ESGIndicator]:
    """Get all indicators for a specific category."""
    return [ind for ind in ESG_INDICATORS if ind.category == category]


def get_indicator_by_code(code: str) -> Optional[ESGIndicator]:
    """Get a specific indicator by its code."""
    for indicator in ESG_INDICATORS:
        # Handle both string and IndicatorCode enum
        indicator_code = indicator.code.value if hasattr(indicator.code, 'value') else indicator.code
        if indicator_code == code:
            return indicator
    return None

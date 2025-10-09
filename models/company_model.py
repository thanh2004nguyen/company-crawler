from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CompanyData(BaseModel):
    """Model cho dữ liệu công ty Đức từ nhiều nguồn"""
    
    # Thông tin cơ bản
    registernummer: str = Field(..., description="Số đăng ký HRB từ sổ thương mại")
    handelsregister: str = Field(..., description="Tên tòa án đăng ký thương mại")
    mitarbeiter: Optional[int] = Field(None, description="Số lượng nhân viên hiện tại")
    ust_idnr: str = Field(..., description="Mã số thuế VAT")
    insolvenz: bool = Field(False, description="Tình trạng phá sản (Có/Không)")
    
    # Thông tin kinh doanh
    unternehmenszweck: Optional[str] = Field(None, description="Mục đích và hoạt động kinh doanh")
    umsatz: Optional[float] = Field(None, description="Doanh thu tính bằng EUR")
    gewinn: Optional[float] = Field(None, description="Lợi nhuận/Lỗ tính bằng EUR")
    
    # Thông tin bất động sản
    anzahl_immobilien: Optional[int] = Field(None, description="Số lượng bất động sản sở hữu")
    gesamtwert_immobilien: Optional[float] = Field(None, description="Tổng giá trị bất động sản")
    
    # Sở hữu trí tuệ
    sonstige_rechte: Optional[list[str]] = Field(default_factory=list, description="Bằng sáng chế, thương hiệu, v.v.")
    
    # Thông tin thời gian
    gruendungsdatum: Optional[str] = Field(None, description="Ngày thành lập công ty")
    aktiv_seit: Optional[str] = Field(None, description="Hoạt động từ (năm/tháng)")
    bankverbindung_seit: Optional[str] = Field(None, description="Kết nối ngân hàng từ")
    geschaeftsadresse_seit: Optional[str] = Field(None, description="Địa chỉ kinh doanh từ")
    telefonnummer_seit: Optional[str] = Field(None, description="Số điện thoại từ")
    mobilfunknummer_seit: Optional[str] = Field(None, description="Số di động từ")
    
    # Đánh giá rủi ro
    negativmerkmale_unternehmen: Optional[str] = Field(None, description="Dấu hiệu tiêu cực công ty")
    negativmerkmale_unternehmer: Optional[str] = Field(None, description="Dấu hiệu tiêu cực chủ sở hữu")
    
    # Thông tin địa điểm
    land_des_hauptsitzes: str = Field(default="Deutschland", description="Quốc gia trụ sở chính")
    gerichtsstand: str = Field(..., description="Vị trí tòa án có thẩm quyền")
    
    # Thông tin pháp lý
    paragraph_34_gewo: bool = Field(False, description="Trạng thái giấy phép §34 GewO")
    
    # Thông tin bổ sung
    geschaeftsfuehrer: Optional[list[str]] = Field(default_factory=list, description="Tên giám đốc điều hành")
    geschaeftsadresse: Optional[str] = Field(None, description="Địa chỉ kinh doanh đầy đủ")
    telefonnummer: Optional[str] = Field(None, description="Số điện thoại liên hệ")
    email: Optional[str] = Field(None, description="Địa chỉ email liên hệ")
    website: Optional[str] = Field(None, description="URL website công ty")
    
    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.now, description="Thời gian trích xuất dữ liệu")
    data_sources: list[str] = Field(default_factory=list, description="Danh sách nguồn dữ liệu")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True


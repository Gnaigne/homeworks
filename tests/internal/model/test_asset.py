import pytest
from pydantic import ValidationError

from internal.model.asset import AssetType, AssetStatus, CreateAssetRequest

# =============================================================================
# BÀI TẬP SESSION 6: TESTING & QUALITY ASSURANCE
# Tầng Model: Kiểm tra các Enums và Data Transfer Objects của Asset
# =============================================================================

# 🎓 TEACHING NOTES: Table-Driven Tests bằng pytest.mark.parametrize
# Thay vì viết 5 hàm test riêng biệt (test_domain, test_ip, test_service...), 
# ta chỉ cần viết 1 hàm duy nhất, cung cấp một "Bảng Dữ Liệu" (Table) 
# chứa các trường hợp đầu vào mong muốn. Pytest sẽ tự động chạy lặp qua từng dòng!

@pytest.mark.parametrize("valid_type", [
    "domain",
    "ip",
    "service"
])
def test_valid_asset_type_enum(valid_type):
    """Kiểm tra Enum AssetType chấp nhận các giá trị chuẩn."""
    # Khi khai báo CreateAssetRequest, Pydantic sẽ tự động ép kiểu string 
    # về Enum AssetType tương ứng.
    request = CreateAssetRequest(name="example.com", type=valid_type)
    assert request.type == AssetType(valid_type)

@pytest.mark.parametrize("invalid_type", [
    "website",
    "server",
    "",
    "DOMAIN",  # Phân biệt hoa thường
    " ip ",    # Có dấu cách
])
def test_invalid_asset_type_enum(invalid_type):
    """Đảm bảo Pydantic quăng lỗi ValidationError nếu nhập sai loại AssetType."""
    with pytest.raises(ValidationError) as exc_info:
        CreateAssetRequest(name="example.com", type=invalid_type)
    
    # Kiểm tra xem lỗi có đúng là lỗi thuộc tính 'type' không
    assert "type" in str(exc_info.value)

@pytest.mark.parametrize("valid_status", [
    "active",
    "inactive"
])
def test_valid_asset_status_enum(valid_status):
    """Kiểm tra Enum AssetStatus."""
    assert AssetStatus(valid_status).value == valid_status

def test_invalid_asset_status_enum():
    """Kiểm tra giá trị lỗi cho AssetStatus."""
    with pytest.raises(ValueError):
        AssetStatus("pending")
    with pytest.raises(ValueError):
        AssetStatus("")

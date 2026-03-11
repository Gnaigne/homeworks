"""
=============================================================================
File: internal/model/asset.py
Layer: Entity Layer (Clean Architecture)
Tác dụng: Định nghĩa cấu trúc dữ liệu Asset — thực thể cốt lõi của hệ thống.
=============================================================================

ĐỌC FILE NÀY ĐẦU TIÊN — đây là trung tâm của toàn bộ ứng dụng.

Asset đại diện cho một tài nguyên (domain, IP, service) mà hệ thống
Attack Surface Management (ASM) theo dõi và quản lý.

File này chứa:
    1. Enum cho asset type và status — đảm bảo type safety
    2. Asset model (Pydantic) — entity chính với validation tự động
    3. Request models — cấu trúc dữ liệu cho API request body

🏗️ CLEAN ARCHITECTURE:
    Entity Layer là lớp trong cùng, KHÔNG phụ thuộc vào layer nào khác.
    Các layer khác (service, handler, storage) đều phụ thuộc vào model,
    nhưng model KHÔNG import gì từ chúng.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS - Kiểu dữ liệu liệt kê (thay thế constants trong Go)
# =============================================================================
# Trong Go dùng string constants:
#   const TypeDomain = "domain"
#
# Python dùng Enum — an toàn hơn vì compiler/IDE kiểm tra được,
# và tự động validate giá trị hợp lệ.


class AssetType(str, Enum):
    """
    Loại asset có thể quản lý trong hệ thống.

    Kế thừa cả `str` và `Enum` để giá trị enum là string,
    giúp serialize/deserialize JSON tự nhiên (không cần custom encoder).

    Attributes:
        DOMAIN: Tên miền (ví dụ: example.com)
        IP: Địa chỉ IP (ví dụ: 192.168.1.1)
        SERVICE: Dịch vụ mạng (ví dụ: HTTPS trên cổng 443)
    """
    DOMAIN = "domain"
    IP = "ip"
    SERVICE = "service"


class AssetStatus(str, Enum):
    """
    Trạng thái hoạt động của asset.

    Attributes:
        ACTIVE: Asset đang hoạt động, cần theo dõi
        INACTIVE: Asset không hoạt động hoặc đã ngừng theo dõi
    """
    ACTIVE = "active"
    INACTIVE = "inactive"


# =============================================================================
# ASSET MODEL - Entity chính của hệ thống
# =============================================================================
# Tương đương Go struct:
#   type Asset struct {
#       ID        string    `json:"id"`
#       Name      string    `json:"name"`
#       Type      string    `json:"type"`
#       Status    string    `json:"status"`
#       CreatedAt time.Time `json:"created_at"`
#       UpdatedAt time.Time `json:"updated_at"`
#   }
#
# Pydantic BaseModel cung cấp:
#   ✅ Tự động validate kiểu dữ liệu khi tạo instance
#   ✅ Serialize sang JSON (model.model_dump())
#   ✅ Tạo JSON Schema cho API documentation


class Asset(BaseModel):
    """
    Model chính đại diện cho một tài nguyên mạng (domain, IP, hoặc service).

    Đây là domain entity — chỉ chứa dữ liệu và validation cơ bản,
    không chứa business logic hay HTTP concerns.

    Attributes:
        id: UUID duy nhất, tự động tạo bởi service layer
        name: Tên tài nguyên (ví dụ: "example.com", "192.168.1.1")
        type: Loại asset (domain / ip / service)
        status: Trạng thái hoạt động (active / inactive)
        created_at: Thời điểm tạo (UTC), tự động gán bởi service
        updated_at: Thời điểm cập nhật cuối (UTC), tự động cập nhật
    """

    id: str
    name: str
    type: AssetType
    status: AssetStatus
    created_at: datetime
    updated_at: datetime

    # Cấu hình cho Pydantic V2 — tương đương json tags trong Go
    model_config = {
        # Cho phép tạo model từ ORM object (chuẩn bị cho session 3 - database)
        "from_attributes": True,
        # Ví dụ JSON output cho API documentation
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "example.com",
                "type": "domain",
                "status": "active",
                "created_at": "2026-03-06T10:00:00Z",
                "updated_at": "2026-03-06T10:00:00Z",
            }
        },
    }


# =============================================================================
# REQUEST MODELS - Cấu trúc dữ liệu cho HTTP request body
# =============================================================================
# Tách riêng request model khỏi domain model (Asset) vì:
#   - API request ≠ domain entity (request có thể thiếu field như id, timestamps)
#   - Dễ kiểm soát field nào client được gửi
#   - Rõ ràng hơn cho API documentation


class CreateAssetRequest(BaseModel):
    """
    Request body cho POST /assets — tạo asset mới.

    Client chỉ cần gửi name và type. Các field khác (id, status, timestamps)
    sẽ được service layer tự động tạo.

    Attributes:
        name: Tên tài nguyên (bắt buộc)
        type: Loại asset — domain, ip, hoặc service (bắt buộc)
    """
    name: str
    type: AssetType

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "example.com",
                "type": "domain",
            }
        },
    }


class UpdateAssetRequest(BaseModel):
    """
    Request body cho PUT /assets/{id} — cập nhật asset.

    Hỗ trợ partial update — chỉ cập nhật field được gửi.
    Field không gửi (None) sẽ giữ nguyên giá trị cũ.

    Attributes:
        name: Tên mới (tùy chọn)
        type: Loại mới (tùy chọn)
        status: Trạng thái mới (tùy chọn)
    """
    name: Optional[str] = None
    type: Optional[AssetType] = None
    status: Optional[AssetStatus] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "new-name.com",
                "type": "domain",
                "status": "inactive",
            }
        },
    }

class BatchCreateAssetRequest(BaseModel):
    """
    [BÀI 2] Request body cho POST /assets/batch — tạo nhiều asset cùng lúc.

    Client gửi 1 list các asset cần tạo. Server sẽ:
        1. Validate từng asset (name không trống, type hợp lệ)
        2. Nếu TẤT CẢ hợp lệ → tạo trong 1 transaction (all or nothing)
        3. Nếu 1 cái fail → rollback tất cả, không tạo asset nào

    Cú pháp:  assets: List[CreateAssetRequest]
              │       │
              │       └─ List chứa các CreateAssetRequest (đã định nghĩa ở trên)
              │          Pydantic tự validate từng phần tử trong list
              └─ Tên field — client gửi JSON key "assets"

    Attributes:
        assets: Danh sách asset cần tạo (mỗi phần tử có name + type)
    """
    assets: List[CreateAssetRequest]

    model_config = {
        "json_schema_extra": {
            "example": {
                "assets": [
                    {"name": "example.com", "type": "domain"},
                    {"name": "new-example.com", "type": "domain"}
                ]
            }
        },
    }
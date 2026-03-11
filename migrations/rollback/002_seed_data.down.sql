-- =============================================================================
-- Rollback Migration 002: Xóa seed data
-- =============================================================================
-- Chỉ xóa các dòng được tạo bởi 002_seed_data.up.sql (theo ID cụ thể)
-- Không ảnh hưởng data do user tạo sau này

DELETE FROM assets WHERE id IN (
    '576682d6-7922-49d5-8fdc-4dcacd15616a',
    '1466bba2-3c45-4dda-8c23-97b726dd5e67',
    '31f71c3c-425b-4bbb-9ec2-b8d37e168f14',
    'a3462d65-ab1d-418b-905a-f02b20f0c81d',
    '9bcd34c9-c4e1-460a-8105-cdae4c63aca7',
    'f3af9849-eac3-4a2c-97f0-9f8f7f99ba54',
    'e40c1e49-253e-4f2a-84b3-6745ccdd12d8',
    'c4e515ce-2053-4be7-be9c-c018f3139034',
    '18d37480-c97b-4ab2-bbca-3d650265cc2f',
    '81c92790-3f8a-4c7d-95c4-396cb2861afb',
    '57891de3-62b4-4ef3-b172-115091f90eae',
    'c21ae43f-06dd-45c2-be0c-0088b5df4d53',
    '8e2cc6b9-48a7-4da0-91ca-fa028d7d34fb',
    '7e8e24ce-68e1-47ff-b81b-181fc4009a9c',
    'b7155d04-a277-44a7-805f-ee94bb22c1d9',
    '37a202b0-53b8-4187-b9fc-1c740ae22666',
    'bc62455e-bbfb-44d2-8ebd-c9b9c59222cc'
);

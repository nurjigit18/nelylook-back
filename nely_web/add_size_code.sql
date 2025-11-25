-- Migration: Add size_code field to sizes table
-- Run this SQL in your database

-- Add the size_code column
ALTER TABLE sizes ADD COLUMN size_code VARCHAR(5) NULL;

-- Update existing sizes with appropriate size codes
-- These are common mappings, adjust based on your actual data

-- European shoe sizes (typically 36-46)
UPDATE sizes SET size_code = 'XS' WHERE size_name IN ('36', '37');
UPDATE sizes SET size_code = 'S' WHERE size_name IN ('38', '39');
UPDATE sizes SET size_code = 'M' WHERE size_name IN ('40', '41', '42');
UPDATE sizes SET size_code = 'L' WHERE size_name IN ('43', '44');
UPDATE sizes SET size_code = 'XL' WHERE size_name IN ('45', '46');

-- Clothing sizes (if you have numeric sizes like 42, 44, 46)
UPDATE sizes SET size_code = 'XS' WHERE size_name IN ('38', '40') AND size_code IS NULL;
UPDATE sizes SET size_code = 'S' WHERE size_name IN ('42', '44') AND size_code IS NULL;
UPDATE sizes SET size_code = 'M' WHERE size_name IN ('46', '48') AND size_code IS NULL;
UPDATE sizes SET size_code = 'L' WHERE size_name IN ('50', '52') AND size_code IS NULL;
UPDATE sizes SET size_code = 'XL' WHERE size_name IN ('54', '56') AND size_code IS NULL;
UPDATE sizes SET size_code = 'XXL' WHERE size_name IN ('58', '60') AND size_code IS NULL;

-- If you already have letter sizes, keep them as-is
UPDATE sizes SET size_code = size_name WHERE size_name IN ('XS', 'S', 'M', 'L', 'XL', 'XXL');

-- Check results
SELECT size_id, size_name, size_code, sort_order FROM sizes ORDER BY sort_order, size_name;

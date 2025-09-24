@echo off
REM complete_reset.bat - Complete database reset for Windows

echo 🚨 COMPLETE DATABASE RESET - This will delete ALL data!
echo Press Ctrl+C to cancel, or press any key to continue...
pause

echo 🧹 Step 1: Clearing database...
python manage.py flush --noinput

echo 🗑️  Step 2: Removing all migrations...
for /r . %%i in (migrations\*.py) do (
    if not "%%~ni"=="__init__" del "%%i"
)
for /r . %%i in (migrations\*.pyc) do del "%%i"

echo 📋 Step 3: Creating fresh migrations...
python manage.py makemigrations authentication
python manage.py makemigrations core  
python manage.py makemigrations catalog
python manage.py makemigrations cart
python manage.py makemigrations orders
python manage.py makemigrations payments
python manage.py makemigrations wishlist

echo 📤 Step 4: Applying migrations...
python manage.py migrate

echo 🎭 Step 5: Populating with fake data...
python manage.py populate_db --users 50 --products 100

echo ✅ DATABASE RESET COMPLETE!
echo.
echo 🔑 Admin Access:
echo    Email: admin@nelylook.com
echo    Password: admin123
echo.
echo 📊 Data Created:
echo    - 50 users with addresses
echo    - 100 products with variants
echo    - Categories, colors, sizes
echo    - Shopping carts and orders
echo    - Wishlists and collections

pause
import os
import uuid
import re
from urllib.parse import quote
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.text import slugify
from unidecode import unidecode


class SupabaseStorage(Storage):
    """
    Custom storage backend for Supabase with support for Cyrillic filenames
    """
    def __init__(self, bucket_name=None):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.bucket_name = bucket_name or settings.SUPABASE_BUCKET_NAME
        
        # Lazy import to avoid issues if supabase isn't installed
        try:
            from supabase import create_client, Client
            self.client = create_client(self.supabase_url, self.supabase_key)
        except ImportError:
            raise ImportError("supabase package is required. Install it with: pip install supabase")
    
    def _sanitize_filename(self, filename):
        """
        Sanitize filename to remove special characters and transliterate Cyrillic.
        Converts: 'products/грин.png' -> 'grin.png'
        """
        import re
        import unicodedata
        
        # Transliteration map for Cyrillic to Latin
        cyrillic_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        }
        
        # Split filename and extension
        import os
        name, ext = os.path.splitext(filename)
        
        # Transliterate Cyrillic characters
        transliterated = ''
        for char in name:
            transliterated += cyrillic_to_latin.get(char, char)
        
        # Remove any remaining non-ASCII characters
        transliterated = unicodedata.normalize('NFKD', transliterated)
        transliterated = transliterated.encode('ascii', 'ignore').decode('ascii')
        
        # Replace spaces and special characters with hyphens
        transliterated = re.sub(r'[^\w\s-]', '', transliterated)
        transliterated = re.sub(r'[-\s]+', '-', transliterated)
        
        # Remove leading/trailing hyphens
        transliterated = transliterated.strip('-')
        
        # Convert to lowercase
        transliterated = transliterated.lower()
        
        # Reconstruct filename with extension
        sanitized = f"{transliterated}{ext.lower()}"
        
        return sanitized
            
    def _save(self, name, content):
        """
        Save file to Supabase storage with sanitized filename.
        Removes directory prefixes and sanitizes to handle Cyrillic and special characters.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Log original name
        logger.info(f"📥 Original name: {name}")
        
        # ✅ STEP 1: Remove directory prefix FIRST (e.g., 'products/') - keep only filename
        if '/' in name:
            name = name.split('/')[-1]
            logger.info(f"🔧 Removed directory prefix, new name: {name}")
        
        # ✅ STEP 2: Sanitize the filename to handle Cyrillic and special characters
        sanitized_name = self._sanitize_filename(name)
        logger.info(f"✨ Sanitized name: {sanitized_name}")
        
        # ✅ STEP 3: Strip any leading slashes to ensure root-level save
        sanitized_name = sanitized_name.lstrip('/')
        
        # ✅ STEP 4: Generate unique name if file already exists (optional)
        # Uncomment if you want to avoid overwriting files
        # import uuid
        # from pathlib import Path
        # if sanitized_name:
        #     stem = Path(sanitized_name).stem
        #     ext = Path(sanitized_name).suffix
        #     sanitized_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
        
        logger.info(f"📁 Final path (root level): {sanitized_name}")
        
        # Read file content
        if hasattr(content, 'read'):
            file_content = content.read()
            # Reset file pointer if possible
            if hasattr(content, 'seek'):
                content.seek(0)
        else:
            file_content = content
            
        # Upload to Supabase
        try:
            response = self.client.storage.from_(self.bucket_name).upload(
                path=sanitized_name,
                file=file_content,
                file_options={"content-type": self._get_content_type(sanitized_name)}
            )
            logger.info(f"✅ Uploaded successfully to: {sanitized_name}")
            return sanitized_name
        except Exception as e:
            logger.error(f"❌ Upload failed: {str(e)}")
            # If file exists, try updating it
            try:
                response = self.client.storage.from_(self.bucket_name).update(
                    path=sanitized_name,
                    file=file_content,
                    file_options={"content-type": self._get_content_type(sanitized_name)}
                )
                logger.info(f"✅ Updated successfully: {sanitized_name}")
                return sanitized_name
            except Exception as update_error:
                logger.error(f"❌ Update also failed: {str(update_error)}")
                raise Exception(f"Failed to upload to Supabase: {update_error}")
    
    def _open(self, name, mode='rb'):
        """
        Retrieve file from Supabase storage
        """
        try:
            response = self.client.storage.from_(self.bucket_name).download(name)
            return ContentFile(response)
        except Exception as e:
            raise Exception(f"Failed to download from Supabase: {e}")
    
    def delete(self, name):
        """
        Delete file from Supabase storage
        """
        try:
            self.client.storage.from_(self.bucket_name).remove([name])
        except Exception as e:
            # Don't raise exception if file doesn't exist
            pass
    
    def exists(self, name):
        """
        Check if file exists in Supabase storage
        """
        try:
            files = self.client.storage.from_(self.bucket_name).list()
            return any(f['name'] == name for f in files)
        except:
            return False
    
    def url(self, name):
        """
        Return public URL for the file.
        Constructs a reliable public URL for Supabase storage.
        """
        if not name:
            return None
        
        # Clean the name - remove any leading slashes
        clean_name = name.lstrip('/')
        
        # URL encode the name to handle special characters
        # Use quote() to properly encode the path while keeping slashes
        encoded_name = quote(clean_name, safe='/')
        
        # Construct the public URL directly
        # This is more reliable than using get_public_url()
        public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{encoded_name}"
        
        return public_url
    
    def size(self, name):
        """
        Return file size
        """
        try:
            response = self.client.storage.from_(self.bucket_name).download(name)
            return len(response)
        except:
            return 0
    
    def _get_content_type(self, name):
        """
        Get content type based on file extension
        """
        ext = os.path.splitext(name)[1].lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.pdf': 'application/pdf',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
        }
        return content_types.get(ext, 'application/octet-stream')


def video_storage():
    """Factory function to create video storage instance"""
    return SupabaseStorage(bucket_name='product-videos')
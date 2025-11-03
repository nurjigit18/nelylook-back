import os
import uuid
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.conf import settings


class SupabaseStorage(Storage):
    """
    Custom storage backend for Supabase
    """
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.bucket_name = settings.SUPABASE_BUCKET_NAME
        
        # Lazy import to avoid issues if supabase isn't installed
        try:
            from supabase import create_client, Client
            self.client = create_client(self.supabase_url, self.supabase_key)
        except ImportError:
            raise ImportError("supabase package is required. Install it with: pip install supabase")
        
    def _save(self, name, content):
        """
        Save file to Supabase storage
        """
        # Generate unique filename if needed
        if not name:
            ext = os.path.splitext(content.name)[1] if hasattr(content, 'name') else ''
            name = f"{uuid.uuid4()}{ext}"
        
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
            self.client.storage.from_(self.bucket_name).upload(
                path=name,
                file=file_content,
                file_options={"content-type": self._get_content_type(name)}
            )
            return name
        except Exception as e:
            # If file exists, try updating it
            try:
                self.client.storage.from_(self.bucket_name).update(
                    path=name,
                    file=file_content,
                    file_options={"content-type": self._get_content_type(name)}
                )
                return name
            except Exception as update_error:
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
        Return public URL for the file
        ⚠️ FIXED: Properly handles the upload_to path
        """
        try:
            # Ensure name doesn't have leading slash
            clean_name = name.lstrip('/')
            # Get public URL using Supabase client
            response = self.client.storage.from_(self.bucket_name).get_public_url(clean_name)
            return response
        except Exception as e:
            # Fallback to constructed URL
            clean_name = name.lstrip('/')
            return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{clean_name}"
    
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
        }
        return content_types.get(ext, 'application/octet-stream')
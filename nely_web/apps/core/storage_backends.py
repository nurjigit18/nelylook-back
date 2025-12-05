"""
Custom storage backend for Supabase using native Python client
"""
from django.core.files.storage import Storage
from django.conf import settings
from supabase import create_client, Client
from io import BytesIO
import os


class SupabaseStorage(Storage):
    """
    Custom storage backend for Supabase Storage
    Uses native Supabase Python client instead of S3-compatible API
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.bucket_name = settings.SUPABASE_BUCKET_NAME
        self.location = getattr(settings, 'AWS_LOCATION', '')

        # Initialize Supabase client
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

    def _full_path(self, name):
        """Get the full path including location prefix"""
        # Normalize path separators (Windows uses backslash, but URLs need forward slash)
        name = name.replace('\\', '/')
        if self.location:
            return f"{self.location}/{name}"
        return name

    def _save(self, name, content):
        """
        Save file to Supabase Storage
        """
        # Get file path with location prefix
        file_path = self._full_path(name)

        # Read file content
        if hasattr(content, 'read'):
            file_data = content.read()
        else:
            file_data = content

        # Determine content type based on file extension
        content_type = self._get_content_type(name)

        try:
            # Upload to Supabase
            result = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={
                    "content-type": content_type,
                    "upsert": "false"  # Don't overwrite existing files
                }
            )
            return name
        except Exception as e:
            # If file exists, generate a new name
            if "already exists" in str(e).lower():
                name = self.get_available_name(name)
                return self._save(name, BytesIO(file_data))
            raise

    def _get_content_type(self, name):
        """Determine content type from file extension"""
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

    def _open(self, name, mode='rb'):
        """
        Open a file from Supabase Storage for reading
        """
        file_path = self._full_path(name)
        try:
            # Download file from Supabase
            file_data = self.client.storage.from_(self.bucket_name).download(file_path)
            return BytesIO(file_data)
        except Exception as e:
            raise Exception(f"Could not open file {name}: {str(e)}")

    def exists(self, name):
        """
        Check if file exists in Supabase Storage
        """
        file_path = self._full_path(name)
        try:
            # List files to check if it exists
            result = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(file_path) or None
            )
            filename = os.path.basename(file_path)
            return any(item['name'] == filename for item in result)
        except:
            return False

    def url(self, name):
        """
        Return the public URL for the file
        """
        file_path = self._full_path(name)
        # Get public URL
        public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
        return public_url

    def delete(self, name):
        """
        Delete file from Supabase Storage
        """
        file_path = self._full_path(name)
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
        except:
            pass

    def size(self, name):
        """
        Return the size of the file
        """
        # Supabase doesn't provide easy size lookup, return 0 as fallback
        return 0

    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's available in the storage
        """
        # Normalize path separators
        name = name.replace('\\', '/')
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        count = 1

        while self.exists(name):
            # file.ext becomes file_1.ext, file_2.ext, etc.
            name = os.path.join(dir_name, f"{file_root}_{count}{file_ext}").replace('\\', '/')
            if max_length and len(name) > max_length:
                raise Exception(f"Storage can not find an available filename for '{name}'")
            count += 1

        return name

# apps/media/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from apps.catalog.models import Product, ProductImage, Color
from apps.core.storage import SupabaseStorage
import logging

logger = logging.getLogger(__name__)


class UploadProductImageView(APIView):
    """
    API endpoint for uploading product images.
    
    POST /api/media/upload-product-image/
    
    Required fields:
    - image: File (required)
    - product_id: Integer (required)
    - color_id: Integer (optional)
    - is_primary: Boolean (optional)
    - alt_text: String (optional)
    - display_order: Integer (optional)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
            # Get uploaded file
            image_file = request.FILES.get('image')
            if not image_file:
                return Response(
                    {'error': 'No image file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get product ID
            product_id = request.data.get('product_id')
            if not product_id:
                return Response(
                    {'error': 'product_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify product exists
            try:
                product = Product.objects.get(product_id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {'error': f'Product with id {product_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get optional fields
            color_id = request.data.get('color_id')
            is_primary = request.data.get('is_primary', 'false').lower() == 'true'
            alt_text = request.data.get('alt_text', '')
            display_order = int(request.data.get('display_order', 1))
            
            # Verify color exists if provided
            color = None
            if color_id:
                try:
                    color = Color.objects.get(color_id=color_id)
                except Color.DoesNotExist:
                    return Response(
                        {'error': f'Color with id {color_id} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Create ProductImage instance
            product_image = ProductImage(
                product=product,
                color=color,
                image_file=image_file,  # This will trigger SupabaseStorage
                alt_text=alt_text or f"{product.product_name} image",
                is_primary=is_primary,
                display_order=display_order
            )
            
            # Save will automatically upload to Supabase and set image_url
            product_image.save()
            
            logger.info(
                f"Image uploaded successfully: {product_image.image_url} "
                f"for product {product.product_name}"
            )
            
            return Response({
                'status': 'success',
                'message': 'Image uploaded successfully',
                'data': {
                    'image_id': product_image.image_id,
                    'image_url': product_image.image_url,
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'color_name': color.color_name if color else None,
                    'is_primary': product_image.is_primary,
                    'display_order': product_image.display_order,
                }
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response(
                {'error': f'Invalid data: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to upload image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteProductImageView(APIView):
    """
    API endpoint for deleting product images.
    
    DELETE /api/media/delete-product-image/<image_id>/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def delete(self, request, image_id):
        try:
            # Get the image
            try:
                product_image = ProductImage.objects.get(image_id=image_id)
            except ProductImage.DoesNotExist:
                return Response(
                    {'error': f'Image with id {image_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Delete from Supabase storage
            if product_image.image_file:
                try:
                    storage = SupabaseStorage()
                    storage.delete(product_image.image_file.name)
                except Exception as e:
                    logger.warning(f"Failed to delete file from storage: {e}")
            
            # Delete from database
            product_name = product_image.product.product_name
            product_image.delete()
            
            logger.info(f"Image {image_id} deleted successfully for product {product_name}")
            
            return Response({
                'status': 'success',
                'message': 'Image deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error deleting image: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to delete image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListProductImagesView(APIView):
    """
    API endpoint for listing all images for a product.
    
    GET /api/media/product-images/<product_id>/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, product_id):
        try:
            # Verify product exists
            try:
                product = Product.objects.get(product_id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {'error': f'Product with id {product_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get all images for the product
            images = ProductImage.objects.filter(product=product).select_related('color').order_by('display_order')
            
            image_data = [{
                'image_id': img.image_id,
                'image_url': img.image_url,
                'alt_text': img.alt_text,
                'is_primary': img.is_primary,
                'display_order': img.display_order,
                'color_id': img.color.color_id if img.color else None,
                'color_name': img.color.color_name if img.color else None,
                'color_code': img.color.color_code if img.color else None,
            } for img in images]
            
            return Response({
                'status': 'success',
                'data': {
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'images': image_data,
                    'total_images': len(image_data)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error listing images: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to list images: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Alias for backward compatibility
UploadProductImage = UploadProductImageView
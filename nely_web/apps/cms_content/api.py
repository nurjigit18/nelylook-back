from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from wagtail.images import get_image_model
from .models import SocialLink, ContactInformation


# Custom API views with AllowAny permission (public access)
class PublicPagesAPIViewSet(PagesAPIViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []

    def detail_view(self, request, pk):
        """Override detail view to expand image data"""
        response = super().detail_view(request, pk)
        if response.status_code == 200:
            response.data = self._expand_images(response.data)
        return response

    def listing_view(self, request):
        """Override listing view to expand image data"""
        response = super().listing_view(request)
        if response.status_code == 200 and 'items' in response.data:
            response.data['items'] = [self._expand_images(item) for item in response.data['items']]
        return response

    def _expand_images(self, data):
        """Recursively expand image IDs to full image objects"""
        Image = get_image_model()

        if isinstance(data, dict):
            # Process hero_banners
            if 'hero_banners' in data:
                for banner in data['hero_banners']:
                    if 'value' in banner and 'image' in banner['value']:
                        image_id = banner['value']['image']
                        if isinstance(image_id, int):
                            try:
                                image = Image.objects.get(id=image_id)
                                banner['value']['image'] = {
                                    'id': image.id,
                                    'title': image.title,
                                    'url': image.file.url,
                                    'width': image.width,
                                    'height': image.height,
                                }
                            except Image.DoesNotExist:
                                banner['value']['image'] = None

            # Process collection_tiles
            if 'collection_tiles' in data:
                for tile in data['collection_tiles']:
                    if 'value' in tile and 'image' in tile['value']:
                        image_id = tile['value']['image']
                        if isinstance(image_id, int):
                            try:
                                image = Image.objects.get(id=image_id)
                                tile['value']['image'] = {
                                    'id': image.id,
                                    'title': image.title,
                                    'url': image.file.url,
                                    'width': image.width,
                                    'height': image.height,
                                }
                            except Image.DoesNotExist:
                                tile['value']['image'] = None

            # Process collection_banner
            if 'collection_banner' in data:
                for banner in data['collection_banner']:
                    if 'value' in banner and 'image' in banner['value']:
                        image_id = banner['value']['image']
                        if isinstance(image_id, int):
                            try:
                                image = Image.objects.get(id=image_id)
                                banner['value']['image'] = {
                                    'id': image.id,
                                    'title': image.title,
                                    'url': image.file.url,
                                    'width': image.width,
                                    'height': image.height,
                                }
                            except Image.DoesNotExist:
                                banner['value']['image'] = None

        return data


class PublicImagesAPIViewSet(ImagesAPIViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []


class PublicDocumentsAPIViewSet(DocumentsAPIViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []


# Create the API router
api_router = WagtailAPIRouter('wagtailapi')

# Register public API endpoints (no authentication required)
api_router.register_endpoint('pages', PublicPagesAPIViewSet)
api_router.register_endpoint('images', PublicImagesAPIViewSet)
api_router.register_endpoint('documents', PublicDocumentsAPIViewSet)


# Custom API endpoint for contact information
@api_view(['GET'])
@permission_classes([AllowAny])  # Public endpoint
def contact_info_api(request):
    """
    API endpoint for contact information
    Returns the contact information managed in Wagtail CMS

    Example response:
    {
        "address": "ул. Токтогула 123\nБишкек, Кыргызстан",
        "phones": "+996 708 200 125\n+996 708 268 626",
        "emails": "info@nelylook.com\nsupport@nelylook.com",
        "working_hours": "Пн-Пт: 10:00 - 20:00\nСб-Вс: 11:00 - 19:00",
        "social_media": {
            "whatsapp": "https://wa.me/996708200125",
            "telegram": "https://t.me/nelylook",
            "instagram": "https://instagram.com/nelylook"
        }
    }
    """
    contact = ContactInformation.load()

    data = {
        'address': contact.address,
        'phones': contact.phones,
        'emails': contact.emails,
        'working_hours': contact.working_hours,
        'social_media': {
            'whatsapp': contact.whatsapp_url,
            'telegram': contact.telegram_url,
            'instagram': contact.instagram_url,
        }
    }

    return Response(data)


# Custom API endpoint for social links
@api_view(['GET'])
@permission_classes([AllowAny])  # Public endpoint
def social_links_api(request):
    """
    API endpoint for social media links
    Returns all active social links ordered by display_order

    Example response:
    {
        "data": [
            {
                "platform": "instagram",
                "url": "https://instagram.com/nely.look",
                "display_order": 0
            },
            ...
        ]
    }
    """
    links = SocialLink.objects.filter(is_active=True)

    data = [
        {
            'platform': link.platform,
            'url': link.url,
            'display_order': link.display_order,
        }
        for link in links
    ]

    return Response({'data': data})

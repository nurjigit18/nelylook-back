# apps/catalog/views.py
import logging
from django.db.models import Q, F, Prefetch, Count, Min, Max
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.response_utils import APIResponse
from .models import (
    Product, ProductVariant, ProductImage, 
    Category, ClothingType, Collection, 
    Color, Size, RelatedProduct
)
from .serializers import (
    ProductSerializer, ProductDetailSerializer,
    CategorySerializer, ClothingTypeSerializer,
    CollectionSerializer, ColorSerializer, SizeSerializer,
    ProductVariantSerializer
)
from .filters import ProductFilter

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'category_id'
    pagination_class = None
    
    def get_queryset(self):
        qs = super().get_queryset()
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            qs = qs.filter(parent_category_id=parent_id)
        if self.request.query_params.get('root_only') == 'true':
            qs = qs.filter(parent_category__isnull=True)
        return qs.order_by('display_order', 'category_name')
    
    @action(detail=True, methods=['get'])
    def products(self, request, category_id=None):
        category = self.get_object()
        products = Product.objects.filter(
            category=category,
            status='active'
        ).select_related('category', 'clothing_type')
        serializer = ProductSerializer(products, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Products in {category.category_name}"
        )
    
    @action(detail=True, methods=['get'])
    def children(self, request, category_id=None):
        category = self.get_object()
        children = category.children.filter(is_active=True)
        serializer = self.get_serializer(children, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Subcategories of {category.category_name}"
        )
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message=f"Category details: {instance.category_name}"
        )


class ClothingTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClothingType.objects.filter(is_active=True)
    serializer_class = ClothingTypeSerializer
    permission_classes = [AllowAny]
    lookup_field = 'type_id'
    
    def get_queryset(self):
        qs = super().get_queryset()
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs.select_related('category').order_by('display_order', 'type_name')


class ColorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Color.objects.filter(is_active=True)
    serializer_class = ColorSerializer
    permission_classes = [AllowAny]
    lookup_field = 'color_id'
    
    def get_queryset(self):
        qs = super().get_queryset()
        family = self.request.query_params.get('family')
        if family:
            qs = qs.filter(color_family__iexact=family)
        return qs.order_by('color_name')


class SizeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Size.objects.filter(is_active=True)
    serializer_class = SizeSerializer
    permission_classes = [AllowAny]
    lookup_field = 'size_id'
    
    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(size_category__iexact=category)
        return qs.order_by('sort_order', 'size_name')
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message=f"Size details: {instance.size_name}"
        )


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Collection.objects.filter(is_active=True)
    serializer_class = CollectionSerializer
    permission_classes = [AllowAny]
    lookup_field = 'collection_id'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('featured') == 'true':
            qs = qs.filter(is_featured=True)
        return qs.order_by('display_order', '-created_at')

    def get_object(self):
        """Override to support both ID and slug lookups"""
        lookup_value = self.kwargs.get(self.lookup_field)

        # Try to get by ID first
        if lookup_value and lookup_value.isdigit():
            return super().get_object()

        # Otherwise, treat as slug
        queryset = self.filter_queryset(self.get_queryset())
        obj = queryset.filter(collection_slug=lookup_value).first()

        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Collection not found")

        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, methods=['get'])
    def products(self, request, collection_id=None):
        collection = self.get_object()
        products = Product.objects.filter(
            collection_memberships__collection=collection,
            status='active'
        ).select_related('category', 'clothing_type').distinct()
        serializer = ProductSerializer(products, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Products in {collection.collection_name} collection"
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message=f"Collection details: {instance.collection_name}"
        )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Main Product ViewSet with slug filtering support
    """
    queryset = Product.objects.filter(status='active')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    lookup_field = 'product_id'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['product_name', 'description', 'product_code']
    ordering_fields = ['created_at', 'base_price', 'product_name', 'stock_quantity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """✅ ADD SLUG FILTERING HERE"""
        qs = super().get_queryset()
        
        # Handle slug filtering manually (not through filter_backends)
        slug = self.request.query_params.get('slug')
        if slug:
            logger.info(f"🔍 Filtering by slug: {slug}")
            qs = qs.filter(slug=slug)
        
        # Prefetch related data
        qs = qs.select_related('category', 'clothing_type')
        
        # Detailed prefetch for single product views
        if self.action == 'retrieve' or slug:
            logger.info("📦 Prefetching variants and images")
            qs = qs.prefetch_related(
                Prefetch(
                    'variants',
                    queryset=ProductVariant.objects.filter(status='active').select_related('size', 'color')
                ),
                Prefetch(
                    'images',
                    queryset=ProductImage.objects.select_related('color').order_by('display_order')
                )
            )
        
        return qs
    
    def get_serializer_class(self):
        """Use detailed serializer for single products"""
        if self.action == 'retrieve' or self.request.query_params.get('slug'):
            return ProductDetailSerializer
        return ProductSerializer
    
    def list(self, request, *args, **kwargs):
        """Override list to handle slug lookups"""
        slug = request.query_params.get('slug')
        
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # If slug filter, check if product exists
            if slug:
                count = queryset.count()
                logger.info(f"📦 Found {count} products with slug: {slug}")
                
                if count == 0:
                    logger.warning(f"⚠️ No product found with slug: {slug}")
                    return APIResponse.error(
                        message=f"Product not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
            
            # Pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(
                data=serializer.data,
                message="Products retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"❌ Error in list: {str(e)}", exc_info=True)
            return APIResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            logger.info(f"✅ Retrieved: {instance.product_name}")
            return APIResponse.success(
                data=serializer.data,
                message=f"Product: {instance.product_name}"
            )
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}", exc_info=True)
            return APIResponse.error(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        products = self.get_queryset().filter(is_featured=True)[:12]
        serializer = self.get_serializer(products, many=True)
        return APIResponse.success(data=serializer.data, message="Featured products")
    
    @action(detail=False, methods=['get'], url_path='new-arrivals')
    def new_arrivals(self, request):
        products = self.get_queryset().filter(is_new_arrival=True).order_by('-created_at')[:20]
        serializer = self.get_serializer(products, many=True)
        return APIResponse.success(data=serializer.data, message="New arrivals")
    
    @action(detail=False, methods=['get'])
    def bestsellers(self, request):
        products = self.get_queryset().filter(is_bestseller=True)[:12]
        serializer = self.get_serializer(products, many=True)
        return APIResponse.success(data=serializer.data, message="Bestsellers")
    
    @action(detail=True, methods=['get'])
    def related(self, request, product_id=None):
        product = self.get_object()
        related_ids = RelatedProduct.objects.filter(product=product).values_list('related_product_id', flat=True)
        related_products = Product.objects.filter(
            product_id__in=related_ids,
            status='active'
        ).select_related('category', 'clothing_type')
        serializer = ProductSerializer(related_products, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Related to {product.product_name}"
        )

    @action(detail=True, methods=['get'], url_path='see-also')
    def see_also(self, request, product_id=None):
        """
        Get 'See Also' products - products from the same category,
        excluding the current product and already-related products.
        """
        product = self.get_object()

        # Get related product IDs to exclude them
        related_ids = list(RelatedProduct.objects.filter(
            product=product
        ).values_list('related_product_id', flat=True))

        # Exclude current product and related products
        exclude_ids = [product.product_id] + related_ids

        # Get products from the same category
        see_also_products = Product.objects.filter(
            category=product.category,
            status='active'
        ).exclude(
            product_id__in=exclude_ids
        ).select_related('category', 'clothing_type').prefetch_related(
            Prefetch(
                'images',
                queryset=ProductImage.objects.select_related('color').order_by('-is_primary', 'display_order')
            ),
            Prefetch(
                'variants',
                queryset=ProductVariant.objects.filter(status='active').select_related('color')
            )
        ).order_by('-is_featured', '-is_new_arrival', '-created_at')[:8]

        # Build response with images array for hover effect
        result = []
        for p in see_also_products:
            # Get primary image and additional images
            all_images = []
            primary_img = None

            for img in p.images.all():
                img_url = img.image_url
                if not img_url and img.image_file:
                    from apps.core.storage import SupabaseStorage
                    storage = SupabaseStorage()
                    filename = img.image_file.name
                    if '/' in filename:
                        filename = filename.split('/')[-1]
                    img_url = storage.url(filename)

                if img_url:
                    if img.is_primary:
                        primary_img = img_url
                    else:
                        all_images.append(img_url)

            # Put primary first
            images = []
            if primary_img:
                images.append(primary_img)
            images.extend(all_images)
            images = images[:3]  # Limit to 3 for hover effect

            # Get default variant ID
            default_variant = p.variants.first()

            result.append({
                'id': p.product_id,
                'slug': p.slug,
                'name': p.product_name,
                'base_price': str(p.base_price),
                'sale_price': str(p.sale_price) if p.sale_price else None,
                'primary_image': images[0] if images else None,
                'images': images,
                'category_name': p.category.category_name if p.category else None,
                'default_variant_id': default_variant.variant_id if default_variant else None,
            })

        return APIResponse.success(
            data=result,
            message=f"See also products for {product.product_name}"
        )
    
    @action(detail=True, methods=['get'])
    def variants(self, request, product_id=None):
        product = self.get_object()
        variants = product.variants.select_related('size', 'color').filter(status='active')

        # Filter by color if provided
        color_id = request.query_params.get('color')
        if color_id:
            variants = variants.filter(color_id=color_id)

        serializer = ProductVariantSerializer(variants, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Variants for {product.product_name}"
        )

    @action(detail=True, methods=['get'], url_path='variant-by-options')
    def variant_by_options(self, request, product_id=None):
        """Get specific variant by color and size"""
        product = self.get_object()
        color_id = request.query_params.get('color')
        size_id = request.query_params.get('size')

        if not color_id or not size_id:
            return APIResponse.error(
                message="Both color and size are required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            variant = product.variants.select_related('size', 'color').get(
                color_id=color_id,
                size_id=size_id,
                status='active'
            )
            serializer = ProductVariantSerializer(variant)
            return APIResponse.success(
                data=serializer.data,
                message=f"Variant found"
            )
        except ProductVariant.DoesNotExist:
            return APIResponse.error(
                message="No variant found with the specified color and size",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except ProductVariant.MultipleObjectsReturned:
            # If multiple variants exist (shouldn't happen), return the first one
            variant = product.variants.select_related('size', 'color').filter(
                color_id=color_id,
                size_id=size_id,
                status='active'
            ).first()
            serializer = ProductVariantSerializer(variant)
            return APIResponse.success(
                data=serializer.data,
                message=f"Variant found"
            )
    
    @action(detail=True, methods=['get'])
    def colors(self, request, product_id=None):
        product = self.get_object()
        colors = Color.objects.filter(
            variants__product=product,
            variants__status='active'
        ).distinct()
        serializer = ColorSerializer(colors, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Colors for {product.product_name}"
        )
    
    @action(detail=True, methods=['get'])
    def sizes(self, request, product_id=None):
        product = self.get_object()
        color_id = request.query_params.get('color')
        sizes_query = Size.objects.filter(
            variants__product=product,
            variants__status='active'
        )
        if color_id:
            sizes_query = sizes_query.filter(variants__color_id=color_id)
        sizes = sizes_query.distinct().order_by('sort_order')
        serializer = SizeSerializer(sizes, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Sizes for {product.product_name}"
        )
    
    @action(detail=False, methods=['get'])
    def filters(self, request):
        products = self.get_queryset()
        price_range = products.aggregate(
            min_price=Min('base_price'),
            max_price=Max('base_price')
        )
        categories = Category.objects.filter(
            products__in=products,
            is_active=True
        ).distinct().values('category_id', 'category_name')
        colors = Color.objects.filter(
            variants__product__in=products,
            is_active=True
        ).distinct().values('color_id', 'color_name', 'color_code')
        sizes = Size.objects.filter(
            variants__product__in=products,
            is_active=True
        ).distinct().order_by('sort_order').values('size_id', 'size_name')
        
        return APIResponse.success(
            data={
                'price_range': price_range,
                'categories': list(categories),
                'colors': list(colors),
                'sizes': list(sizes),
                'seasons': [
                    {'value': choice[0], 'label': choice[1]} 
                    for choice in Product._meta.get_field('season').choices
                ],
            },
            message="Filter options"
        )
        
    @action(detail=False, methods=['get'], url_path='by-color')
    def by_color(self, request):
        """
        Get products expanded by color variants.
        Returns one "product card" per color variant.
        """
        from django.db.models import Prefetch, Min
        
        products = self.filter_queryset(self.get_queryset())
        
        products = products.prefetch_related(
            Prefetch(
                'variants', 
                queryset=ProductVariant.objects.select_related('color', 'size').filter(
                    status='active',
                    stock_quantity__gt=0
                ).order_by('size__sort_order')  # ✅ Order by size to get consistent "first" variant
            ),
            Prefetch(
                'images', 
                queryset=ProductImage.objects.select_related('color').order_by('display_order')
            )
        )
        
        color_variants = []
        
        for product in products:
            colors_data = {}
            
            for variant in product.variants.all():
                if not variant.color:
                    continue
                    
                color_id = variant.color.color_id
                
                if color_id not in colors_data:
                    colors_data[color_id] = {
                        'color': variant.color,
                        'sizes': set(),
                        'stock': 0,
                        'default_variant_id': variant.variant_id,  # ✅ First variant for this color
                    }
                
                if variant.size:
                    colors_data[color_id]['sizes'].add(variant.size.size_name)
                colors_data[color_id]['stock'] += variant.stock_quantity
        
            for color_id, color_info in colors_data.items():
                if color_info['stock'] <= 0:
                    continue

                color = color_info['color']

                # Collect ALL images for this color (up to 3 for hover effect)
                color_images = []
                primary_img = None

                for img in product.images.all():
                    if img.color_id == color_id:
                        img_url = None
                        if img.image_url:
                            img_url = img.image_url
                        elif img.image_file:
                            from apps.core.storage import SupabaseStorage
                            storage = SupabaseStorage()
                            filename = img.image_file.name
                            if '/' in filename:
                                filename = filename.split('/')[-1]
                            img_url = storage.url(filename)

                        if img_url:
                            if img.is_primary:
                                primary_img = img_url
                            else:
                                color_images.append(img_url)

                # Put primary image first, then others (limit to 3 total)
                all_images = []
                if primary_img:
                    all_images.append(primary_img)
                all_images.extend(color_images)
                all_images = all_images[:3]  # Limit to 3 images for hover zones

                color_variant = {
                    'id': product.product_id,
                    'slug': product.slug,
                    'name': product.product_name,
                    'color_id': color.color_id,
                    'color_name': color.color_name,
                    'color_code': color.color_code or '#CCCCCC',
                    'primary_image': all_images[0] if all_images else None,
                    'images': all_images,  # All images for hover effect
                    'base_price': str(product.base_price),
                    'sale_price': str(product.sale_price) if product.sale_price else None,
                    'available_sizes': sorted(list(color_info['sizes'])),
                    'is_featured': product.is_featured,
                    'is_new_arrival': product.is_new_arrival,
                    'is_bestseller': product.is_bestseller,
                    'category': product.category.category_name if product.category else None,
                    'season': product.season,
                    'stock_quantity': color_info['stock'],
                    'default_variant_id': color_info['default_variant_id'],
                }

                color_variants.append(color_variant)
        
        color_variants.sort(key=lambda x: (x['name'], x['color_name']))
        
        page = self.paginate_queryset(color_variants)
        if page is not None:
            return self.get_paginated_response(page)
        
        return APIResponse.success(
            data=color_variants,
            message=f"Found {len(color_variants)} color variants"
        )
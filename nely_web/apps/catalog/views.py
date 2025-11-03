# apps/catalog/views.py
from django.db.models import Q, Prefetch, Count, Min, Max
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductFilter

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
)
from .filters import ProductFilter  # We'll create this


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for categories.
    
    List: GET /catalog/categories/
    Retrieve: GET /catalog/categories/{id}/
    Get products in category: GET /catalog/categories/{id}/products/
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'category_id'
    
    def get_queryset(self):
        """Filter to show only active categories, with optional parent filter."""
        qs = super().get_queryset()
        
        # Filter by parent category
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            qs = qs.filter(parent_category_id=parent_id)
        
        # Get root categories only (no parent)
        if self.request.query_params.get('root_only') == 'true':
            qs = qs.filter(parent_category__isnull=True)
        
        return qs.order_by('display_order', 'category_name')
    
    @action(detail=True, methods=['get'])
    def products(self, request, category_id=None):
        """Get all products in this category."""
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
        """Get child categories."""
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
    """
    ViewSet for clothing types.
    
    List: GET /catalog/clothing-types/
    Retrieve: GET /catalog/clothing-types/{id}/
    Filter by category: GET /catalog/clothing-types/?category={id}
    """
    queryset = ClothingType.objects.filter(is_active=True)
    serializer_class = ClothingTypeSerializer
    permission_classes = [AllowAny]
    lookup_field = 'type_id'
    
    def get_queryset(self):
        """Filter by category if provided."""
        qs = super().get_queryset()
        
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        
        return qs.select_related('category').order_by('display_order', 'type_name')


class ColorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for colors.
    
    List: GET /catalog/colors/
    Retrieve: GET /catalog/colors/{id}/
    """
    queryset = Color.objects.filter(is_active=True)
    serializer_class = ColorSerializer
    permission_classes = [AllowAny]
    lookup_field = 'color_id'
    
    def get_queryset(self):
        """Optionally filter by color family."""
        qs = super().get_queryset()
        
        family = self.request.query_params.get('family')
        if family:
            qs = qs.filter(color_family__iexact=family)
        
        return qs.order_by('color_name')


class SizeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for sizes.
    
    List: GET /catalog/sizes/
    Retrieve: GET /catalog/sizes/{id}/
    Filter by category: GET /catalog/sizes/?category={category}
    """
    queryset = Size.objects.filter(is_active=True)
    serializer_class = SizeSerializer
    permission_classes = [AllowAny]
    lookup_field = 'size_id'
    
    def get_queryset(self):
        """Filter by size category if provided."""
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
    """
    ViewSet for collections.
    
    List: GET /catalog/collections/
    Retrieve: GET /catalog/collections/{id}/
    Get featured: GET /catalog/collections/?featured=true
    Get products: GET /catalog/collections/{id}/products/
    """
    queryset = Collection.objects.filter(is_active=True)
    serializer_class = CollectionSerializer
    permission_classes = [AllowAny]
    lookup_field = 'collection_id'
    
    def get_queryset(self):
        """Filter collections."""
        qs = super().get_queryset()
        
        # Featured collections only
        if self.request.query_params.get('featured') == 'true':
            qs = qs.filter(is_featured=True)
        
        return qs.order_by('display_order', '-created_at')
    
    @action(detail=True, methods=['get'])
    def products(self, request, collection_id=None):
        """Get all products in this collection."""
        collection = self.get_object()
        
        # Get products through the junction table
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
            message=f"Size details: {instance.collection_name}"
        )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
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
        """Optimized queryset with prefetching."""
        qs = super().get_queryset()
        
        # ✅ Add slug filtering support
        slug = self.request.query_params.get('slug')
        if slug:
            logger.info(f"Filtering products by slug: {slug}")
            qs = qs.filter(slug=slug)
        
        # Prefetch related data for efficiency
        qs = qs.select_related('category', 'clothing_type')
        
        # Add prefetch for variants and images if detail view or slug lookup
        if self.action == 'retrieve' or slug:
            qs = qs.prefetch_related(
                Prefetch('variants', queryset=ProductVariant.objects.select_related('size', 'color')),
                Prefetch('images', queryset=ProductImage.objects.select_related('color').order_by('display_order'))
            )
        
        return qs
    
    def list(self, request, *args, **kwargs):
        """Override list to add logging"""
        slug = request.query_params.get('slug')
        if slug:
            logger.info(f"📍 List action with slug filter: {slug}")
        
        response = super().list(request, *args, **kwargs)
        
        if slug:
            logger.info(f"📦 Returned {len(response.data.get('results', []))} products for slug: {slug}")
        
        return response

    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products."""
        products = self.get_queryset().filter(is_featured=True)[:12]
        serializer = self.get_serializer(products, many=True)
        
        return APIResponse.success(
            data=serializer.data,
            message="Featured products"
        )
    
    @action(detail=False, methods=['get'], url_path='new-arrivals')
    def new_arrivals(self, request):
        """Get new arrival products."""
        try:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info("🔍 Fetching new arrivals...")
            
            # Get products
            products = self.get_queryset().filter(is_new_arrival=True).order_by('-created_at')[:20]
            logger.info(f"📦 Found {products.count()} products")
            
            # Serialize
            logger.info("🔄 Serializing products...")
            serializer = self.get_serializer(products, many=True)
            
            logger.info("✅ Serialization complete")
            data = serializer.data
            logger.info(f"📊 Serialized {len(data)} products")
            
            return APIResponse.success(
                data=data,
                message="New arrivals"
            )
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            
            # Log the full error
            logger.error("❌ Error in new_arrivals:")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("Full traceback:")
            logger.error(traceback.format_exc())
            
            return APIResponse.error(
                message=f"Error fetching new arrivals: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def bestsellers(self, request):
        """Get bestseller products."""
        products = self.get_queryset().filter(is_bestseller=True)[:12]
        serializer = self.get_serializer(products, many=True)
        
        return APIResponse.success(
            data=serializer.data,
            message="Bestsellers"
        )
    
    @action(detail=True, methods=['get'])
    def related(self, request, product_id=None):
        """Get related products."""
        product = self.get_object()
        
        # Get related products
        related_ids = RelatedProduct.objects.filter(
            product=product
        ).values_list('related_product_id', flat=True)
        
        related_products = Product.objects.filter(
            product_id__in=related_ids,
            status='active'
        ).select_related('category', 'clothing_type')
        
        serializer = ProductSerializer(related_products, many=True)
        
        return APIResponse.success(
            data=serializer.data,
            message=f"Products related to {product.product_name}"
        )
    
    @action(detail=True, methods=['get'])
    def variants(self, request, product_id=None):
        """Get all variants for a product with stock info."""
        product = self.get_object()
        variants = product.variants.select_related('size', 'color').filter(status='active')
        
        # You'll need to create a ProductVariantSerializer
        from .serializers import ProductVariantSerializer
        serializer = ProductVariantSerializer(variants, many=True)
        
        return APIResponse.success(
            data=serializer.data,
            message=f"Variants for {product.product_name}"
        )
    
    @action(detail=True, methods=['get'])
    def colors(self, request, product_id=None):
        """Get available colors for a product."""
        product = self.get_object()
        
        # Get unique colors from variants
        colors = Color.objects.filter(
            variants__product=product,
            variants__status='active'
        ).distinct()
        
        serializer = ColorSerializer(colors, many=True)
        
        return APIResponse.success(
            data=serializer.data,
            message=f"Available colors for {product.product_name}"
        )
    
    @action(detail=True, methods=['get'])
    def sizes(self, request, product_id=None):
        """Get available sizes for a product, optionally filtered by color."""
        product = self.get_object()
        color_id = request.query_params.get('color')
        
        # Base query for sizes
        sizes_query = Size.objects.filter(
            variants__product=product,
            variants__status='active'
        )
        
        # Filter by color if provided
        if color_id:
            sizes_query = sizes_query.filter(variants__color_id=color_id)
        
        sizes = sizes_query.distinct().order_by('sort_order')
        serializer = SizeSerializer(sizes, many=True)
        
        return APIResponse.success(
            data=serializer.data,
            message=f"Available sizes for {product.product_name}"
        )
    
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get available filter options (categories, colors, sizes, price range)."""
        # Get active products
        products = self.get_queryset()
        
        # Get price range
        price_range = products.aggregate(
            min_price=Min('base_price'),
            max_price=Max('base_price')
        )
        
        # Get available categories
        categories = Category.objects.filter(
            products__in=products,
            is_active=True
        ).distinct().values('category_id', 'category_name')
        
        # Get available colors
        colors = Color.objects.filter(
            variants__product__in=products,
            is_active=True
        ).distinct().values('color_id', 'color_name', 'color_code')
        
        # Get available sizes
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
                'seasons': [{'value': choice[0], 'label': choice[1]} for choice in Product._meta.get_field('season').choices],
            },
            message="Available filter options"
        )
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve product by slug instead of product_id
        """
        slug = kwargs.get('product_id')  # The URL parameter is still called product_id
        
        try:
            # Try to get by slug first
            instance = Product.objects.select_related(
                'category', 'clothing_type'
            ).prefetch_related(
                Prefetch('variants', queryset=ProductVariant.objects.select_related('size', 'color')),
                Prefetch('images', queryset=ProductImage.objects.select_related('color').order_by('display_order'))
            ).get(slug=slug, status='active')
        except Product.DoesNotExist:
            # Fallback to product_id if slug doesn't work
            try:
                instance = Product.objects.select_related(
                    'category', 'clothing_type'
                ).prefetch_related(
                    Prefetch('variants', queryset=ProductVariant.objects.select_related('size', 'color')),
                    Prefetch('images', queryset=ProductImage.objects.select_related('color').order_by('display_order'))
                ).get(product_id=slug, status='active')
            except (Product.DoesNotExist, ValueError):
                return APIResponse.error(
                    message="Product not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
        
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message=f"Product details: {instance.product_name}"
        )

from django.db import models
from django import forms
from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.blocks import CharBlock, RichTextBlock, URLBlock, StructBlock
from wagtail.images.blocks import ImageChooserBlock
from rest_framework import serializers
from wagtail.snippets.models import register_snippet
from wagtail.api import APIField
from wagtail.images.api.fields import ImageRenditionField


# Custom URL field that accepts relative URLs
class RelativeURLBlock(CharBlock):
    """URL block that accepts both absolute and relative URLs"""
    def __init__(self, required=True, help_text=None, max_length=None, min_length=None, **kwargs):
        super().__init__(required=required, help_text=help_text, max_length=max_length, min_length=min_length, **kwargs)

    class Meta:
        icon = "link"


# ============================================================
# STREAMFIELD BLOCKS
# ============================================================

class HeroBannerBlock(StructBlock):
    """Hero banner with image, text, and CTA"""
    image = ImageChooserBlock(required=True, help_text="Banner image (recommended size: 1920x800px)")
    title = CharBlock(required=True, max_length=100, help_text="Banner title")
    description = RichTextBlock(required=False, help_text="Banner description")
    cta_text = CharBlock(required=False, max_length=50, help_text="Button text (e.g., 'Перейти', 'Узнать больше')")
    cta_link = RelativeURLBlock(required=False, help_text="Button link (e.g., '/collections/evening' or 'https://example.com')")

    class Meta:
        icon = 'image'
        label = 'Hero Banner'


class CollectionTileBlock(StructBlock):
    """Collection tile with image and text"""
    image = ImageChooserBlock(required=True, help_text="Tile image (recommended size: 600x800px)")
    title = CharBlock(required=True, max_length=100, help_text="Tile title")
    description = RichTextBlock(required=False, help_text="Tile description")
    link = RelativeURLBlock(required=True, help_text="Collection link (e.g., '/collections/spring-2025' or 'https://example.com')")

    class Meta:
        icon = 'grip'
        label = 'Collection Tile'


class CollectionBannerBlock(StructBlock):
    """Large collection banner"""
    image = ImageChooserBlock(required=False, help_text="Banner background image (recommended size: 1920x600px)")
    title = CharBlock(required=True, max_length=200, help_text="Banner title (supports line breaks with \\n)")
    description = RichTextBlock(required=False, help_text="Banner description")
    cta_text = CharBlock(required=False, max_length=50, help_text="Button text")
    cta_link = RelativeURLBlock(required=False, help_text="Button link (e.g., '/collections/spring-2025' or 'https://example.com')")

    class Meta:
        icon = 'doc-full'
        label = 'Collection Banner'


# ============================================================
# HOMEPAGE
# ============================================================

class HomePage(Page):
    """Main homepage with hero banners and collection tiles"""

    # Limit to one instance
    max_count = 1

    # Hero Banners (carousel)
    hero_banners = StreamField([
        ('hero_banner', HeroBannerBlock()),
    ], blank=True, use_json_field=True, help_text="Add multiple banners to create a carousel")

    # Collection Tiles
    collection_tiles = StreamField([
        ('collection_tile', CollectionTileBlock()),
    ], blank=True, use_json_field=True, help_text="Add 4 collection tiles for the grid")

    # Collection Banner
    collection_banner = StreamField([
        ('collection_banner', CollectionBannerBlock()),
    ], blank=True, max_num=1, use_json_field=True, help_text="Add one collection banner")

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('hero_banners'),
        ], heading="🎠 Hero Carousel"),

        MultiFieldPanel([
            FieldPanel('collection_tiles'),
        ], heading="🎨 Collection Tiles"),

        MultiFieldPanel([
            FieldPanel('collection_banner'),
        ], heading="📢 Collection Banner"),
    ]

    api_fields = [
        APIField('hero_banners'),
        APIField('collection_tiles'),
        APIField('collection_banner'),
    ]

    class Meta:
        verbose_name = "Home Page"


# ============================================================
# STANDARD TEXT PAGES (About, FAQ, Contacts, etc.)
# ============================================================

class StandardPage(Page):
    """Text pages with rich content"""

    body = StreamField([
        ('heading', CharBlock(form_classname="title", icon="title", help_text="Section heading")),
        ('paragraph', RichTextBlock(icon="pilcrow", help_text="Paragraph text with formatting")),
        ('image', ImageChooserBlock(icon="image", help_text="Add an image")),
    ], blank=True, use_json_field=True, help_text="Build your page content with these blocks")

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    api_fields = [
        APIField('body'),
    ]

    class Meta:
        verbose_name = "Text Page"
        verbose_name_plural = "Text Pages"


# ============================================================
# COLLECTION PAGE
# ============================================================

class CollectionPage(Page):
    """Collection page with hero banner"""

    # Hero section
    hero_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Collection hero image (recommended size: 1920x600px)"
    )

    hero_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Hero title (leave blank to use page title)"
    )

    hero_description = RichTextField(
        blank=True,
        help_text="Hero description text"
    )

    # Collection slug/identifier (to match with Django collections)
    collection_slug = models.CharField(
        max_length=100,
        blank=True,
        help_text="Collection identifier (e.g., 'spring-2025', 'evening', 'everyday'). Must match your Django collection slug."
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('hero_image'),
            FieldPanel('hero_title'),
            FieldPanel('hero_description'),
        ], heading="🖼️ Hero Section"),

        FieldPanel('collection_slug', help_text="⚠️ Important: This must match the collection slug in your Django catalog"),
    ]

    api_fields = [
        APIField('hero_image', serializer=ImageRenditionField('fill-1920x600')),
        APIField('hero_title'),
        APIField('hero_description'),
        APIField('collection_slug'),
    ]

    class Meta:
        verbose_name = "Collection Page"
        verbose_name_plural = "Collection Pages"


# ============================================================
# SOCIAL MEDIA LINKS (Footer)
# ============================================================

@register_snippet
class SocialLink(models.Model):
    """Social media link for footer"""

    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'),
        ('tiktok', 'TikTok'),
        ('facebook', 'Facebook'),
        ('telegram', 'Telegram'),
        ('youtube', 'YouTube'),
        ('twitter', 'Twitter / X'),
        ('other', 'Other'),
    ]

    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        help_text="Social media platform"
    )

    url = models.URLField(
        help_text="Full URL (e.g., https://instagram.com/nelylook)"
    )

    display_order = models.IntegerField(
        default=0,
        help_text="Order in footer (lower numbers appear first)"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Show this link in footer"
    )

    panels = [
        FieldPanel('platform'),
        FieldPanel('url'),
        FieldPanel('display_order'),
        FieldPanel('is_active'),
    ]

    def __str__(self):
        return f"{self.get_platform_display()} - {self.url}"

    class Meta:
        ordering = ['display_order', 'platform']
        verbose_name = "Social Media Link"
        verbose_name_plural = "Social Media Links"

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
# CONTENT BLOCKS FOR TEXT PAGES
# ============================================================

class TextBlock(StructBlock):
    """Simple text block with heading"""
    heading = CharBlock(required=False, max_length=200, help_text="Section heading")
    content = RichTextBlock(required=True, help_text="Text content with formatting")

    class Meta:
        icon = 'doc-full'
        label = 'Text Section'


class FAQBlock(StructBlock):
    """FAQ item with question and answer"""
    question = CharBlock(required=True, max_length=500, help_text="Question")
    answer = RichTextBlock(required=True, help_text="Answer")

    class Meta:
        icon = 'help'
        label = 'FAQ Item'


class ContactInfoBlock(StructBlock):
    """Contact information block"""
    title = CharBlock(required=True, max_length=100, help_text="Section title (e.g., 'Телефон', 'Email')")
    content = RichTextBlock(required=True, help_text="Contact details")
    icon = CharBlock(required=False, max_length=50, help_text="Icon name (optional)")

    class Meta:
        icon = 'mail'
        label = 'Contact Info'


# ============================================================
# STANDARD TEXT PAGES (About, FAQ, Contacts, etc.)
# ============================================================

class StandardPage(Page):
    """Generic text pages with rich content"""

    body = StreamField([
        ('heading', CharBlock(form_classname="title", icon="title", help_text="Section heading")),
        ('paragraph', RichTextBlock(icon="pilcrow", help_text="Paragraph text with formatting")),
        ('image', ImageChooserBlock(icon="image", help_text="Add an image")),
        ('text_block', TextBlock()),
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
# ABOUT US PAGE
# ============================================================

class AboutPage(Page):
    """О нас - About Us page"""

    max_count = 1  # Only one about page

    intro = RichTextField(
        blank=True,
        help_text="Introduction text"
    )

    body = StreamField([
        ('text_block', TextBlock()),
        ('image', ImageChooserBlock(icon="image", help_text="Add an image")),
    ], blank=True, use_json_field=True, help_text="Page content")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    api_fields = [
        APIField('intro'),
        APIField('body'),
    ]

    class Meta:
        verbose_name = "About Us Page"


# ============================================================
# FAQ PAGE
# ============================================================

class FAQPage(Page):
    """FAQ - Frequently Asked Questions"""

    max_count = 1  # Only one FAQ page

    intro = RichTextField(
        blank=True,
        help_text="Introduction text"
    )

    faqs = StreamField([
        ('faq_item', FAQBlock()),
    ], blank=True, use_json_field=True, help_text="Add FAQ items")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('faqs'),
    ]

    api_fields = [
        APIField('intro'),
        APIField('faqs'),
    ]

    class Meta:
        verbose_name = "FAQ Page"


# ============================================================
# CONTACT PAGE
# ============================================================

class ContactPage(Page):
    """Контакты - Contact information page"""

    max_count = 1  # Only one contact page

    intro = RichTextField(
        blank=True,
        help_text="Introduction text"
    )

    contact_info = StreamField([
        ('contact_block', ContactInfoBlock()),
    ], blank=True, use_json_field=True, help_text="Contact information blocks")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('contact_info'),
    ]

    api_fields = [
        APIField('intro'),
        APIField('contact_info'),
    ]

    class Meta:
        verbose_name = "Contact Page"


# ============================================================
# RETURNS & EXCHANGES PAGE
# ============================================================

class ReturnsPage(Page):
    """Возврат и Обмен - Returns and Exchanges policy"""

    max_count = 1  # Only one returns page

    body = StreamField([
        ('text_block', TextBlock()),
    ], blank=True, use_json_field=True, help_text="Returns and exchanges policy content")

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    api_fields = [
        APIField('body'),
    ]

    class Meta:
        verbose_name = "Returns & Exchanges Page"


# ============================================================
# PRIVACY POLICY PAGE
# ============================================================

class PrivacyPolicyPage(Page):
    """Политика конфиденциальности - Privacy Policy"""

    max_count = 1  # Only one privacy policy page

    body = StreamField([
        ('text_block', TextBlock()),
    ], blank=True, use_json_field=True, help_text="Privacy policy content")

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    api_fields = [
        APIField('body'),
    ]

    class Meta:
        verbose_name = "Privacy Policy Page"


# ============================================================
# TERMS OF SERVICE PAGE
# ============================================================

class TermsPage(Page):
    """Условия пользования - Terms of Service"""

    max_count = 1  # Only one terms page

    body = StreamField([
        ('text_block', TextBlock()),
    ], blank=True, use_json_field=True, help_text="Terms of service content")

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    api_fields = [
        APIField('body'),
    ]

    class Meta:
        verbose_name = "Terms of Service Page"


# ============================================================
# CONTACT INFORMATION (Snippet)
# ============================================================

@register_snippet
class ContactInformation(models.Model):
    """Contact information for contact page - managed in Wagtail"""

    # Singleton pattern - only one instance
    class Meta:
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"

    # Each section has one multi-line text field
    address = models.TextField(
        blank=True,
        verbose_name="Адрес",
        help_text="Введите адрес. Можно использовать несколько строк."
    )

    phones = models.TextField(
        blank=True,
        verbose_name="Телефоны",
        help_text="Введите номера телефонов. Можно использовать несколько строк."
    )

    emails = models.TextField(
        blank=True,
        verbose_name="Email",
        help_text="Введите email адреса. Можно использовать несколько строк."
    )

    working_hours = models.TextField(
        blank=True,
        verbose_name="Время работы",
        help_text="Введите часы работы. Можно использовать несколько строк."
    )

    # Social media URL fields
    whatsapp_url = models.URLField(
        blank=True,
        verbose_name="WhatsApp",
        help_text="Например: https://wa.me/996708200125"
    )

    telegram_url = models.URLField(
        blank=True,
        verbose_name="Telegram",
        help_text="Например: https://t.me/nelylook"
    )

    instagram_url = models.URLField(
        blank=True,
        verbose_name="Instagram",
        help_text="Например: https://instagram.com/nely.look"
    )

    panels = [
        MultiFieldPanel([
            FieldPanel('address'),
        ], heading="📍 Адрес"),

        MultiFieldPanel([
            FieldPanel('phones'),
        ], heading="📞 Телефоны"),

        MultiFieldPanel([
            FieldPanel('emails'),
        ], heading="📧 Email"),

        MultiFieldPanel([
            FieldPanel('working_hours'),
        ], heading="🕐 Время работы"),

        MultiFieldPanel([
            FieldPanel('whatsapp_url'),
            FieldPanel('telegram_url'),
            FieldPanel('instagram_url'),
        ], heading="💬 Социальные сети"),
    ]

    def __str__(self):
        return "Contact Information"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Load the singleton instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


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

from django.urls import path
from .views import UploadProductImage

urlpatterns = [
    path("upload/", UploadProductImage.as_view(), name="upload-product-image"),
]

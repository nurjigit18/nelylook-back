from django.db import models

class Item(models.Model):
    title = models.CharField(max_length=100, default='title')
    name = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)
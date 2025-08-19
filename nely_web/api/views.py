from django.shortcuts import render
from base.models import Item
from .serializers import ItemSerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated 

class ItemCreate(generics.ListCreateAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    
class ItemRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated]
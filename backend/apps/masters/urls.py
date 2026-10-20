from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.masters.serializers import RESOURCES
from apps.masters.views import master_view, ProspectViewSet
from apps.masters.models import Prospect
from apps.specifications.models import ProductModel
from apps.specifications.views import ProductModelViewSet, RevisionViewSet
from apps.imports.views import ImportViewSet

router=DefaultRouter()
for route,model in RESOURCES.items():
    router.register(route,master_view(model,ProspectViewSet) if model is Prospect else master_view(model),basename=route)
ModelView=master_view(ProductModel,ProductModelViewSet)
router.register('models',ModelView,basename='models')
router.register('model-revisions',RevisionViewSet,basename='model-revisions')
router.register('imports',ImportViewSet,basename='imports')
urlpatterns=[path('',include(router.urls))]

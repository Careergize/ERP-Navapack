from rest_framework.routers import SimpleRouter
from .views import CommercialViewSet
from .governance_views import GovernanceViewSet, DecisionSubmissionViewSet, DecisionRegistryViewSet
from .reference_views import CommercialReferenceViewSet

router = SimpleRouter()
router.register('documents', CommercialViewSet, basename='commercial-document')
router.register('policy-proposals', GovernanceViewSet, basename='commercial-policy-proposal')
router.register('decision-submissions', DecisionSubmissionViewSet, basename='commercial-decision-submission')
router.register('decision-registry', DecisionRegistryViewSet, basename='commercial-decision-registry')
router.register('references', CommercialReferenceViewSet, basename='commercial-reference')
urlpatterns = router.urls

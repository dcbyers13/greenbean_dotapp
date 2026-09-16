from django.http import JsonResponse
from django.views import View
from .services import CoopManifestService


class CoopManifestView(View):
    """Serve the decentralized cooperative manifest at /.well-known/coop-manifest.json."""

    def get(self, request):
        manifest_data = CoopManifestService.get_manifest()
        response = JsonResponse(manifest_data, json_dumps_params={"indent": 2})
        response["Access-Control-Allow-Origin"] = "*"
        return response

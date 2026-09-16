from django.shortcuts import render


def splash(request):
    """Render the Green Bean brand splash and mission presentation page."""
    context = {
        "brand_name": "Green Bean",
        "tagline": "Worker-owned, community-powered coffee.",
        "mission": (
            "Worker-owned, community-powered coffee. "
            "Sourced ethically, roasted locally, and rooted in our neighborhood."
        ),
        "established_year": 2017,
        "domain": "greenbean.app",
        "phase_status": "Phase 1: Operational",
    }
    return render(request, "core/splash.html", context)

from django.shortcuts import render

# Create your views here.
def handler404(request, exception):
    """404 xato sahifasi"""
    return render(request, '404.html', status=404)

def handler500(request):
    """500 xato sahifasi"""
    return render(request, '500.html', status=500)
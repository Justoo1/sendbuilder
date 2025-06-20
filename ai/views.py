from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import AIModel, AIConfiguration
from .forms import AIModelForm, AIConfigurationForm


@login_required
def aimodel_list(request):
    """List all AI models"""
    models = AIModel.objects.all().order_by('name')
    return render(request, 'ai/aimodel_list.html', {'models': models})


@login_required
def aimodel_create(request):
    """Create a new AI model"""
    if request.method == 'POST':
        form = AIModelForm(request.POST)
        if form.is_valid():
            model = form.save()
            messages.success(request, f'AI Model "{model.name}" created successfully!')
            return redirect('ai:aimodel_list')
    else:
        form = AIModelForm()
    
    return render(request, 'ai/aimodel_form.html', {'form': form})


@login_required
def aimodel_update(request, pk):
    """Update an existing AI model"""
    model = get_object_or_404(AIModel, pk=pk)
    
    if request.method == 'POST':
        form = AIModelForm(request.POST, instance=model)
        if form.is_valid():
            model = form.save()
            messages.success(request, f'AI Model "{model.name}" updated successfully!')
            return redirect('ai:aimodel_list')
    else:
        form = AIModelForm(instance=model)
    
    return render(request, 'ai/aimodel_form.html', {'form': form})


@login_required
def aimodel_delete(request, pk):
    """Delete an AI model"""
    model = get_object_or_404(AIModel, pk=pk)
    model_name = model.name
    model.delete()
    messages.success(request, f'AI Model "{model_name}" deleted successfully!')
    return redirect('ai:aimodel_list')


@login_required
def ai_configuration(request):
    """AI configuration settings"""
    try:
        config = AIConfiguration.objects.first()
        if not config:
            config = AIConfiguration.objects.create()
    except AIConfiguration.DoesNotExist:
        config = AIConfiguration.objects.create()
    
    if request.method == 'POST':
        form = AIConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'AI Configuration updated successfully!')
            return redirect('ai:ai_configuration')
    else:
        form = AIConfigurationForm(instance=config)
    
    return render(request, 'ai/aiconfig_form.html', {'form': form})
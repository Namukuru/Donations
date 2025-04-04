from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Need
from ..forms import NeedForm

@login_required
def need_list(request):
    if not hasattr(request.user, 'recipient'):
        messages.error(request, "Only recipients can view needs")
        return redirect('home')
    
    # Retrieve needs for the logged-in user
    needs = Need.objects.filter(recipient=request.user.recipient).order_by('-priority', 'is_fulfilled', '-date_logged')

    # Calculate fulfillment percentage for each need
    for need in needs:
        if need.quantity_needed > 0:  # Avoid division by zero
            need.fulfillment_percentage = int((need.quantity_received / need.quantity_needed) * 100)
        else:
            need.fulfillment_percentage = 0

    # Calculate the total number of needs, fulfilled needs, and urgent needs
    total_needs = needs.count()
    fulfilled_needs = needs.filter(is_fulfilled=True).count()
    urgent_needs = needs.filter(priority=4, is_fulfilled=False).count()

    # Check if there are no needs and show a message
    if total_needs == 0:
        messages.info(request, "You currently have no needs recorded.")

    context = {
        'needs': needs,  # Directly use the list of needs
        'total_needs': total_needs,
        'fulfilled_needs': fulfilled_needs,
        'urgent_needs': urgent_needs,
    }

    return render(request, 'need_list.html', context)



@login_required
def need_create(request):
    if not hasattr(request.user, 'recipient'):
        messages.error(request, "Only recipients can create needs")
        return redirect('home')
    
    if request.method == 'POST':
        form = NeedForm(request.POST)
        if form.is_valid():
            need = form.save(commit=False)
            need.recipient = request.user.recipient
            need.save()
            messages.success(request, "Need successfully recorded!")
            return redirect('need_list')
    else:
        form = NeedForm()
    
    context = {'form': form, 'title': "Record New Need", 'submit_text': "Create Need"}
    return render(request, 'need_form.html', context)

@login_required
def need_update(request, pk):
    if not hasattr(request.user, 'recipient'):
        messages.error(request, "Only recipients can edit needs")
        return redirect('home')
    
    need = get_object_or_404(Need, pk=pk, recipient=request.user.recipient)
    if request.method == 'POST':
        form = NeedForm(request.POST, instance=need)
        if form.is_valid():
            form.save()
            messages.success(request, "Need successfully updated!")
            return redirect('need_list')
    else:
        form = NeedForm(instance=need)
    
    context = {'form': form, 'title': "Update Need", 'submit_text': "Update Need"}
    return render(request, 'need_form.html', context)

@login_required
def need_delete(request, pk):
    if not hasattr(request.user, 'recipient'):
        messages.error(request, "Only recipients can delete needs")
        return redirect('home')
    
    need = get_object_or_404(Need, pk=pk, recipient=request.user.recipient)
    if request.method == 'POST':
        need.delete()
        messages.success(request, "Need successfully deleted")
        return redirect('need_list')
    
    return render(request, 'need_delete.html', {'need': need})

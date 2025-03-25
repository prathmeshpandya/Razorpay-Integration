from django.shortcuts import render, redirect
from .forms import CoffeePaymentForm
import razorpay
from .models import HotCoffee
from django.http import HttpResponseBadRequest

# Razorpay API Credentials
RAZORPAY_KEY_ID = "rzp_test_mMdWScRTlByYZi"
RAZORPAY_KEY_SECRET = "j1SZgqBn2IwiypREDtUavlwn"

def coffee_payment(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        amount = request.POST.get('amount')

        # Validate amount input
        try:
            amount = int(amount) * 100  # Convert to paise
        except ValueError:
            return HttpResponseBadRequest("Invalid amount entered.")

        # Create Razorpay client
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

        # Create order
        response_payment = client.order.create(
            dict(amount=amount, currency='INR', payment_capture="1")
        )

        order_id = response_payment.get('id')
        order_status = response_payment.get('status')

        if order_status == 'created':
            # Save order details in DB
            hotcoffee = HotCoffee(
                name=name,
                amount=amount,
                order_id=order_id,
            )
            hotcoffee.save()

            # Include callback URL for redirection
            response_payment['name'] = name
            response_payment['callback_url'] = "http://127.0.0.1:8000/payment_status/"

            form = CoffeePaymentForm(request.POST or None)
            return render(request, 'coffee_payment.html', {'form': form, 'payment': response_payment})

    form = CoffeePaymentForm()
    return render(request, 'coffee_payment.html', {'form': form})


def payment_status(request):
    if request.method == "POST":
        response = request.POST

        # Ensure required fields exist
        if not all(k in response for k in ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature"]):
            return render(request, 'payment_status.html', {'status': False, 'error': "Missing Razorpay response parameters"})

        params_dict = {
            'razorpay_order_id': response.get('razorpay_order_id'),
            'razorpay_payment_id': response.get('razorpay_payment_id'),
            'razorpay_signature': response.get('razorpay_signature')
        }

        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

        try:
            # Verify payment signature
            status = client.utility.verify_payment_signature(params_dict)

            hotcoffee = HotCoffee.objects.get(order_id=response.get('razorpay_order_id'))
            hotcoffee.razorpay_payment_id = response.get('razorpay_payment_id')
            hotcoffee.paid = True
            hotcoffee.save()

            return render(request, 'payment_status.html', {'status': True})
        except Exception as e:
            print(f"Payment verification error: {e}")  # Debug log
            return render(request, 'payment_status.html', {'status': False, 'error': str(e)})

    return render(request, 'payment_status.html', {'status': False})

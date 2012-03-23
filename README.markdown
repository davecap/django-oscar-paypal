## django-oscar-paypal

PayPal Payment Module for django-oscar.
Adapted from django-paypal: https://github.com/johnboxall/django-paypal.git

### Requirements

* django-paypal
* django-oscar

### How to use

Install django-paypal and add `paypal.standard.ipn` to your `INSTALLED_APPS`
*TODO: Incorporate IPN into this package?*

### Settings

    PAYPAL_DEBUG = False
    PAYPAL_TEST = False
    PAYPAL_RECEIVER_EMAIL = '<EMAIL>'
    PAYPAL_WPP_CURRENCY = "CAD"

    PAYPAL_WPP_USER = "<WPP USER>"
    PAYPAL_WPP_PASSWORD = "<WPP PASS>"
    PAYPAL_WPP_SIGNATURE = "<WPP SIGNATURE>"

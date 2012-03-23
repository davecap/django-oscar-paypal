from string import split as L
import urllib
from decimal import Decimal

from django.db import models
from django.utils.http import urlencode
from django.contrib.auth.models import User

class PayPalNVP(models.Model):
    """Record of a NVP interaction with PayPal."""
    TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # 2009-02-03T17:47:41Z
    RESTRICTED_FIELDS = L("expdate cvv2 acct")
    ADMIN_FIELDS = L("id user flag flag_code flag_info request response created_at updated_at")
    DATETIME_FIELDS = L("timestamp")
    DECIMAL_FIELDS = L("amt shippingamt taxamt feeamt settleamt")
    
    BILLING_ADDRESS_FIELDS = L("firstname lastname street street2 city state countrycode zip")
    SHIPPING_ADDRESS_FIELDS = L("shiptoname shiptostreet shiptostreet2 shiptocity shiptostate shiptocountry shiptozip shiptophonenum")
    PAYMENT_FIELDS = L("amt shippingamt taxamt feeamt settleamt paymentstatus pendingreason reasoncode")
    
    # Common response fields
    method = models.CharField(max_length=64, blank=True)
    ack = models.CharField(max_length=32, blank=True)    
    correlationid = models.CharField(max_length=32, blank=True) # 25b380cda7a21
    timestamp = models.DateTimeField(blank=True, null=True)
    
    # Standard payments fields
    token = models.CharField(max_length=64, blank=True)
    payerid = models.CharField(max_length=64, blank=True)
    invnum = models.CharField(max_length=255, blank=True)
    custom = models.CharField(max_length=255, blank=True)
    transactionid = models.CharField(max_length=255, blank=True)
    email = models.CharField(max_length=100, blank=True)
    paymentstatus = models.CharField(max_length=30, blank=True)
    
    # Admin fields
    user = models.ForeignKey(User, blank=True, null=True)
    flag = models.BooleanField(default=False, blank=True)
    flag_code = models.CharField(max_length=32, blank=True)
    flag_info = models.TextField(blank=True)    
    ipaddress = models.IPAddressField(blank=True)
    request = models.TextField(blank=True)
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    class Meta:
        db_table = "paypal_nvp"
        verbose_name = "PayPal NVP"
    
    def init(self, paypal_request, paypal_response):
        """Initialize a PayPalNVP instance from a HttpRequest."""
        # No storing credit card info.
        request_data = dict((k,v) for k, v in paypal_request.iteritems() 
                            if k not in self.RESTRICTED_FIELDS)
        self.request = urlencode(request_data)
        self.response = urlencode(paypal_response)

        ack = paypal_response.get('ack', False)
        if ack != "Success":
            if ack == "SuccessWithWarning":
                self.flag_info = paypal_response.get('l_longmessage0', '')
            else:
                self.set_flag(paypal_response.get('l_longmessage0', ''), 
                            paypal_response.get('l_errorcode0', ''))

    def set_flag(self, info, code=None):
        """Flag this instance for investigation."""
        self.flag = True
        self.flag_info += info
        if code is not None:
            self.flag_code = code
            
    def get_request_params(self, params):
        data = {}      
        for kv in self.request.split('&'):
            key, value = kv.split("=")
            if key.lower() in params:
                v = urllib.unquote(value)
                if key.lower() in self.DECIMAL_FIELDS:
                    data[key.lower()] = Decimal(v)
                else:
                    data[key.lower()] = v
        return data

    def get_response_params(self, params):
        data = {}      
        for kv in self.response.split('&'):
            key, value = kv.split("=")
            if key.lower() in params:
                v = urllib.unquote(value)
                if key.lower() in self.DECIMAL_FIELDS:
                    data[key.lower()] = Decimal(v)
                else:
                    data[key.lower()] = v
        return data

    # helper functions
    
    def get_payment_details(self):
        return self.get_response_params(self.PAYMENT_FIELDS)
        
    def get_shipping_address(self):
        return self.get_response_params(self.SHIPPING_ADDRESS_FIELDS)


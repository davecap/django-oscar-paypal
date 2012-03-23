import datetime
import time
import urllib
import urllib2
import pprint
from string import split as L

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import MergeDict
from django.utils.http import urlencode

import logging
logger = logging.getLogger('apps.payment.paypal.utils')

from oscar.core.loading import import_module
import_module('payment.exceptions', ['GatewayError'], locals())

from apps.payment.paypal.signals import *
from apps.payment.paypal.models import PayPalNVP
from apps.payment.paypal.exceptions import PayPalFailure, PayPalError

BASE_PARAMS = dict(USER=settings.PAYPAL_WPP_USER,
                    PWD=settings.PAYPAL_WPP_PASSWORD,
                    SIGNATURE=settings.PAYPAL_WPP_SIGNATURE,
                    VERSION=84.0)
ENDPOINT = "https://api-3t.paypal.com/nvp"
SANDBOX_ENDPOINT = "https://api-3t.sandbox.paypal.com/nvp"
EXPRESS_ENDPOINT = "https://www.paypal.com/webscr?cmd=_express-checkout&%s"
SANDBOX_EXPRESS_ENDPOINT = "https://www.sandbox.paypal.com/webscr?cmd=_express-checkout&%s"
CURRENCY = settings.PAYPAL_WPP_CURRENCY

if settings.PAYPAL_TEST:
    EXPRESS_ENDPOINT = SANDBOX_EXPRESS_ENDPOINT
    ENDPOINT = SANDBOX_ENDPOINT

from django.forms.models import fields_for_model
NVP_FIELDS = fields_for_model(PayPalNVP).keys()

class Gateway(object):
    """
    Wrapper class for the PayPal Website Payments Pro.
    
    Website Payments Pro Integration Guide:
    https://cms.paypal.com/cms_content/US/en_US/files/developer/PP_WPP_IntegrationGuide.pdf

    Name-Value Pair API Developer Guide and Reference:
    https://cms.paypal.com/cms_content/US/en_US/files/developer/PP_NVPAPI_DeveloperGuide.pdf
    """
    
    def __init__(self, params=BASE_PARAMS, ipaddress=None, user=None):
        """Required - USER / PWD / SIGNATURE / VERSION"""
        self.endpoint = ENDPOINT
        self.signature_values = params
        self.signature = urlencode(self.signature_values) + "&"
        self.ipaddress = ipaddress
        self.user = user

    def doDirectPayment(self, params):
        """Call PayPal DoDirectPayment method."""
        defaults = {"method": "DoDirectPayment", 
                    "paymentaction": "Sale",
                    "returnfmfdetails": 0,
                    "currencycode": CURRENCY,
                    "ipaddress": self.ipaddress}
        required = L("creditcardtype acct expdate cvv2 ipaddress firstname lastname street city state countrycode zip amt")
        nvp_obj = self._fetch(params, required, defaults)
        if nvp_obj.flag:
            raise PayPalFailure(nvp_obj.flag_info)
        # @@@ Could check cvv2match / avscode are both 'X' or '0'
        # qd = django.http.QueryDict(nvp_obj.response)
        # if qd.get('cvv2match') not in ['X', '0']:
        #   nvp_obj.set_flag("Invalid cvv2match: %s" % qd.get('cvv2match')
        # if qd.get('avscode') not in ['X', '0']:
        #   nvp_obj.set_flag("Invalid avscode: %s" % qd.get('avscode')
        return nvp_obj

    def setExpressCheckout(self, params):
        """
        Initiates an Express Checkout transaction.
        Optionally, the SetExpressCheckout API operation can set up billing agreements for
        reference transactions and recurring payments.
        Returns a NVP instance - check for token and payerid to continue!
        """
        if self._is_recurring(params):
            params = self._recurring_setExpressCheckout_adapter(params)

        defaults = {"method": "SetExpressCheckout", 
                    "noshipping": 1,
                    "currencycode": CURRENCY}
        required = L("returnurl cancelurl amt")
        nvp_obj = self._fetch(params, required, defaults)
        if nvp_obj.flag:
            raise PayPalFailure(nvp_obj.flag_info)
        return nvp_obj

    def doExpressCheckoutPayment(self, params):
        """
        Check the dude out:
        """
        defaults = {"method": "DoExpressCheckoutPayment",
                    "paymentaction": "Sale",
                    "currencycode": CURRENCY}
        required = L("amt token payerid")
        nvp_obj = self._fetch(params, required, defaults)
        if nvp_obj.flag:
            raise PayPalFailure(nvp_obj.flag_info)
        return nvp_obj
        
    def createRecurringPaymentsProfile(self, params, direct=False):
        """
        Set direct to True to indicate that this is being called as a directPayment.
        Returns True PayPal successfully creates the profile otherwise False.
        """
        defaults = {"method": "CreateRecurringPaymentsProfile"}
        required = L("profilestartdate billingperiod billingfrequency amt")

        # Direct payments require CC data
        if direct:
            required + L("creditcardtype acct expdate firstname lastname")
        else:
            required + L("token payerid")

        nvp_obj = self._fetch(params, required, defaults)
        
        # Flag if profile_type != ActiveProfile
        if nvp_obj.flag:
            raise PayPalFailure(nvp_obj.flag_info)
        paymentfile_created.send(params)
        return nvp_obj

    def getExpressCheckoutDetails(self, params):
        defaults = {"method": "GetExpressCheckoutDetails"}
        required = L("token")
        nvp_obj = self._fetch(params, required, defaults)
        if nvp_obj.flag:
            raise PayPalFailure(nvp_obj.flag_info)
        return nvp_obj

    def setCustomerBillingAgreement(self, params):
        raise DeprecationWarning

    def getTransactionDetails(self, params):
        defaults = {"method": "GetTransactionDetails"}
        required = L("transactionid")

        nvp_obj = self._fetch(params, required, defaults)
        if nvp_obj.flag:
            raise PayPalFailure(nvp_obj.flag_info)
        return nvp_obj

    def massPay(self, params):
        raise NotImplementedError

    def getRecurringPaymentsProfileDetails(self, params):
        raise NotImplementedError

    def updateRecurringPaymentsProfile(self, params):
        defaults = {"method": "UpdateRecurringPaymentsProfile"}
        required = L("profileid")

        nvp_obj = self._fetch(params, required, defaults)
        if nvp_obj.flag:
            raise PayPalFailure(nvp_obj.flag_info)
        return nvp_obj
    
    def billOutstandingAmount(self, params):
        raise NotImplementedError
        
    def manangeRecurringPaymentsProfileStatus(self, params, fail_silently=False):
        """
        Requires `profileid` and `action` params.
        Action must be either "Cancel", "Suspend", or "Reactivate".
        """
        defaults = {"method": "ManageRecurringPaymentsProfileStatus"}
        required = L("profileid action")

        nvp_obj = self._fetch(params, required, defaults)

        # TODO: This fail silently check should be using the error code, but its not easy to access
        if not nvp_obj.flag or (fail_silently and nvp_obj.flag_info == 'Invalid profile status for cancel action; profile should be active or suspended'):
            if params['action'] == 'Cancel':
                recurring_cancel.send(sender=nvp_obj)
            elif params['action'] == 'Suspend':
                recurring_suspend.send(sender=nvp_obj)
            elif params['action'] == 'Reactivate':
                recurring_reactivate.send(sender=nvp_obj)
        else:
            raise PayPalFailure(nvp_obj.flag_info)
        return nvp_obj
        
    def refundTransaction(self, params):
        raise NotImplementedError

    def _is_recurring(self, params):
        """Returns True if the item passed is a recurring transaction."""
        return 'billingfrequency' in params

    def _recurring_setExpressCheckout_adapter(self, params):
        """
        The recurring payment interface to SEC is different than the recurring payment
        interface to ECP. This adapts a normal call to look like a SEC call.
        """
        params['l_billingtype0'] = "RecurringPayments"
        params['l_billingagreementdescription0'] = params['desc']

        REMOVE = L("billingfrequency billingperiod profilestartdate desc")
        for k in params.keys():
            if k in REMOVE:
                del params[k]
                
        return params

    def _fetch(self, params, required, defaults):
        """Make the NVP request and store the response."""
        defaults.update(params)
        pp_params = self._check_and_update_params(required, defaults)
        pp_string = self.signature + urlencode(pp_params)
        response = self._request(pp_string)
        response_params = self._parse_response(response)
        
        if getattr(settings, 'PAYPAL_DEBUG', settings.DEBUG):
            print 'PayPal Request:'
            pprint.pprint(defaults)
            print '\nPayPal Response:'
            pprint.pprint(response_params)
        
        # Gather all NVP parameters to pass to a new instance.
        nvp_params = {}
        for k, v in MergeDict(defaults, response_params).items():
            if k in NVP_FIELDS:
                nvp_params[str(k)] = v

        # PayPal timestamp has to be formatted.
        if 'timestamp' in nvp_params:
            nvp_params['timestamp'] = self._from_paypal_time(nvp_params['timestamp'])
        # double check that ipaddress is saved
        if not 'ipaddress' in nvp_params:
            nvp_params['ipaddress'] = self.ipaddress

        nvp_obj = PayPalNVP(**nvp_params)
        if self.user.is_authenticated():
            nvp_obj.user = self.user
        nvp_obj.init(params, response_params)
        nvp_obj.save()
        return nvp_obj
        
    def _request(self, data):
        """Moved out to make testing easier."""
        return urllib2.urlopen(self.endpoint, data).read()

    def _check_and_update_params(self, required, params):
        """
        Ensure all required parameters were passed to the API call and format
        them correctly.
        """
        for r in required:
            if r not in params:
                raise PayPalError("Missing required param: %s" % r)    

        # Upper case all the parameters for PayPal.
        return (dict((k.upper(), v) for k, v in params.iteritems()))

    def _parse_response(self, response):
        """Turn the PayPal response into a dict"""
        response_tokens = {}
        for kv in response.split('&'):
            key, value = kv.split("=")
            response_tokens[key.lower()] = urllib.unquote(value)
        return response_tokens

    def _to_paypal_time(self, time_obj=None):
        """Returns a time suitable for PayPal time fields."""
        if time_obj is None:
            time_obj = time.gmtime()
        return time.strftime(PayPalNVP.TIMESTAMP_FORMAT, time_obj)

    def _from_paypal_time(self, t):
        """Convert a PayPal time string to a DateTime."""
        return datetime.datetime(*(time.strptime(t, PayPalNVP.TIMESTAMP_FORMAT)[:6]))



class Facade(object):
    """
    Responsible for dealing with oscar objects
    """
    
    def __init__(self, request):
        self.gateway = Gateway(ipaddress=request.META.get('REMOTE_ADDR', '').split(':')[0],
                                user=request.user)
    
    #
    # PayPal Express Checkout
    #
    
    def setExpressCheckout(self, basket_id, order_number, amt, email, returnurl, cancelurl):
        """
        First step of ExpressCheckout. Calls setExpressCheckout.
        Returns the URL for redirecting the user.
        https://cms.paypal.com/us/cgi-bin/?cmd=_render-content&content_ID=developer/e_howto_api_ECCustomizing
        """
        params = {  'returnurl': returnurl,
                    'cancelurl': cancelurl,
                    'invnum': str(order_number),
                    'custom': str(basket_id),
                    'amt': str(amt),
                    'email': email,
                    'noshipping': '1',
                    'addroverride': '0',
                    'reqconfirmshipping': '0'}
        
        try:
            self.nvp_obj = self.gateway.setExpressCheckout(params)
        except PayPalFailure as e:
            logger.error("PayPal Failure: %s" % e)
            raise GatewayError(_("There was a problem connecting to PayPal, please try again later."))
        else:
            pp_params = dict(token=self.nvp_obj.token, AMT=amt, 
                             RETURNURL=returnurl, CANCELURL=cancelurl)
            # stay on PayPal
            pp_params['useraction'] = 'commit'
            return EXPRESS_ENDPOINT % urlencode(pp_params)
    
    def getExpressCheckoutDetails(self, token):
        """ Second step of ExpressCheckout """
        
        params = {'token': token}
        try:
            self.nvp_obj = self.gateway.getExpressCheckoutDetails(params)
        except PayPalFailure as e:
            raise GatewayError(str(e))
        else:
            return self.nvp_obj

    def doExpressCheckoutPayment(self, token, payerid, basket_id, order_number, amount, notifyurl):
        """ Third step of ExpressCheckout """
        
        params = {'token': token,
                    'payerid': payerid,
                    'custom': str(basket_id),
                    'invnum': str(order_number),
                    'amt': str(amount),
                    'notifyurl': notifyurl
                    # 'taxamt': str(taxamt),
                    # 'shippingamt': str(shippingamt)
                    }
        
        try:
            self.nvp_obj = self.gateway.doExpressCheckoutPayment(params)
        except PayPalFailure as e:
            raise GatewayError(str(e))
        else:
            # verify the tokens
            if self.nvp_obj.token != token:
                logger.error("""token mismatch on doExpressCheckoutPayment response! 
                                    Expected: %s Received: %s""" % 
                                    (token, self.nvp_obj.token))
                raise GatewayError(_("There was a problem connecting to PayPal, please try again later."))
            return self.nvp_obj
    
    #
    # Website Payments Pro
    #
    
    def doDirectPayment(self, basket_id, order_number, amount,
                        creditcard, billing_address, shipping_address):

        params = {'custom': str(basket_id),
                    'invnum': str(order_number),
                    'amt': str(amount),
                    'acct': creditcard.number,
                    'expdate': creditcard.expdate.strftime("%m%Y"),
                    'cvv2': creditcard.cvv2,
                    'creditcardtype': creditcard.get_type(),
                    # billing address
                    'firstname': billing_address.first_name,
                    'lastname': billing_address.last_name,
                    'street': billing_address.line1,
                    'street2': billing_address.line2,
                    'city': billing_address.city,
                    'state': billing_address.state,
                    'countrycode': billing_address.country.iso_3166_1_a2,
                    'zip': billing_address.postcode,
                    # shipping address
                    'shiptoname': shipping_address.salutation(),
                    'shiptostreet': shipping_address.line1,
                    'shiptostreet2': shipping_address.line2,
                    'shiptocity': shipping_address.city,
                    'shiptostate': shipping_address.state,
                    'shiptocountry': shipping_address.country.iso_3166_1_a2,
                    'shiptozip': shipping_address.postcode,
                    'shiptophonenum': shipping_address.phone_number,
                }
        
        try:
            self.nvp_obj = self.gateway.doDirectPayment(params)
        except PayPalFailure as e:
            raise GatewayError(str(e))
        else:
            return self.nvp_obj.transactionid


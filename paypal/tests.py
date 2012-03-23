#!/usr/bin/python
# -*- coding: utf-8 -*-
from decimal import Decimal as D
import datetime

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.forms import ValidationError
from django.http import QueryDict
from django.test import TestCase
from django.test.client import Client

from apps.payment.paypal.exceptions import PayPalFailure
from apps.payment.paypal.utils import Gateway, Facade
from apps.payment.paypal.models import PayPalNVP

# class PayPalOrderTransactionTests(TestCase):
#     
#     def test_cc_numbers_are_not_saved(self):
#         
#         request_xml = """<?xml version="1.0" encoding="UTF-8" ?>
# <Request>
#     <Authentication>
#         <client>99000001</client>
#         <password>boomboom</password>
#     </Authentication>
#     <Transaction>
#     <CardTxn>
#         <Card>
#             <pan>1000011100000004</pan>
#             <expirydate>04/06</expirydate>
#             <startdate>01/04</startdate>
#         </Card>
#         <method>auth</method>
#     </CardTxn>
#     <TxnDetails>
#         <merchantreference>1000001</merchantreference>
#         <amount currency="GBP">95.99</amount>
#     </TxnDetails>
#     </Transaction>
# </Request>"""
# 
#         response_xml = """<?xml version="1.0" encoding="UTF-8" ?>
# <Response>
#     <CardTxn>
#         <authcode>060642</authcode>
#         <card_scheme>Switch</card_scheme>
#         <country>United Kingdom</country>
#         <issuer>HSBC</issuer>
#     </CardTxn>
#     <datacash_reference>3000000088888888</datacash_reference>
#     <merchantreference>1000001</merchantreference>
#     <mode>LIVE</mode>
#     <reason>ACCEPTED</reason>
#     <status>1</status>
#     <time>1071567305</time>
# </Response>"""
#         
#         txn = PayPalOrderTransaction.objects.create(order_number='1000',
#                                               method='auth',
#                                               datacash_ref='3000000088888888',
#                                               merchant_ref='1000001',
#                                               amount=D('95.99'),
#                                               status=1,
#                                               reason='ACCEPTED',
#                                               request_xml=request_xml,
#                                               response_xml=response_xml)
#         doc = parseString(txn.request_xml)
#         element = doc.getElementsByTagName('pan')[0]
#         self.assertEqual('XXXXXXXXXXXX0004', element.firstChild.data)
#         
#         
# class IntegrationTests(TestCase):
#     
#     def _test_for_smoke(self):
#         gateway = Gateway(settings.DATACASH_CLIENT, 
#                           settings.DATACASH_PASSWORD,
#                           host=settings.DATACASH_HOST)
#         response = gateway.auth(card_number='1000011000000005',
#                                 expiry_date='01/13',
#                                 amount=D('50.00'),
#                                 currency='GBP',
#                                 merchant_reference='123456_%s' % datetime.datetime.now().microsecond)
#         print response
#         
#     def _test_adapter(self):
#         bankcard = Bankcard(card_number='1000011000000005', expiry_date='01/13')
#     
#         dc_facade = Facade()
#         reference = dc_facade.debit('102910', D('23.00'), bankcard)
#         print reference
#         
#         OrderTransaction.objects.get(order_number='102910')
#         



class DummyPayPalWPP(Gateway):
    pass
#     """Dummy class for testing PayPalWPP."""
#     responses = {
#         # @@@ Need some reals data here.
#         "DoDirectPayment": """ack=Success&timestamp=2009-03-12T23%3A52%3A33Z&l_severitycode0=Error&l_shortmessage0=Security+error&l_longmessage0=Security+header+is+not+valid&version=54.0&build=854529&l_errorcode0=&correlationid=""",
#     }
# 
#     def _request(self, data):
#         return self.responses["DoDirectPayment"]


# class PayPalWPPTest(TestCase):
#     def setUp(self):
#     
#         # Avoding blasting real requests at PayPal.
#         self.old_debug = settings.DEBUG
#         settings.DEBUG = True
#             
#         self.item = {
#             'amt': '9.95',
#             'inv': 'inv',
#             'custom': 'custom',
#             'next': 'http://www.example.com/next/',
#             'returnurl': 'http://www.example.com/pay/',
#             'cancelurl': 'http://www.example.com/cancel/'
#         }                    
#         self.wpp = DummyPayPalWPP(REQUEST)
#         
#     def tearDown(self):
#         settings.DEBUG = self.old_debug
# 
#     def test_doDirectPayment_missing_params(self):
#         data = {'firstname': 'Chewbacca'}
#         self.assertRaises(PayPalError, self.wpp.doDirectPayment, data)
# 
#     def test_doDirectPayment_valid(self):
#         data = {
#             'firstname': 'Brave',
#             'lastname': 'Star',
#             'street': '1 Main St',
#             'city': u'San Jos\xe9',
#             'state': 'CA',
#             'countrycode': 'US',
#             'zip': '95131',
#             'expdate': '012019',
#             'cvv2': '037',
#             'acct': '4797503429879309',
#             'creditcardtype': 'visa',
#             'ipaddress': '10.0.1.199',}
#         data.update(self.item)
#         self.assertTrue(self.wpp.doDirectPayment(data))
#     
#     def test_doDirectPayment_invalid(self):
#         data = {
#             'firstname': 'Epic',
#             'lastname': 'Fail',
#             'street': '100 Georgia St',
#             'city': 'Vancouver',
#             'state': 'BC',
#             'countrycode': 'CA',
#             'zip': 'V6V 1V1',
#             'expdate': '012019',
#             'cvv2': '999',
#             'acct': '1234567890',
#             'creditcardtype': 'visa',
#             'ipaddress': '10.0.1.199',}
#         data.update(self.item)
#         self.assertRaises(PayPalFailure, self.wpp.doDirectPayment, data)
# 
#     def test_setExpressCheckout(self):
#         # We'll have to stub out tests for doExpressCheckoutPayment and friends
#         # because they're behind paypal's doors.
#         nvp_obj = self.wpp.setExpressCheckout(self.item)
#         self.assertTrue(nvp_obj.ack == "Success")


### DoExpressCheckoutPayment
# PayPal Request:
# {'amt': '10.00',
#  'cancelurl': u'http://xxx.xxx.xxx.xxx/deploy/480/upgrade/?upgrade=cname',
#  'custom': u'website_id=480&cname=1',
#  'inv': u'website-480-cname',
#  'method': 'DoExpressCheckoutPayment',
#  'next': u'http://xxx.xxx.xxx.xxx/deploy/480/upgrade/?upgrade=cname',
#  'payerid': u'BN5JZ2V7MLEV4',
#  'paymentaction': 'Sale',
#  'returnurl': u'http://xxx.xxx.xxx.xxx/deploy/480/upgrade/?upgrade=cname',
#  'token': u'EC-6HW17184NE0084127'}
# 
# PayPal Response:
# {'ack': 'Success',
#  'amt': '10.00',
#  'build': '848077',
#  'correlationid': '375f4773c3d34',
#  'currencycode': 'USD',
#  'feeamt': '0.59',
#  'ordertime': '2009-03-04T20:56:08Z',
#  'paymentstatus': 'Completed',
#  'paymenttype': 'instant',
#  'pendingreason': 'None',
#  'reasoncode': 'None',
#  'taxamt': '0.00',
#  'timestamp': '2009-03-04T20:56:09Z',
#  'token': 'EC-6HW17184NE0084127',
#  'transactionid': '3TG42202A7335864V',
#  'transactiontype': 'expresscheckout',
#  'version': '54.0'}
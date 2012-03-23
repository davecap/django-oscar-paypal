#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django import forms

class HiddenConfirmForm(forms.Form):
    """Hidden form used by ExpressPay flow to keep track of payer information."""
    token = forms.CharField(max_length=255, widget=forms.HiddenInput())
    PayerID = forms.CharField(max_length=255, widget=forms.HiddenInput())
from pickletools import OpcodeInfo

# -*- coding: utf-8 -*-
from email.policy import default
import logging
from select import select
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


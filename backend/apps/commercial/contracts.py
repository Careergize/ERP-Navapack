"""Development calculation contract v1. No tax authority, FX or implicit conversion."""
import re
from decimal import Decimal, localcontext, ROUND_HALF_UP, ROUND_HALF_EVEN
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from apps.core.audit import sanitize


def clean_reason(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError({'reason': 'A change reason is required.'})
    result = sanitize(value.strip())
    if len(result) > 500:
        raise ValidationError({'reason': 'Use at most 500 characters after privacy redaction.'})
    return result


class Strict(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise ValidationError({'non_field_errors': ['Use only declared contract fields.']})
        return super().to_internal_value(data)


class ExactDecimal(serializers.CharField):
    def to_internal_value(self, value):
        if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?', value):
            raise ValidationError('Use a nonnegative decimal string: at most 12 integer and 6 fractional digits.')
        return value


class MaterialInput(Strict):
    material = serializers.UUIDField()
    unit = serializers.UUIDField()
    price_unit = serializers.UUIDField()
    currency = serializers.ChoiceField(choices=['UGX', 'USD'])
    quantity = ExactDecimal()
    price = ExactDecimal()


class ProcessInput(Strict):
    description = serializers.CharField(max_length=240)
    currency = serializers.ChoiceField(choices=['UGX', 'USD'])
    amount = ExactDecimal()


class CostInput(Strict):
    materials = MaterialInput(many=True, allow_empty=False, max_length=100)
    processes = ProcessInput(many=True, max_length=100)
    waste_percent = ExactDecimal()
    rejection_percent = ExactDecimal()
    assumption_evidence = serializers.CharField(max_length=500)
    markup_percent = ExactDecimal()


class LineInput(Strict):
    variant = serializers.UUIDField()
    unit = serializers.UUIDField()
    quantity = ExactDecimal()
    unit_price = ExactDecimal()
    specifications = serializers.CharField(max_length=4000, allow_blank=True)
    customisation = serializers.CharField(max_length=4000, allow_blank=True)
    model_revision = serializers.UUIDField(required=False)
    costing_revision = serializers.UUIDField(required=False)
    costing = CostInput(required=False)
    stock_identity = serializers.UUIDField(required=False)
    requested_delivery = serializers.DateField(required=False)


class DocumentInput(Strict):
    currency = serializers.ChoiceField(choices=['UGX', 'USD'])
    money_places = serializers.ChoiceField(choices=[0, 2])
    rounding = serializers.ChoiceField(choices=['HALF_UP', 'HALF_EVEN'])
    customer = serializers.UUIDField(required=False)
    prospect = serializers.UUIDField(required=False)
    classification = serializers.ChoiceField(choices=['B2B', 'B2C'], required=False)
    marketing_person = serializers.UUIDField(required=False)
    quotation_revision = serializers.UUIDField(required=False)
    requested_delivery = serializers.DateField(required=False)
    validity_date = serializers.DateField(required=False)
    terms = serializers.CharField(max_length=4000, allow_blank=True)
    discount = ExactDecimal()
    lines = LineInput(many=True, allow_empty=False, max_length=100)

    def validate(self, data):
        if data.get('customer') and data.get('prospect'):
            raise ValidationError('Select at most one existing customer or prospect.')
        return data


def calculate_cost(cost, output_quantity, currency, quantize):
    """Entered material consumption is gross input; waste/rejection explain net output.

    v1 does not scale consumption by losses again or infer an output mass balance.
    """
    if any(m['currency'] != currency for m in cost['materials']) or any(p['currency'] != currency for p in cost['processes']):
        raise ValidationError('Mixed currency requires an approved FX policy; unavailable.')
    if any(m['unit'] != m['price_unit'] for m in cost['materials']):
        raise ValidationError('Material consumption and price units must match exactly.')
    if any(Decimal(cost[k]) >= 100 for k in ('waste_percent', 'rejection_percent')):
        raise ValidationError('Waste and rejection assumptions must each be below 100%.')
    if any(Decimal(m['quantity']) <= 0 for m in cost['materials']):
        raise ValidationError('Material quantities must be positive.')
    raw = sum((Decimal(m['quantity']) * Decimal(m['price']) for m in cost['materials']), Decimal(0))
    process = sum((Decimal(p['amount']) for p in cost['processes']), Decimal(0))
    total = raw + process
    selling = total * (1 + Decimal(cost['markup_percent']) / 100)
    return {'material_cost': quantize(raw), 'process_cost': quantize(process),
            'estimated_production_cost': quantize(total), 'cost_per_output_unit': quantize(total / output_quantity),
            'suggested_net_selling': quantize(selling),
            'suggested_unit_price': quantize(selling / output_quantity),
            'gross_margin_percent': str(((selling - total) / selling * 100).quantize(Decimal('.000001'))) if selling else None,
            'loss_treatment': 'Entered gross consumption; no automatic yield scaling', 'actual_cost': None}


def estimate(data):
    with localcontext() as ctx:
        ctx.prec = 60
        ctx.rounding = {'HALF_UP': ROUND_HALF_UP, 'HALF_EVEN': ROUND_HALF_EVEN}[data['rounding']]
        quantum = Decimal(1).scaleb(-data['money_places'])
        def money(value):
            if abs(value) >= Decimal('1e30'):
                raise ValidationError('Estimate exceeds supported monetary range.')
            return str(value.quantize(quantum))
        lines = []
        for line in data['lines']:
            quantity = Decimal(line['quantity'])
            if quantity <= 0:
                raise ValidationError('Output and commercial quantities must be positive.')
            result = {'net_amount': money(quantity * Decimal(line['unit_price']))}
            if 'costing' in line:
                result['costing'] = calculate_cost(line['costing'], quantity, data['currency'], money)
                selling = quantity * Decimal(line['unit_price'])
                # Use unrounded cost inputs for margin, display money only at the
                # selected quantum; a document discount is not allocated to lines.
                cost = sum((Decimal(m['quantity']) * Decimal(m['price']) for m in line['costing']['materials']), Decimal(0)) + sum((Decimal(p['amount']) for p in line['costing']['processes']), Decimal(0))
                result['costing']['entered_selling_before_discount'] = money(selling)
                result['costing']['entered_gross_margin_percent_before_discount'] = str(((selling-cost)/selling*100).quantize(Decimal('.000001'))) if selling else None
            lines.append(result)
        subtotal = sum((Decimal(line['net_amount']) for line in lines), Decimal(0))
        discount = Decimal(data['discount'])
        if discount > subtotal or discount != Decimal(money(discount)):
            raise ValidationError('Discount exceeds subtotal or currency precision.')
        return {'contract': 'phase4a-v1', 'lines': lines, 'net_subtotal': money(subtotal),
                'net_estimate': money(subtotal - discount), 'vat': None, 'led': None,
                'payable_total': None, 'authoritative': False,
                'blocked_by': ['tax_levy_policy', 'commercial_authority_policy']}

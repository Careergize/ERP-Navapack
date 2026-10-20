"""Versioned development registry metadata, never executable policy or authority."""
POLICY_TYPES = ['PRICING_DISCOUNT', 'APPROVAL_MATRIX', 'CURRENCY_ROUNDING', 'VAT_LED',
                'CUSTOMER_ACCEPTANCE', 'DOCUMENT_NUMBERING', 'QUOTATION_VALIDITY',
                'ORDER_AMENDMENT', 'COSTING_UNIT_GOVERNANCE']

DECISIONS = {
    'P4-01': {'department': 'Finance / Management',
        'required_evidence': ['Adopted tax/levy rule, applicability, base, denominator, currency and effective date', 'Client legal/fiscal verification'],
        'conflicting_evidence': [
            {'reference': 'Phase 4A user requirement', 'interpretation': 'Higher of a percentage or fixed amount per 1,000 units; denominator/rates unresolved'},
            {'reference': 'frontend/src/lib/led.ts; 15 October notes', 'interpretation': '2.5% versus USD70/tonne using eligible kg and dated USD-to-UGX'},
            {'reference': 'frontend/docs/custom-costing-routing.md', 'interpretation': 'Historic C25 MAX(0.07,C24*2.5%); ambiguous unit/currency; original costing workbook absent'}],
        'outstanding_questions': ['Which denominator, rates and eligible products?', 'Which percentage/VAT base, discounts and levy ordering?', 'Which currency, FX evidence and legal basis?']},
    'P4-02': {'department': 'Finance', 'required_evidence': ['Currency precision and rounding sequence', 'Approved FX source/version if applicable'],
        'outstanding_questions': ['Which currencies, scales and rounding?', 'How are FX dates, revisions and discounts governed?']},
    'P4-03': {'department': 'Production / QC / Finance', 'required_evidence': ['Item/model unit and gross/net/yield evidence', 'Versioned conversion governance'],
        'outstanding_questions': ['Which exact stock/output units and precision?', 'How are waste, rejection and recoverable scrap treated?']},
    'P4-04': {'department': 'Management / Operations / Finance', 'required_evidence': ['Named delegated commercial matrix', 'Independent review and amendment/cancellation controls'],
        'outstanding_questions': ['Who approves which scoped amounts/discounts/credit?', 'How are confirmations, amendments and cancellations independently approved?']},
    'P4-05': {'department': 'Sales / Management / IT', 'required_evidence': ['Customer/team access policy', 'Verified customer acceptance and conversion requirements'],
        'outstanding_questions': ['Which owner/team/customer visibility?', 'What proves acceptance, rejection and quote conversion?']},
    'P4-06': {'department': 'Sales / Finance', 'required_evidence': ['Adopted numbering/template/signatory/terms standards'],
        'outstanding_questions': ['Which numbering, validity, legal identity and retention?', 'Which approved reusable documents?']},
    'P4-07': {'department': 'Management / Production / Stores', 'required_evidence': ['Separately approved downstream integration contracts'],
        'baseline_status': 'CONFIRMED_PRINCIPLES_DEFERRED',
        'outstanding_questions': ['How will later production/physical dispatch integrate under remaining Phase 3 gates?'],
        'confirmed_principles': ['Multi-product orders; stock and/or manufacturing fulfilment', 'No reservation or deduction on order creation/review',
            'Future physical dispatch is Stock OUT trigger', 'Governed confirmed changes', 'One Job Card may cover the whole order', 'Stock manufacturing may exist without an order']},
    'P4-08': {'department': 'Management / IT', 'required_evidence': ['Browser acceptance', 'Restricted runtime grants, migration/recovery and authorized release evidence'],
        'outstanding_questions': ['Are browser and release gates accepted?', 'Has controlled SOP adoption occurred?']},
}

"""Append a synthetic dataset; logical reset preserves all existing audit/history."""
import hashlib
import re
from pathlib import Path
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Permission
from django.db import connection, transaction
from django.utils import timezone
from apps.accounts.models import Employee
from apps.masters.models import Department, Unit, Product, ProductVariant, Material, Customer
from apps.inventory.models import Warehouse, WarehouseScope
from apps.core.audit import record_event
import uuid


CAPABILITIES = ['commercial.use_foundation', 'rehearsal.use_simulation',
    'masters.view_customer', 'masters.add_customer', 'masters.view_prospect', 'masters.view_unit',
    'masters.view_productvariant', 'masters.view_material', 'specifications.view_productmodelrevision',
    'inventory.view_warehouse']


class Command(BaseCommand):
    help = 'Trusted DEMO-owner seed. New generation = logical reset; no deletion or policy activation.'

    def add_arguments(self, parser):
        parser.add_argument('--database', required=True)
        parser.add_argument('--generation', required=True)
        parser.add_argument('--maker-password-file', required=True)
        parser.add_argument('--reviewer-password-file', required=True)
        parser.add_argument('--approval-reference', required=True)
        parser.add_argument('--retire-previous-generations', action='store_true')

    def handle(self, **o):
        if (settings.SETTINGS_MODULE != 'config.settings.demo' or settings.APP_ENV != 'DEMO'
                or o['database'] != settings.DEMO_DATABASE_NAME or not re.fullmatch(r'[a-z0-9]{1,16}', o['generation'])):
            raise CommandError('Explicit DEMO target and generation required.')
        passwords = [Path(o[k]).read_text().strip() for k in ('maker_password_file', 'reviewer_password_file')]
        for password in passwords:
            validate_password(password)
        if passwords[0] == passwords[1]:
            raise CommandError('Use independent synthetic actor passwords.')
        tag = o['generation']
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SELECT current_database(), instance_id::text, expires_at FROM core_demoboundary WHERE singleton')
            row = cursor.fetchone()
            if not row or row[0] != o['database'] or row[1] != settings.DEMO_INSTANCE_ID or row[2] <= timezone.now():
                raise CommandError('Approved current DEMO stamp required.')
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [70462090])
            maker_email = f'demo-maker+{tag}@example.invalid'
            if get_user_model().objects.filter(email=maker_email).exists():
                self.stdout.write('Generation already exists; unchanged (no password or data overwrite).')
                return
            maker, reviewer = [get_user_model().objects.create_user(email, password, name=f'SYNTHETIC DEMO {name}')
                for email, password, name in [(maker_email, passwords[0], 'Maker'),
                    (f'demo-reviewer+{tag}@example.invalid', passwords[1], 'Reviewer')]]
            retired = []
            if o['retire_previous_generations']:
                candidates = get_user_model().objects.filter(email__endswith='@example.invalid', name__startswith='SYNTHETIC DEMO ',
                    employee__employee_id__startswith='DEMO-', is_superuser=False, is_staff=False, is_master_admin=False).exclude(
                    pk__in=[maker.pk, reviewer.pk])
                retired = [str(pk) for pk in candidates.values_list('pk', flat=True)]
                get_user_model().objects.filter(pk__in=retired).update(is_active=False)
            fields = {'created_by': maker, 'updated_by': maker}
            dept = Department.objects.create(name=f'DEMO {tag} — synthetic only', **fields)
            for actor in (maker, reviewer):
                Employee.objects.create(user=actor, employee_id=f'DEMO-{tag}-{actor.pk}', department=dept,
                    designation='Synthetic demonstration actor; no operational authority', **fields)
                permissions = []
                for code in CAPABILITIES:
                    app, codename = code.split('.')
                    permissions.append(Permission.objects.get(content_type__app_label=app, codename=codename))
                actor.user_permissions.add(*permissions)
            warehouse = Warehouse.objects.create(code=f'DEMO-{tag}', name=f'Synthetic demo {tag}', created_by=maker)
            for actor, other in ((maker, reviewer), (reviewer, maker)):
                WarehouseScope.objects.create(user=actor, warehouse=warehouse, requested_by=actor, approved_by=other,
                    policy_reference='DEMO-SIMULATION-ONLY', evidence_reference=o['approval_reference'], expires_at=row[2])
            unit = Unit.objects.create(code=f'dkg{tag}', name=f'Demo kilogram {tag}', dimension='mass', **fields)
            product = Product.objects.create(name=f'Synthetic film {tag}', unit=unit, **fields)
            variants = [ProductVariant.objects.create(name=f'Synthetic {name} {tag}', product=product, unit=unit, category='packing', **fields)
                        for name in ('bag', 'pouch')]
            material = Material.objects.create(name=f'Synthetic resin {tag}', unit=unit, category='virgin', **fields)
            customer = Customer.objects.create(name=f'SYNTHETIC DEMO customer {tag}', customer_type='B2B', **fields)
            record_event(actor=reviewer, action='demo.seed', entity_type='demo.generation', entity_id=uuid.uuid4(),
                request_id=uuid.uuid4(), reason='Approved synthetic dataset generation',
                summary={'outcome': {'generation': tag, 'operational': False, 'retired_users':retired}, 'changed_fields': ['synthetic_dataset']})
            cursor.execute('SELECT runtime_role FROM core_demoboundary WHERE singleton')
            from psycopg import sql
            cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(cursor.fetchone()[0])))
            from apps.commercial import services as commercial
            from apps.commercial.handoffs import derive
            from apps.rehearsal import services as rehearsal
            def run(service, **payload):
                return service(actor=maker, key=str(uuid.uuid4()), request_id=uuid.uuid4(), reason='Synthetic demo seed', **payload)[0]
            data = {'currency': 'UGX', 'money_places': 2, 'rounding': 'HALF_UP', 'discount': '0', 'terms': 'DEMO ONLY',
                'customer': str(customer.pk), 'classification': 'B2B', 'lines': []}
            for i, variant in enumerate(variants):
                data['lines'].append({'variant': str(variant.pk), 'unit': str(unit.pk), 'quantity': str(100*(i+1)),
                    'unit_price': '3500', 'specifications': 'Synthetic demonstration specification', 'customisation': '',
                    'costing': {'materials': [{'material': str(material.pk), 'unit': str(unit.pk), 'price_unit': str(unit.pk),
                        'currency': 'UGX', 'quantity': str(110*(i+1)), 'price': '2500'}],
                        'processes': [], 'waste_percent': '0', 'rejection_percent': '0', 'markup_percent': '20',
                        'assumption_evidence': 'Synthetic demonstration assumptions; not approved yield'}})
            cost = run(commercial.command, kind='COSTING', data=data)
            quote = run(derive, source_id=cost['revision'])
            order = run(derive, source_id=quote['revision'])
            create = {'sales_order_revision': order['revision'], 'warehouse': str(warehouse.pk),
                      'routes': [{'line': 0, 'stages': ['EXTRUSION', 'PACKING']}, {'line': 1, 'stages': ['PACKING']}]}
            job = run(rehearsal.command, data=create)
            steps = [('review', {}), ('issue', {'quantity': '330', 'available_quantity': '330'})]
            for line, stage in ((0, 'EXTRUSION'), (0, 'PACKING'), (1, 'PACKING')):
                amount = str(100*(line+1))
                steps += [('start', {'line': line, 'stage': stage, 'machine': 'synthetic:demo-machine',
                    'operator': 'synthetic:demo-operator', 'input_quantity': amount}),
                    ('complete', {'line': line, 'stage': stage, 'output_quantity': amount, 'waste': '0', 'rejection': '0'})]
            steps += [('qc', {'outcome': 'FAIL', 'remarks': 'Synthetic demonstration failure'}),
                      ('qc', {'outcome': 'PASS', 'remarks': 'Synthetic reinspection'}), ('finish', {}), ('dispatch', {})]
            for action, values in steps:
                job = run(rehearsal.command, pk=job['id'], version=job['version'], action=action, data=values)
            run(rehearsal.command, data=create)
            import copy
            stock_data = copy.deepcopy(data)
            stock_data.pop('customer'); stock_data.pop('classification')
            stock = run(commercial.command, kind='COSTING', data=stock_data)
            run(rehearsal.command, data={'costing_revision': stock['revision'], 'warehouse': str(warehouse.pk),
                'routes': [{'line': i, 'stages': ['PACKING']} for i in range(2)]})
        self.stdout.write(f'Synthetic generation {tag} created. Accounts use example.invalid; no email sent. No stock or policy posted.')

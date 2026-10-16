import axios from 'axios';
import { api } from './api';
import { readToken } from './authSession';
import type { Customer } from '@/types';

export interface CustomerRecord {
  id: number; code: string; name: string; contact_person: string; phone: string; email: string;
  address: string; delivery_address: string; tin: string; customer_type: 'B2B' | 'B2C'; is_active: boolean;
}

export function customerFromApi(record: CustomerRecord): Customer {
  return { id: `db:${record.id}`, code: record.code, name: record.name, contactPerson: record.contact_person,
    phone: record.phone, email: record.email, billingAddress: record.address, deliveryAddress: record.delivery_address,
    tin: record.tin, customerType: record.customer_type };
}

export function customerPayload(customer: Omit<Customer, 'id'>) {
  return { name: customer.name.trim(), contact_person: customer.contactPerson.trim(), phone: customer.phone.trim(),
    email: customer.email?.trim() ?? '', address: customer.billingAddress?.trim() ?? '',
    delivery_address: customer.deliveryAddress?.trim() ?? '', tin: customer.tin?.trim() ?? '', customer_type: customer.customerType ?? 'B2B' };
}

function requireBackendLogin() {
  if (!readToken('navapack_access') && !readToken('navapack_refresh')) throw new Error('Sign in with a backend account to save customers permanently. Demo login cannot save to the database.');
}

export async function loadCustomers(): Promise<Customer[]> {
  requireBackendLogin();
  const customers: Customer[] = [];
  let page = 1;
  while (true) {
    const { data } = await api.get<{ results: CustomerRecord[]; next: string | null }>('/customers/', { params: { active: 'true', page } });
    customers.push(...data.results.map(customerFromApi));
    if (!data.next) return customers;
    page++;
  }
}

export async function createCustomer(customer: Omit<Customer, 'id'>, creationKey: string): Promise<Customer> {
  requireBackendLogin();
  const { data } = await api.post<CustomerRecord>('/customers/', { ...customerPayload(customer), creation_key: creationKey });
  return customerFromApi(data);
}

export async function updateCustomer(customer: Customer): Promise<Customer> {
  requireBackendLogin();
  if (!/^db:\d+$/.test(customer.id)) throw new Error('Select a saved backend customer to edit.');
  const { data } = await api.patch<CustomerRecord>(`/customers/${customer.id.slice(3)}/`, customerPayload(customer));
  return customerFromApi(data);
}

export function customerError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'Customer save/load could not reach the backend. Retry; the same save request will not create a duplicate.';
    if (error.response.status === 403) return 'Your backend account needs customer view/add/change permissions for this action.';
    return JSON.stringify(error.response.data);
  }
  return error instanceof Error ? error.message : 'Unable to save customer.';
}

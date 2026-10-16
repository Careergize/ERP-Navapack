import { createContext, useContext, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { MOCK_CUSTOMERS } from '@/lib/mockData';
import type { Customer } from '@/types';
import { createCustomer, updateCustomer, loadCustomers, customerError } from '@/lib/customersApi';
import { COMPANY_DEFAULTS, QUOTATION_EDIT_ROLES, type CompanySettings, type QuotationTerms } from '@/lib/quotations';
export interface CustomerProspect extends Customer { linkedCustomerId?: string }
interface CommercialValue { customers: Customer[]; customersLoading: boolean; customersError: string; reloadCustomers: () => Promise<void>; createSavedCustomer: (customer: Omit<Customer, 'id'>, creationKey: string) => Promise<Customer>; prospects: CustomerProspect[]; company: CompanySettings; termsTemplates: QuotationTerms[]; saveCustomer: (customer: Customer) => Promise<void>; addProspect: (prospect: Omit<CustomerProspect, 'id'>) => CustomerProspect; promoteProspect: (id: string, customerId?: string) => Customer; saveSettings: (company: CompanySettings) => void; saveTermsTemplate: (terms: QuotationTerms) => void }
const Context = createContext<CommercialValue | undefined>(undefined);
export function CommercialProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth(); const [customers, setCustomers] = useState(MOCK_CUSTOMERS); const customerRef = useRef(customers);
  const [customersLoading, setCustomersLoading] = useState(false), [customersError, setCustomersError] = useState('');
  const customerSession = useRef(user?.id);
  customerSession.current = user?.id;
  const isDemo = user?.id.startsWith('demo-');
  const publishCustomer = (customer: Customer) => { customerRef.current = [...customerRef.current.filter(c => c.id !== customer.id), customer]; setCustomers(customerRef.current); };
  const reloadCustomers = useCallback(async () => {
    if (!user || user.id.startsWith('demo-')) return;
    const accountId = user.id;
    setCustomersLoading(true); setCustomersError('');
    try {
      const rows = await loadCustomers();
      if (customerSession.current === accountId) { customerRef.current = rows; setCustomers(rows); }
    } catch (e) { if (customerSession.current === accountId) setCustomersError(customerError(e)); }
    finally { if (customerSession.current === accountId) setCustomersLoading(false); }
  }, [user?.id]);
  useEffect(() => {
    const rows = user?.id.startsWith('demo-') ? MOCK_CUSTOMERS : [];
    customerRef.current = rows; setCustomers(rows); setCustomersError(''); setCustomersLoading(false);
    void reloadCustomers();
  }, [reloadCustomers]);
  const [prospects, setProspects] = useState<CustomerProspect[]>([]); const prospectRef = useRef(prospects);
  const [company, setCompany] = useState(COMPANY_DEFAULTS); const [termsTemplates, setTermsTemplates] = useState<QuotationTerms[]>([]);
  const check = () => { if (!user || !QUOTATION_EDIT_ROLES.includes(user.role)) throw new Error('Your role cannot edit customer prospects.'); };
  return <Context.Provider value={{ customers, customersLoading, customersError, reloadCustomers, prospects, company, termsTemplates,
    createSavedCustomer: async (customer, creationKey) => { check(); if (customersLoading) throw new Error('Wait for the customer list to finish loading.'); const accountId = user?.id; const saved = await createCustomer(customer, creationKey); if (customerSession.current === accountId) publishCustomer(saved); return saved; },
    saveCustomer: async customer => { if (user?.role !== 'admin' || !customer.name.trim()) throw new Error('Admin manages the shared customer master.'); if (customersLoading) throw new Error('Wait for the customer list to finish loading.'); const accountId = user.id; try { const saved = customer.id.startsWith('db:') ? await updateCustomer(customer) : await createCustomer(customer, customer.id.startsWith('master-') ? customer.id.slice(7) : crypto.randomUUID()); if (customerSession.current === accountId) publishCustomer(saved); } catch(e) { throw new Error(customerError(e)); } },
    addProspect: draft => { check(); if (!draft.name.trim()) throw new Error('Enter prospect name.'); const p = { ...draft, id: crypto.randomUUID() }; prospectRef.current = [...prospectRef.current, p]; setProspects(prospectRef.current); return p; },
    promoteProspect: (id, existingId) => { check(); const p = prospectRef.current.find(p => p.id === id); if (!p) throw new Error('Prospect not found.'); if (p.linkedCustomerId) return customerRef.current.find(c => c.id === p.linkedCustomerId)!;
      const existing = existingId ? customerRef.current.find(c => c.id === existingId) : undefined;
      if (existingId && !existing) throw new Error('Select an existing customer by ID.');
      if (!existing && !isDemo) throw new Error('Save this prospect as a customer through the quotation new-customer form first, then link the saved customer here.');
      const c: Customer = existing ?? { ...p, id: crypto.randomUUID(), prospectId: p.id };
      if (!existing) { customerRef.current = [...customerRef.current, c]; setCustomers(customerRef.current); }
      prospectRef.current = prospectRef.current.map(row => row.id === id ? { ...row, linkedCustomerId: c.id } : row); setProspects(prospectRef.current); return c;
    },
    saveSettings: settings => { if (user?.role !== 'admin' || !settings.tradingName.trim() || !settings.currency.trim() || !Number.isInteger(settings.validityDays) || settings.validityDays < 0 || settings.validityDays > 3650 || !Number.isFinite(settings.taxRate) || settings.taxRate < 0 || settings.taxRate > 100 || !['inclusive', 'exclusive'].includes(settings.taxMode) || new Set(settings.banks.map(b => b.id)).size !== settings.banks.length) throw new Error('Admin must provide valid company, currency, validity and tax settings.'); setCompany(structuredClone(settings)); },
    saveTermsTemplate: terms => { if (user?.role !== 'admin' || !terms.name?.trim()) throw new Error('Admin must name the terms template.'); setTermsTemplates(all => [...all.filter(t => t.name !== terms.name), structuredClone(terms)]); },
  }}>{children}</Context.Provider>;
}
export function useCommercial() { const value = useContext(Context); if (!value) throw new Error('CommercialProvider required'); return value; }

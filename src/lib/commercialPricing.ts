import { roundMoney } from './customCosting';
export type TaxMode = 'inclusive' | 'exclusive';
export const COMMERCIAL_ROUNDING = 'Round each line and monetary subtotal/tax/total to 2 decimals; preserve entered unit-price precision.';
export interface CommercialTotals { subtotal: number; subtotalBeforeTax: number; discount: number; discountBeforeTax: number; taxableAmount: number; tax: number; total: number }
export function calculateCommercialTotals(lines: { quantity: number; unitPrice: number }[], discount: number, taxRate: number, mode: TaxMode): CommercialTotals {
  if (!['inclusive', 'exclusive'].includes(mode) || !Number.isFinite(taxRate) || taxRate < 0 || taxRate > 100 || !Number.isFinite(discount) || discount < 0 || lines.some(l => !Number.isFinite(l.quantity) || l.quantity <= 0 || !Number.isFinite(l.unitPrice) || l.unitPrice < 0)) throw new Error('Complete positive quantities, nonnegative prices/discount and valid tax treatment.');
  const subtotal = roundMoney(lines.reduce((sum, l) => sum + roundMoney(l.quantity * l.unitPrice), 0));
  discount = roundMoney(discount);
  if (!Number.isFinite(subtotal) || discount > subtotal) throw new Error('Discount exceeds subtotal or amounts exceed the supported range.');
  const basis = roundMoney(subtotal - discount), factor = 1 + taxRate / 100;
  const taxableAmount = mode === 'inclusive' ? roundMoney(basis / factor) : basis;
  const tax = mode === 'inclusive' ? roundMoney(basis - taxableAmount) : roundMoney(taxableAmount * taxRate / 100);
  const total = mode === 'inclusive' ? basis : roundMoney(taxableAmount + tax);
  const subtotalBeforeTax = mode === 'inclusive' ? roundMoney(subtotal / factor) : subtotal;
  if (![taxableAmount, tax, total].every(Number.isFinite)) throw new Error('Unsupported monetary range.');
  return { subtotal, subtotalBeforeTax, discount, discountBeforeTax: roundMoney(subtotalBeforeTax - taxableAmount), taxableAmount, tax, total };
}

import { api } from './api';
import type { Page } from './commercialApi';
export const productionStages = ['EXTRUSION', 'PRINTING', 'SLITTING', 'MAKING', 'PACKING'] as const;
export type RehearsalAction = 'review' | 'issue' | 'start' | 'complete' | 'qc' | 'finish' | 'dispatch';
export interface RehearsalStage { name: string; status: string; [key: string]: unknown }
export interface RehearsalJob {
  id: string; version: number; status: string; sales_order_revision: string | null; costing_revision?: string | null; purpose?: string; warehouse: string;
  simulation: true; operational_posting: false;
  snapshot: { source: Record<string, unknown>; routes: {line: number; stages: RehearsalStage[]}[]; material_issue: unknown; qc: unknown[]; history: unknown[]; [key: string]: unknown };
  invoice_preview: { watermark: string; currency: string; net_estimate: string; vat: null; led: null; payable_total: null };
}
export interface RehearsalRevision { id: string; number: number; at: string; reason: string; snapshot: RehearsalJob['snapshot']; [key: string]: unknown }
export const rehearsalJobs = async (page = 1) => (await api.get<Page<RehearsalJob>>('/rehearsal/jobs/', {params: {page}})).data;
export const rehearsalJob = async (id: string) => (await api.get<RehearsalJob>(`/rehearsal/jobs/${id}/`)).data;
export const rehearsalHistory = async (id: string, page = 1) => (await api.get<Page<RehearsalRevision>>(`/rehearsal/jobs/${id}/history/`, {params: {page}})).data;
export const rehearsalDashboard = async () => (await api.get<Record<string, unknown>>('/rehearsal/jobs/dashboard/')).data;
export const createRehearsal = async (body: {sales_order_revision?: string; costing_revision?: string; warehouse: string; routes: {line: number; stages: string[]}[]; reason: string}, key: string) => (await api.post<RehearsalJob>('/rehearsal/jobs/', body, {headers: {'Idempotency-Key': key}})).data;
export const commandRehearsal = async (job: RehearsalJob, action: RehearsalAction, data: Record<string, unknown>, reason: string, key: string) => (await api.post<RehearsalJob>(`/rehearsal/jobs/${job.id}/command/`, {action, data, reason}, {headers: {'Idempotency-Key': key, 'If-Match': `"${job.version}"`}})).data;

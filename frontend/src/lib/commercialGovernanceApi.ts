import { api } from './api';
import { allCommercialReferences } from './commercialApi';
export interface ProposalRecord { id: string; kind: 'POLICY'|'DECISION'; key: string; version: number; revision: string; status: string; content: Record<string, unknown>; reason: string; authority: false; active: false; approved: false }
export interface DecisionRecord { decision_id: string; department: string; status: string; baseline_status: string; required_evidence: string[]; conflicting_evidence: { reference: string; interpretation: string }[]; outstanding_questions: string[]; latest_submission: ProposalRecord | null; review_history_count: number; review_performed: false }
export interface DecisionRegistry { catalog_version: string; policy_types: string[]; results: DecisionRecord[] }
export const decisionRegistry = async () => (await api.get<DecisionRegistry>('/commercial/decision-registry/')).data;
export const proposalRecords = (kind: 'POLICY'|'DECISION') => allCommercialReferences<ProposalRecord>(`/commercial/${kind === 'POLICY' ? 'policy-proposals' : 'decision-submissions'}/`);
export async function saveProposal(kind: 'POLICY'|'DECISION', data: Record<string, unknown>, reason: string, key: string, existing?: ProposalRecord) {
  const url = `/commercial/${kind === 'POLICY' ? 'policy-proposals' : 'decision-submissions'}/`;
  const headers = { 'Idempotency-Key': key, ...(existing ? { 'If-Match': `"${existing.version}"` } : {}) };
  return (existing ? await api.patch<ProposalRecord>(`${url}${existing.id}/`, { data, reason }, { headers }) : await api.post<ProposalRecord>(url, { data, reason }, { headers })).data;
}
export const proposalHistory = (record: ProposalRecord) => allCommercialReferences<{ id: string; number: number; status: string; reason: string; author: string; created_at: string; content: Record<string, unknown> }>(`/commercial/${record.kind === 'POLICY' ? 'policy-proposals' : 'decision-submissions'}/${record.id}/history/`);

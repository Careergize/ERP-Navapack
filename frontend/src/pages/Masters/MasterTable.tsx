import { FormEvent, useEffect, useState } from "react";
import { X } from "lucide-react";
import type { Stage } from "@/types";

export const ALL_MASTER_STAGES: Stage[] = ["Extrusion", "Printing", "Packaging", "Stock", "Ready to Sale"];

export type MasterRow = { id: string };
export type MasterColumn = { key: string; label: string; kind?: "text" | "stages" };

interface MasterTableProps<T extends MasterRow> {
  title: string;
  columns: MasterColumn[];
  rows: T[];
  onAdd: (row: T) => void;
  onEdit: (row: T) => void;
}

type FormValue = string | Stage[];

const stageDot = (stage: Stage, active: boolean) => (
  <span
    key={stage}
    title={stage}
    className={`h-2 w-6 rounded-full ${active ? "bg-green" : "bg-gray-200"}`}
  />
);

function renderValue(value: unknown, column: MasterColumn) {
  if (column.kind === "stages") {
    const stages = Array.isArray(value) ? value : [];
    return <div className="flex gap-1">{ALL_MASTER_STAGES.map((stage) => stageDot(stage, stages.includes(stage)))}</div>;
  }
  return <span>{String(value ?? "—")}</span>;
}

export function MasterTable<T extends MasterRow>({ title, columns, rows, onAdd, onEdit }: MasterTableProps<T>) {
  const [editingRow, setEditingRow] = useState<T | null>(null);
  const [formValues, setFormValues] = useState<Record<string, FormValue>>({});

  useEffect(() => {
    if (!editingRow) return;
    const values: Record<string, FormValue> = {};
    const rowValues = editingRow as unknown as Record<string, unknown>;
    columns.forEach((column) => {
      const value = rowValues[column.key];
      values[column.key] = column.kind === "stages" ? ((Array.isArray(value) ? value : []) as Stage[]) : String(value ?? "");
    });
    setFormValues(values);
  }, [columns, editingRow]);

  function openAdd() {
    const blank: MasterRow = { id: `master-${Date.now()}` };
    const blankValues = blank as Record<string, unknown>;
    columns.forEach((column) => { blankValues[column.key] = column.kind === "stages" ? [] : ""; });
    setEditingRow(blank as T);
  }

  function closeModal() {
    setEditingRow(null);
    setFormValues({});
  }

  function toggleStage(stage: Stage) {
    const selected = (formValues.stages as Stage[] | undefined) ?? [];
    setFormValues({ ...formValues, stages: selected.includes(stage) ? selected.filter((item) => item !== stage) : [...selected, stage] });
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!editingRow) return;
    const saved = { ...editingRow, ...formValues } as T;
    if (rows.some((row) => row.id === editingRow.id)) onEdit(saved);
    else onAdd(saved);
    closeModal();
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-navy">{title}</h2>
        <button type="button" onClick={openAdd} className="rounded-card bg-navy px-4 py-2 text-sm font-medium text-white hover:opacity-90">
          Add {title.slice(0, -1)}
        </button>
      </div>

      <div className="overflow-hidden rounded-card border border-gray-100 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-navy text-xs text-white">
              <tr>
                {columns.map((column) => <th key={column.key} className="px-4 py-3 font-medium">{column.label}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row) => (
                <tr key={row.id} onClick={() => setEditingRow(row)} className="cursor-pointer text-gray-600 hover:bg-gray-50">
                  {columns.map((column) => <td key={column.key} className="px-4 py-3">{renderValue((row as unknown as Record<string, unknown>)[column.key], column)}</td>)}
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={columns.length} className="px-4 py-8 text-center text-sm text-gray-500">No {title.toLowerCase()} yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {editingRow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/30 p-4" role="dialog" aria-modal="true" aria-label={`${rows.some((row) => row.id === editingRow.id) ? "Edit" : "Add"} ${title.slice(0, -1)}`}>
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-card bg-white p-5 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-navy">{rows.some((row) => row.id === editingRow.id) ? "Edit" : "Add"} {title.slice(0, -1)}</h3>
              <button type="button" onClick={closeModal} className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-navy" aria-label="Close"><X size={18} /></button>
            </div>
            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              {columns.map((column) => (
                <label key={column.key} className="block text-sm text-gray-600">
                  {column.label}
                  {column.kind === "stages" ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {ALL_MASTER_STAGES.map((stage) => {
                        const active = ((formValues[column.key] as Stage[] | undefined) ?? []).includes(stage);
                        return <button key={stage} type="button" onClick={() => toggleStage(stage)} className={`rounded-full border px-3 py-1.5 text-xs font-medium ${active ? "border-green bg-green/10 text-green" : "border-gray-200 text-gray-500 hover:border-navy hover:text-navy"}`}>{stage}</button>;
                      })}
                    </div>
                  ) : (
                    <input required={column.key !== "department"} value={String(formValues[column.key] ?? "")} onChange={(event) => setFormValues({ ...formValues, [column.key]: event.target.value })} className="mt-1 block w-full rounded-card border border-gray-200 px-3 py-2 text-sm text-ink focus:border-blue focus:outline-none" />
                  )}
                </label>
              ))}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={closeModal} className="rounded-card border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:border-navy hover:text-navy">Cancel</button>
                <button type="submit" className="rounded-card bg-navy px-4 py-2 text-sm font-medium text-white hover:opacity-90">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

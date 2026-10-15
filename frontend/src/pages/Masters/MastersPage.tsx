import { GenerateQuotation } from '@/components/GenerateQuotation';
import { useCommercial } from '@/context/CommercialContext';
import { useModels } from '@/context/ModelsContext';
import { ModelManager } from './ModelManager';
import { useState } from "react";
import { MasterTable, type MasterColumn } from "@/pages/Masters/MasterTable";
import { MOCK_DEPARTMENTS, MOCK_ITEMS, MOCK_SUPPLIERS, MOCK_USERS } from "@/lib/mockData";
import type { Customer, Department, Item, MasterUser, Model, Supplier } from "@/types";

type MasterKey = "items" | "models" | "customers" | "suppliers" | "departments" | "users";
type MasterData = Item | Model | Customer | Supplier | Department | MasterUser;

interface MasterConfig {
  label: string;
  columns: MasterColumn[];
  rows: MasterData[];
}

const CONFIG_COLUMNS: Record<MasterKey, MasterColumn[]> = {
  items: [
    { key: "name", label: "Name" },
    { key: "unit", label: "Unit" },
    { key: "category", label: "Category" },
  ],
  models: [
    { key: "name", label: "Name" },
    { key: "billOfMaterials", label: "Bill of Materials" },
    { key: "stages", label: "Stages", kind: "stages" },
  ],
  customers: [
    { key: "name", label: "Name" },
    { key: "contactPerson", label: "Contact Person" },
    { key: "phone", label: "Phone" },
  ],
  suppliers: [
    { key: "name", label: "Name" },
    { key: "materialSupplied", label: "Material Supplied" },
    { key: "phone", label: "Phone" },
  ],
  departments: [
    { key: "name", label: "Name" },
    { key: "assignedProductionManager", label: "Assigned Production Manager" },
  ],
  users: [
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "role", label: "Role" },
    { key: "department", label: "Department" },
  ],
};

export function MastersPage() {
  const [selected, setSelected] = useState<MasterKey>("items");
  const [items, setItems] = useState<Item[]>(MOCK_ITEMS);
  const { models } = useModels();
  const { customers, saveCustomer } = useCommercial();
  const [suppliers, setSuppliers] = useState<Supplier[]>(MOCK_SUPPLIERS);
  const [departments, setDepartments] = useState<Department[]>(MOCK_DEPARTMENTS);
  const [users, setUsers] = useState<MasterUser[]>(MOCK_USERS);

  const configs: Record<MasterKey, MasterConfig> = {
    items: { label: "Items", columns: CONFIG_COLUMNS.items, rows: items },
    models: { label: "Models", columns: CONFIG_COLUMNS.models, rows: models },
    customers: { label: "Customers", columns: CONFIG_COLUMNS.customers, rows: customers },
    suppliers: { label: "Suppliers", columns: CONFIG_COLUMNS.suppliers, rows: suppliers },
    departments: { label: "Departments", columns: CONFIG_COLUMNS.departments, rows: departments },
    users: { label: "Users", columns: CONFIG_COLUMNS.users, rows: users },
  };

  function addRow(row: MasterData) {
    if (selected === "items") setItems((current) => [...current, row as Item]);

    if (selected === "customers") saveCustomer(row as Customer);
    if (selected === "suppliers") setSuppliers((current) => [...current, row as Supplier]);
    if (selected === "departments") setDepartments((current) => [...current, row as Department]);
    if (selected === "users") setUsers((current) => [...current, row as MasterUser]);
  }

  function editRow(row: MasterData) {
    if (selected === "items") setItems((current) => current.map((item) => item.id === row.id ? row as Item : item));

    if (selected === "customers") saveCustomer(row as Customer);
    if (selected === "suppliers") setSuppliers((current) => current.map((item) => item.id === row.id ? row as Supplier : item));
    if (selected === "departments") setDepartments((current) => current.map((item) => item.id === row.id ? row as Department : item));
    if (selected === "users") setUsers((current) => current.map((item) => item.id === row.id ? row as MasterUser : item));
  }

  const config = configs[selected];

  return (
    <div>{selected==='customers'&&<section className="mb-4 rounded-card border p-3"><h2 className="font-semibold">Customer quotation actions</h2>{customers.map(c=><p key={c.id}>{c.name} · <GenerateQuotation customerId={c.id}/></p>)}</section>}
      <h1 className="text-2xl font-semibold text-navy">Masters</h1>
      <p className="mt-1 text-sm text-gray-500">Manage the reference data used across NavaPack operations.</p>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[190px_minmax(0,1fr)]">
        <nav aria-label="Master data types" className="space-y-1">
          {Object.entries(configs).map(([key, item]) => {
            const masterKey = key as MasterKey;
            const active = selected === masterKey;
            return <button key={masterKey} type="button" onClick={() => setSelected(masterKey)} className={`flex w-full items-center rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors ${active ? "bg-navy/10 text-navy" : "text-gray-500 hover:bg-white hover:text-navy"}`}>{item.label}</button>;
          })}
        </nav>

        {selected === "models" ? <ModelManager /> : <MasterTable
          title={config.label}
          columns={config.columns}
          rows={config.rows}
          onAdd={addRow}
          onEdit={editRow}
        />}
      </div>
    </div>
  );
}

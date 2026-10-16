export type Category = "raw" | "finished" | "granules";
export type Direction = "in" | "out";

interface ItemMaster {
  category: Category;
  unit: string;
  minLevel?: number;
}

// One ledger line. Every stock figure on this page is calculated from these lines,
// so stock-in and stock-out always add up: opening + inward − outward = closing.
export interface Movement {
  id: string;
  date: string; // YYYY-MM-DD
  category: Category;
  item: string;
  model?: string; // finished goods only
  type: Direction;
  qty: number;
  ref: string; // Supplier bill, Job Card, Sales Order, recycling batch or granules sale
  party: string;
  price?: number; // inward raw material only, per unit
  currency?: "INR" | "USD";
  rate?: number; // USD to INR rate entered at purchase
}

export const ITEMS: Record<string, ItemMaster> = {
  "HDPE resin": { category: "raw", unit: "kg", minLevel: 1000 },
  "LDPE resin": { category: "raw", unit: "kg", minLevel: 800 },
  "Master batch": { category: "raw", unit: "kg", minLevel: 100 },
  "Printing ink": { category: "raw", unit: "kg", minLevel: 50 },
  "Stitching thread": { category: "raw", unit: "kg", minLevel: 30 },
  "Woven sack 50 kg": { category: "finished", unit: "pcs" },
  "Woven sack 25 kg": { category: "finished", unit: "pcs" },
  "Laminated bag": { category: "finished", unit: "pcs" },
  "Non-woven carry bag": { category: "finished", unit: "pcs" },
  "Recycled granules": { category: "granules", unit: "kg" },
};

const MODEL_OF: Record<string, string> = {
  "Woven sack 50 kg": "Model A",
  "Woven sack 25 kg": "Model A",
  "Laminated bag": "Model B",
  "Non-woven carry bag": "Model C",
};

let seq = 0;
const mv = (
  date: string,
  item: string,
  type: Direction,
  qty: number,
  ref: string,
  party: string,
  cost?: { price: number; currency: "INR" | "USD"; rate?: number },
): Movement => ({
  id: `m${++seq}`,
  date,
  category: ITEMS[item].category,
  item,
  model: MODEL_OF[item],
  type,
  qty,
  ref,
  party,
  ...cost,
});

const inr = (price: number) => ({ price, currency: "INR" as const });
const usd = (price: number, rate: number) => ({ price, currency: "USD" as const, rate });

export const MOVEMENTS: Movement[] = [
  // Raw material inward and outward
  mv("2026-07-28", "HDPE resin", "in", 1800, "Opening balance", "Store", inr(96)),
  mv("2026-08-05", "HDPE resin", "in", 2500, "PO-2208", "Reliance Polymers", usd(1.15, 82.9)),
  mv("2026-08-12", "HDPE resin", "out", 1200, "JC-0310", "Extrusion"),
  mv("2026-08-20", "HDPE resin", "out", 1000, "JC-0312", "Extrusion"),
  mv("2026-09-02", "HDPE resin", "in", 2500, "PO-2214", "Reliance Polymers", usd(1.18, 83.1)),
  mv("2026-09-09", "HDPE resin", "out", 1100, "JC-0316", "Extrusion"),
  mv("2026-09-16", "HDPE resin", "out", 900, "JC-0317", "Extrusion"),
  mv("2026-09-20", "HDPE resin", "out", 350, "JC-0316", "Extrusion"),
  mv("2026-07-25", "LDPE resin", "in", 900, "Opening balance", "Store", inr(105)),
  mv("2026-08-10", "LDPE resin", "in", 600, "PO-2209", "Supreme Traders", inr(106)),
  mv("2026-08-18", "LDPE resin", "out", 700, "JC-0311", "Lamination"),
  mv("2026-09-04", "LDPE resin", "out", 450, "JC-0315", "Lamination"),
  mv("2026-09-15", "LDPE resin", "out", 300, "JC-0316", "Lamination"),
  mv("2026-07-25", "Master batch", "in", 210, "Opening balance", "Store", inr(240)),
  mv("2026-08-15", "Master batch", "out", 80, "JC-0311", "Extrusion"),
  mv("2026-09-06", "Master batch", "in", 150, "PO-2215", "Colour Chem India", inr(245)),
  mv("2026-09-10", "Master batch", "out", 60, "JC-0316", "Extrusion"),
  mv("2026-09-18", "Master batch", "out", 50, "JC-0317", "Extrusion"),
  mv("2026-07-25", "Printing ink", "in", 85, "Opening balance", "Store", inr(620)),
  mv("2026-08-20", "Printing ink", "out", 20, "JC-0312", "Printing"),
  mv("2026-09-12", "Printing ink", "in", 40, "PO-2216", "Inkart Supplies", inr(640)),
  mv("2026-09-14", "Printing ink", "out", 62, "JC-0316", "Printing"),
  mv("2026-07-25", "Stitching thread", "in", 45, "Opening balance", "Store", inr(450)),
  mv("2026-09-05", "Stitching thread", "out", 12, "JC-0314", "Bag making"),
  // Finished goods, moved in from production and out on dispatch
  mv("2026-08-14", "Woven sack 50 kg", "in", 2500, "JC-0310", "Stock keeping"),
  mv("2026-08-28", "Woven sack 50 kg", "out", 1800, "SO-1038", "Apex Packaging"),
  mv("2026-09-05", "Woven sack 50 kg", "in", 3000, "JC-0314", "Stock keeping"),
  mv("2026-09-12", "Woven sack 50 kg", "out", 2600, "SO-1041", "Kaveri Traders"),
  mv("2026-08-20", "Woven sack 25 kg", "in", 1500, "JC-0311", "Stock keeping"),
  mv("2026-09-08", "Woven sack 25 kg", "out", 900, "SO-1040", "Kaveri Traders"),
  mv("2026-09-19", "Woven sack 25 kg", "in", 1200, "JC-0316", "Stock keeping"),
  mv("2026-08-25", "Laminated bag", "in", 2000, "JC-0312", "Stock keeping"),
  mv("2026-09-11", "Laminated bag", "out", 1500, "SO-1041", "Apex Packaging"),
  mv("2026-09-03", "Non-woven carry bag", "in", 1800, "JC-0313", "Stock keeping"),
  mv("2026-09-17", "Non-woven carry bag", "out", 1000, "SO-1042", "Apex Packaging"),
  // Recycled granules: produced from waste, then sold or transferred
  mv("2026-07-30", "Recycled granules", "in", 260, "Opening balance", "Recycling"),
  mv("2026-09-04", "Recycled granules", "in", 400, "W-089", "Recycling"),
  mv("2026-09-11", "Recycled granules", "in", 450, "W-090", "Recycling"),
  mv("2026-09-19", "Recycled granules", "in", 390, "W-091", "Recycling"),
  mv("2026-09-15", "Recycled granules", "out", 600, "GS-014", "Shree Polymers"),
  mv("2026-09-22", "Recycled granules", "out", 400, "GS-015", "Deccan Plastics"),
];


const normalize = (name: string) => name.toLowerCase().replace(/\s+/g, '');
export function getAvailableStock(name: string, unit: string): number | undefined {
  const key = Object.keys(ITEMS).find(item => normalize(item) === normalize(name) && ITEMS[item].unit === unit);
  if (!key) return undefined;
  return MOVEMENTS.filter(m => m.item === key).reduce((sum, m) => sum + (m.type === 'in' ? m.qty : -m.qty), 0);
}

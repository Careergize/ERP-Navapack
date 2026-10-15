import assert from 'node:assert/strict';
import { createServer } from 'vite';

const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
try {
  const { RAW_MATERIALS, RAW_MOVEMENTS, rawMaterialBalance } = await server.ssrLoadModule('/src/lib/rawMaterialData.ts');
  const known = RAW_MATERIALS.find(item => item.openingStock !== null);
  const before = rawMaterialBalance(known, RAW_MOVEMENTS);
  const ledger = [...RAW_MOVEMENTS,
    { materialId: known.id, date: '2026-10-08', movementType: 'IN', quantity: 5 },
    { materialId: known.id, date: '2026-10-08', movementType: 'OUT', quantity: 3 },
  ];
  assert.equal(rawMaterialBalance(known, ledger).currentStock, before.currentStock + 2);
  assert.equal(rawMaterialBalance(known, RAW_MOVEMENTS).currentStock, before.currentStock);
  const unknown = RAW_MATERIALS.find(item => item.openingStock === null);
  assert.equal(rawMaterialBalance(unknown, [...ledger, { materialId: unknown.id, date: '2026-10-08', movementType: 'IN', quantity: 5 }]).currentStock, null);
  const month = rawMaterialBalance(known, ledger, '2026-10');
  assert.equal(month.currentStock, month.openingStock + month.stockIn - month.stockOut);
  const { CONSUMABLE_CATEGORIES, CONSUMABLE_UNITS, consumableBalance } = await server.ssrLoadModule('/src/lib/consumableData.ts');
  assert.deepEqual(CONSUMABLE_CATEGORIES.map(([, label]) => label), ['Imported Spare', 'Local Spare']);
  assert.deepEqual(CONSUMABLE_UNITS, ['Each', 'Both', 'Litres', 'Kilos']);
  const item = { id: 'a', name: 'Test', category: 'imported', unit: 'Each', openingStock: 10, openingDate: '2026-10-08' };
  const movements = [{ materialId: 'a', type: 'IN', quantity: 5 }, { materialId: 'a', type: 'OUT', quantity: 3 }, { materialId: 'other-unit', type: 'IN', quantity: 100 }];
  assert.deepEqual(consumableBalance(item, movements), { stockIn: 5, stockOut: 3, currentStock: 12 });
  assert.equal(consumableBalance(item, [...movements, { materialId: 'a', type: 'OUT', quantity: 20 }]).currentStock, -8);
  console.log('Passed: raw IN/OUT, immutable source balances, unknown openings, monthly carry-forward, consumable categories/units and independent signed ledgers.');
} finally {
  await server.close();
}

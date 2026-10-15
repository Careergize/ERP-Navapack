import assert from 'node:assert/strict';
import { createServer } from 'vite';

// Exercise the actual TypeScript data boundary without a browser or backend.
const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
try {
  const { FINISHED_GOODS: products, FINISHED_MOVEMENTS: movements, finishedBalance, findFinishedGood, matchesFinishedGood } =
    await server.ssrLoadModule('/src/lib/finishedGoodsData.ts');
  assert.equal(products.length, 368);
  assert.equal(new Set(products.map(product => product.id)).size, products.length);
  for (const [category, count] of [['carrier-bags', 78], ['flat-bags', 244], ['packing', 46]]) {
    assert.equal(products.filter(product => product.category === category).length, count);
  }
  assert.equal(movements.length, 799);
  assert.equal(movements.filter(movement => movement.date === '2026-10-01').length, 2);
  const row = (sheet, index) => products.find(product => product.sourceSheet === sheet && product.sourceRow === index);
  for (const product of products.filter(product => product.openingStock !== null)) {
    assert.ok(Math.abs(finishedBalance(product, movements).currentStock - product.sourceClosingStock) < 0.00001, `${product.sourceSheet}, row ${product.sourceRow}`);
  }
  const white = row('Carrier Bags', 4);
  assert.deepEqual(finishedBalance(white, movements), { openingStock: 71, stockIn: 1, stockOut: 4, currentStock: 68 });
  assert.notEqual(row('Carrier Bags', 6).id, row('Carrier Bags', 7).id);
  assert.equal(row('Carrier Bags', 8).customer, ''); // Generic row is not Lamech stock.
  assert.equal(row('Carrier Bags', 7).unit, 'ctn');
  assert.equal(row('Carrier Bags', 7).sourceUnit, '');
  assert.notEqual(row('Flat Bags', 5).id, row('Flat Bags', 6).id); // Packing size matters.
  assert.equal(row('Flat Bags', 189).customer, 'Iz Best Enterprises');
  assert.equal(row('Flat Bags', 252).customer, 'De Master Confectijnaries');
  assert.equal(products.filter(product => product.dataNotes.some(note => note.startsWith('Repeated variant'))).length, 4);
  assert.notEqual(row('Flat Bags', 222).id, row('Flat Bags', 226).id);
  const amina = row('Flat Bags', 80);
  assert.deepEqual(finishedBalance(amina, movements, '2026-09'), { openingStock: 0, stockIn: 4, stockOut: 0, currentStock: 4 });
  assert.deepEqual(finishedBalance(amina, movements, '2026-10'), { openingStock: 4, stockIn: 6, stockOut: 10, currentStock: 0 });
  const adjusted = [...movements,
    { id: 'test-in', productId: white.id, date: '2026-10-05', type: 'IN', quantity: 10, unit: 'ctn' },
    { id: 'test-out', productId: white.id, date: '2026-10-05', type: 'OUT', quantity: 3, unit: 'ctn' },
  ];
  assert.equal(finishedBalance(white, adjusted).currentStock, 75);
  assert.equal(finishedBalance(white, adjusted, '2026-09').currentStock, 68);
  assert.deepEqual(finishedBalance(white, adjusted, '2026-10'), { openingStock: 68, stockIn: 10, stockOut: 3, currentStock: 75 });
  assert.equal(finishedBalance(white, movements, '2026-08').currentStock, null);
  const packing = row('Packing', 4);
  assert.equal(packing.openingDate, '2026-05-01');
  assert.equal(finishedBalance(packing, movements).currentStock, null);
  assert.equal(findFinishedGood(undefined, 'WHITE#15', 'ctn'), undefined); // Ambiguous identity.
  assert.equal(findFinishedGood(white.id, 'any label', 'ctn').id, white.id);
  assert.ok(matchesFinishedGood(row('Carrier Bags', 6), 'WHITE #15'));
  assert.ok(matchesFinishedGood(row('Flat Bags', 5), '5X8'));
  assert.ok(matchesFinishedGood(row('Carrier Bags', 6), 'BEST'));
  assert.ok(matchesFinishedGood(row('Carrier Bags', 7), 'LAMECH'));
  console.log('Passed: variant identity, all recorded workbook closings, source grouping, search, IN/OUT, monthly carry-forward and unknown Packing balances.');
} finally {
  await server.close();
}

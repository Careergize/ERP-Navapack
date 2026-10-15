import type { QCCategory, QCItem, QCTemplate, ResponseType } from './quality';
const items = (labels: string[], type: ResponseType, acceptable: string): QCItem[] => labels.map((label, index) => ({ id: `check-${index + 1}`, label, type, acceptable, required: true, allowNA: true }));
const template = (id: string, name: string, category: QCCategory, checklist: QCItem[], applicable = ''): QCTemplate => ({ id, name, category, revision: 1, effectiveDate: '2026-10-13', department: category === 'machine' ? 'Maintenance' : 'Quality', frequency: category === 'raw' ? 'per_receipt' : category === 'production' ? 'per_batch' : category === 'machine' ? 'weekly' : 'per_activity', applicable, active: true, approvalRequired: true, items: checklist, source: 'User task transcription; eight photographs unavailable. Document code unrecorded; verify before operational use.' });
export const QC_TEMPLATES: QCTemplate[] = [
  template('personnel-safety', 'Personnel Safety Checklist', 'safety', items([
    'Personnel wearing correct protective clothing', 'No eating or drinking in the processing area', 'No smoking in the processing area', 'No jewellery, watches or hanging items', 'No personal belongings in the processing area', 'Personnel in good health without visible signs of contagious illness', 'Personnel operating in a safe environment',
  ], 'tick_cross', 'Tick')),
  template('extruded-rolls', 'Material Sample Test — Extruded Rolls', 'production', [
    ...items(['Roll width matches Sales Order', 'Material matches Sales Order', 'Material colour matches Sales Order', 'Printed roll treated where required', 'Roll thickness matches specification', 'Printed colours match approved instructions', 'Objectionable odour present', 'Tubing opens freely', 'Physical appearance acceptable'], 'yes_no', 'Yes').map((i, index) => index === 6 ? { ...i, acceptable: 'No' } : i),
    { id: 'actual-width', label: 'Actual roll width / specification', type: 'numeric', measurementUnit: 'mm', required: true, allowNA: false },
    { id: 'actual-thickness', label: 'Actual thickness / specification', type: 'numeric', measurementUnit: 'micron', required: true, allowNA: false },
  ]),
  template('weekly-extruder', 'Weekly Extruder Machine Checklist', 'machine', items(['Electrical Panel', 'Gearbox Oil', 'Bearings', 'Sprocket / Chain', 'Motor Pulley and Belts', 'Rollers'], 'ok_not_ok', 'OK'), 'extruder'),
  template('weekly-recycle-extruder', 'Weekly Recycle Extruder Checklist', 'machine', items(['Electrical Panel', 'Gearbox Oil', 'Bearings', 'Hydraulic Unit', 'Motor Pulley and Belts', 'Screen Changer'], 'ok_not_ok', 'OK'), 'recycle_extruder'),
  template('factory-cleaning', 'Factory/General Area Cleaning Checklist', 'cleaning', [{ id: 'observations', label: 'Cleaning observations / outcome (digital review field)', type: 'text', required: true, allowNA: false }]),
  template('raw-receipt', 'Raw Material Receipt and Analysis Record', 'raw', items(['Appearance', 'Colour', 'Packaging Integrity'], 'ok_not_ok', 'OK')),
  { ...template('ksec', 'KSEC — checks and meaning pending clarification', 'safety', [{ id:'ksec-pending', label:'Client-confirmed checklist required before activation', type:'text', required:true, allowNA:false }]), active:false, frequency:'on_demand', source:'Undefined client term. Admin must configure confirmed checks, category and frequency before activation.' },
];
export const CLEANING_AREAS = ['Office', 'Main Production — Extruder Section', 'Main Production — Bag Making Section', 'Finished Goods Store', 'Material Store', 'Toilets', 'General Areas', 'Reception'].map((name, index) => ({ id: `area-${index + 1}`, name }));
export const METADATA_FIELDS: Record<QCCategory, [string, string][]> = {
  raw: [['grade', 'Grade'], ['sampledQuantity', 'Quantity sampled (receipt unit)'], ['coa', 'COA availability'], ['tds', 'TDS availability'], ['msds', 'MSDS availability'], ['additionalObservations', 'Additional observations'], ['acceptanceRemarks', 'Remarks on overall acceptance']],
  production: [['customer', 'Customer'], ['itemDetails', 'Item details'], ['description', 'Product description'], ['rollSize', 'Roll size'], ['thickness', 'Specified thickness']],
  machine: [['week', 'Week commencing'], ['maintenanceRemarks', 'Maintenance observations']],
  cleaning: [['cleaningMethod', 'Method of cleaning'], ['chemicals', 'Chemicals / instruments used (enter None if applicable)'], ['cleanedBy', 'Cleaned by']],
  safety: [],
};

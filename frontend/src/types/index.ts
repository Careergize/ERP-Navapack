export type Role =
  | "authenticated"
  | "qc_inspector"
  | "qc_supervisor"
  | "receptionist"
  | "project_manager"
  | "production_manager"
  | "store_keeper"
  | "production_operator"
  | "recycling_operator"
  | "accounts"
  | "admin";

export type Stage = "Extrusion" | "Printing" | "Packaging" | "Stock" | "Ready to Sale";

export type JobCardStatus =
  | "Draft"
  | "PendingApproval"
  | "Approved"
  | "Issued"
  | "InProduction"
  | "StoreIssuePending"
  | "MaterialIssued"
  | "OnHold"
  | "ReadyForStock"
  | "Completed";

export interface User {
  id: string;
  name: string;
  role: Role;
  department?: string;
  permissions?: string[];
  roles?: string[];
  backendSession?: boolean;
  isMasterAdmin?: boolean;
}

export type CustomerType = "B2B" | "B2C";
export interface SalesOrderItem {
  led?: import('@/lib/led').LEDInput;
  ledSnapshot?: import('@/lib/led').LEDSnapshot;
  quotationLineId?: string;
  quotationCostEstimateId?: string;
  quotationCostEstimateRevision?: number;
  id: string;
  modelId?: string;
  modelRevision?: number;
  specifications?: string;
  requiredDate?: string;
  estimateId?: string;
  fulfillmentSource?: "stock" | "manufacturing";
  itemId?: string;
  itemName: string;
  quantity: number;
  unit: string;
  unitPrice: number;
  totalPrice: number;
}

export interface SalesOrder {
  quotationId?: string;
  quotationRevisionId?: string;
  quotationNumber?: string;
  quotationRevision?: number;
  prospectId?: string;
  customerContact?: import('@/lib/quotations').QuotationCustomer;
  commercialTerms?: import('@/lib/quotations').QuotationTerms;
  commercialPricing?: { taxMode: import('@/lib/commercialPricing').TaxMode; discount: number; roundingPolicy: string };

  taxRate?: number;
  currency?: string;
  customerId?: string;
  marketingPersonName?: string;
  customerType?: CustomerType;
  requisitionOrder?: string;
  items?: SalesOrderItem[];
  orderTotal?: number;
  id: string;
  orderNumber: string;
  customerName: string;
  date: string;
  status: "Open" | "Completed" | "Draft" | "Approved" | "Reserved" | "In Production" | "Ready for Stock" | "Stock Received" | "Partially Dispatched" | "Dispatched" | "Cancelled";
  jobCardIds: string[];
}

export interface JobCardStageEntry {
  stage: Stage;
  sequenceOrder: number;
  required: boolean;
  status: "Pending" | "InProgress" | "Complete";
}

export interface JobCard {
  productionRuns?: { completesStage?: boolean; id: string; number: string; stageId: string; inputKG?: number; inputQuantity: number; outputQuantity: number; wasteQuantity: number; inputUnit: string; outputUnit: string; wasteUnit: string; startedAt: string; completedAt: string; operator: string; remarks: string }[];
  productionBatches?: { id: string; number: string; stageId: string; quantity: number; unit: string; createdAt: string }[];
  /** Present only on new parent cards; legacy single-product records stay unchanged. */
  manufacturingItems?: JobCard[];
  parentJobCardId?: string;
  origin?: 'sales_order' | 'production_for_stock';
  id: string;
  jobCardNumber: string;
  salesOrderId: string;
  salesOrderItemId?: string;
  finishedProductId?: string;
  modelId?: string;
  modelRevision?: number;
  estimateId?: string;
  estimateRevision?: number;
  routingRevision?: number;
  routingApproved?: { revision: number; stages: JobProductionStage[]; materials: JobCardMaterial[]; approvedBy: string; approvedAt: string };
  routingApprovalHistory?: NonNullable<JobCard['routingApproved']>[];
  requirementsReviewRequired?: boolean;
  modelName: string;
  qty: number;
  status: JobCardStatus;
  department: string;
  stages: JobCardStageEntry[];
  salesOrderNumber?: string;
  customerName?: string;
  product?: string;
  specifications?: string;
  productionRequirements?: string;
  unit?: string;
  createdDate?: string;
  requiredDate?: string;
  approval?: { approvedBy: string; approvedAt: string };
  requiredMaterials?: JobCardMaterial[];
  productionStages?: JobProductionStage[];
  activityHistory?: JobCardActivity[];
  acceptedQuantity?: number;
  rejectedQuantity?: number;
  stockReceiptPending?: boolean;
  stockTransfers?: { id: string; batch: string; quantity: number; rejectedQuantity: number; date: string }[];
  stockTransfer?: { quantity: number; unit: string; batchDate: string; confirmedBy: string; confirmedAt: string; jobCardId: string; salesOrderId: string; customerName: string; modelName: string; product: string };
}

export interface JobCardMaterial {
  id: string;
  materialId?: string;
  name: string;
  requiredQuantity: number;
  issuedQuantity: number;
  unit: string;
}
export type ProductionStageStatus = "Pending" | "Received" | "InProgress" | "Completed" | "OnHold";
export interface JobProductionStage {
  qcTemplateIds?: string[];
  machineId?: string;
  id: string;
  name: string;
  department: string;
  sequence: number;
  required: boolean;
  kind: "production" | "stock";
  legacyStage?: Stage;
  status: ProductionStageStatus;
  inputQuantity: number | null;
  outputQuantity: number | null;
  wasteQuantity: number | null;
  inputUnit: string;
  outputUnit: string;
  wasteUnit: string;
  startedAt?: string;
  completedAt?: string;
  machine?: string;
  expectedInput?: number;
  expectedOutput?: number;
  plannedWastePercent?: number;
  instructions?: string;
  operator: string;
  remarks: string;
  handover?: { quantity: number; unit: string; fromStageId: string };
  wasteType?: string;
  wasteReason?: string;
  sentToRecycling?: number;
}
export interface JobCardActivity {
  jobCardId?: string;
  manufacturingItemId?: string;
  id: string;
  timestamp: string;
  action: string;
  user: string;
  department: string;
  description: string;
}

export interface TraceResult {
  traceId: string;
  type: "SalesOrder" | "JobCard" | "MaterialBatch" | "GranulesBatch";
  currentStatus: string;
  currentStage?: Stage;
  history: { label: string; timestamp: string }[];
}

export interface WasteEntry {
  id: string;
  jobCardNumber: string;
  stage: Stage;
  wasteQty: number;
  unit: "kg";
  wasteType: string;
  sentToRecycling: boolean;
  date: string;
}

export interface GranulesBatch {
  id: string;
  batchNumber: string;
  date: string;
  inputWasteQty: number;
  granulesProducedKg: number;
  destination: "Restocked as raw material" | "Sold externally" | "Partially sold";
  reEnteredQty?: number;
  soldQty?: number;
  soldTo?: string;
}

export interface CostingRecord {
  id: string;
  itemOrModel: string;
  rawMaterialCost: number;
  productionCost: number;
  otherCost: number;
  currency: "USD" | "NGN" | "GHS" | "ZAR";
  exchangeRateUsed: number;
  totalCostLocal: number;
  lastUpdated: string;
}

export interface ExchangeRate {
  id: string;
  currency: string;
  rate: number;
  date: string;
  enteredBy: string;
}

export interface Item {
  id: string;
  name: string;
  unit: string;
  category: string;
}

export interface Model {
  id: string;
  name: string;
  revision?: number;
  category?: string;
  description?: string;
  specifications?: string;
  dimensions?: string;
  defaultUnit?: string;
  recipe?: import('@/lib/customCosting').MaterialRecipe[];
  recipeMode?: 'quantities' | 'percentages';
  batchQuantity?: number;
  batchUnit?: string;
  processes?: import('@/lib/customCosting').ProcessCost[];
  routing?: JobProductionStage[];
  wastePercent?: number;
  overheads?: number;
  costingConfig?: { currency: 'USD' | 'UGX'; markupPercent: number; taxPercent: number };
  billOfMaterials: string;
  stages: Stage[];
}

export interface Customer {
  code?: string;
  prospectId?: string;
  billingAddress?: string;
  deliveryAddress?: string;
  email?: string;
  tin?: string;
  customerType?: CustomerType;
  id: string;
  name: string;
  contactPerson: string;
  phone: string;
}

export interface Supplier {
  id: string;
  name: string;
  materialSupplied: string;
  phone: string;
}

export interface Department {
  id: string;
  name: string;
  assignedProductionManager: string;
}

export interface MasterUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  department?: string;
}

import * as React from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  ShieldAlert,
  Upload,
  XCircle,
  Play,
  Trash2,
  Layers,
  Building2,
  ShieldCheck,
  Sun,
  Moon,
  Filter,
  CheckCheck,
  FileCheck2,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  component: Index,
});

const API_BASE_URL =
  (import.meta.env["VITE_API_BASE_URL"] as string | undefined) ?? "http://localhost:8001/api/v1";

const DEFAULT_TENDER_ID = "GEM-2026-CPCL-001";
const DEFAULT_MIN_LOCAL_CONTENT = 50;

type RiskTier = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
type ClauseStatus = "PASS" | "FAIL" | "WARNING";

interface ClauseAuditResult {
  clause_id: string;
  clause_title: string;
  is_mandatory: boolean;
  status: ClauseStatus;
  extracted_value: string | null;
  expected_value: string | null;
  discrepancy_notes: string | null;
  risk_penalty: number;
}

interface BidComplianceReport {
  tender_id: string;
  bidder_name: string;
  compliance_score: number;
  risk_tier: RiskTier;
  is_debarred: boolean;
  evaluated_at: string;
  clause_results: ClauseAuditResult[];
  executive_summary: string;
  recommended_action: string;
}

interface QueueItem {
  id: string;
  file: File;
  status: "QUEUED" | "PROCESSING" | "COMPLETED" | "ERROR";
  report?: BidComplianceReport;
  error?: string;
}

const RISK_STYLES: Record<RiskTier, string> = {
  LOW: "border-emerald-300 bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:border-emerald-700 dark:text-emerald-300",
  MEDIUM: "border-amber-300 bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:border-amber-700 dark:text-amber-300",
  HIGH: "border-rose-300 bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:border-rose-700 dark:text-rose-300",
  CRITICAL: "border-red-600 bg-red-600 text-white dark:bg-red-950 dark:border-red-700 dark:text-red-200",
};

const SCORE_BAR_STYLES: Record<RiskTier, string> = {
  LOW: "[&>div]:bg-emerald-600 dark:[&>div]:bg-emerald-500",
  MEDIUM: "[&>div]:bg-amber-500 dark:[&>div]:bg-amber-400",
  HIGH: "[&>div]:bg-rose-600 dark:[&>div]:bg-rose-500",
  CRITICAL: "[&>div]:bg-red-700 dark:[&>div]:bg-red-600",
};

const STATUS_STYLES: Record<ClauseStatus, string> = {
  PASS: "border-emerald-300 bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:border-emerald-700 dark:text-emerald-300",
  WARNING: "border-amber-300 bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:border-amber-700 dark:text-amber-300",
  FAIL: "border-rose-300 bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:border-rose-700 dark:text-rose-300",
};

function StatusIcon({ status }: { status: ClauseStatus }) {
  if (status === "PASS") return <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 inline mr-1" />;
  if (status === "WARNING") return <AlertTriangle className="size-4 text-amber-600 dark:text-amber-400 inline mr-1" />;
  return <XCircle className="size-4 text-rose-600 dark:text-rose-400 inline mr-1" />;
}

function formatEvaluatedAt(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

async function evaluateBid(
  file: File,
  tenderId: string,
  minLocalContentPct: number
): Promise<BidComplianceReport> {
  const body = new FormData();
  body.append("file", file);
  body.append("tender_id", tenderId);
  body.append("min_local_content_pct", String(minLocalContentPct));

  const response = await fetch(`${API_BASE_URL}/tenders/evaluate`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Evaluation failed with status ${response.status}`;
    throw new Error(detail);
  }
  return (await response.json()) as BidComplianceReport;
}

function Index() {
  const [tenderId, setTenderId] = React.useState(DEFAULT_TENDER_ID);
  const [minLocalContent, setMinLocalContent] = React.useState<number>(DEFAULT_MIN_LOCAL_CONTENT);
  const [queue, setQueue] = React.useState<QueueItem[]>([]);
  const [selectedQueueId, setSelectedQueueId] = React.useState<string | null>(null);
  const [isProcessingQueue, setIsProcessingQueue] = React.useState(false);
  const [isDragging, setIsDragging] = React.useState(false);
  const [riskFilter, setRiskFilter] = React.useState<string>("ALL");
  const [isDark, setIsDark] = React.useState<boolean>(() => {
    if (typeof window !== "undefined") {
      return document.documentElement.classList.contains("dark") ||
        localStorage.getItem("theme") === "dark";
    }
    return false;
  });

  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark((prev) => !prev);

  const addFilesToQueue = (files: FileList | File[]) => {
    const newItems: QueueItem[] = Array.from(files)
      .filter((f) => f.name.toLowerCase().endsWith(".pdf"))
      .map((file) => ({
        id: `${file.name}-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        file,
        status: "QUEUED",
      }));

    if (newItems.length === 0) return;

    setQueue((prev) => {
      const updated = [...prev, ...newItems];
      if (!selectedQueueId && newItems[0]) {
        setSelectedQueueId(newItems[0].id);
      }
      return updated;
    });
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      addFilesToQueue(e.dataTransfer.files);
    }
  };

  const removeItem = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setQueue((prev) => {
      const filtered = prev.filter((item) => item.id !== id);
      if (selectedQueueId === id) {
        setSelectedQueueId(filtered[0]?.id ?? null);
      }
      return filtered;
    });
  };

  const clearQueue = () => {
    if (isProcessingQueue) return;
    setQueue([]);
    setSelectedQueueId(null);
  };

  const runSequentialBatchAudit = async () => {
    if (isProcessingQueue || queue.length === 0) return;
    setIsProcessingQueue(true);

    for (let i = 0; i < queue.length; i++) {
      const current = queue[i];
      if (!current || current.status === "COMPLETED") continue;

      setQueue((prev) =>
        prev.map((item) =>
          item.id === current.id ? { ...item, status: "PROCESSING", error: undefined } : item
        )
      );

      try {
        const report = await evaluateBid(current.file, tenderId, minLocalContent);
        setQueue((prev) =>
          prev.map((item) =>
            item.id === current.id ? { ...item, status: "COMPLETED", report } : item
          )
        );
        setSelectedQueueId(current.id);
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : "Audit evaluation failed";
        setQueue((prev) =>
          prev.map((item) =>
            item.id === current.id ? { ...item, status: "ERROR", error: errMsg } : item
          )
        );
      }
    }
    setIsProcessingQueue(false);
  };

  const filteredQueue = queue.filter((item) => {
    if (riskFilter === "ALL") return true;
    if (riskFilter === "LOW") return item.report?.risk_tier === "LOW";
    if (riskFilter === "REVIEW") return item.report?.risk_tier === "MEDIUM" || item.report?.risk_tier === "HIGH";
    if (riskFilter === "CRITICAL") return item.report?.risk_tier === "CRITICAL" || item.report?.is_debarred;
    return true;
  });

  const selectedItem = queue.find((item) => item.id === selectedQueueId) ?? queue[0];
  const completedReports = queue
    .map((q) => q.report)
    .filter((r): r is BidComplianceReport => r !== undefined);

  const stats = {
    total: queue.length,
    completed: completedReports.length,
    lowRisk: completedReports.filter((r) => r.risk_tier === "LOW").length,
    highRisk: completedReports.filter((r) => r.risk_tier === "HIGH" || r.risk_tier === "MEDIUM").length,
    critical: completedReports.filter((r) => r.risk_tier === "CRITICAL" || r.is_debarred).length,
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-200">
      {/* Top App Header */}
      <header className="border-b bg-card/50 backdrop-blur-md sticky top-0 z-30 px-6 py-3.5">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight sm:text-xl">BidGuard AI</h1>
                <Badge variant="outline" className="text-[10px] py-0 h-4 border-primary/30 text-primary">
                  v0.2 Enterprise
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                GeM Statutory Bid Compliance &amp; Automated Evaluation Engine (SIH26100)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="outline" className="hidden sm:flex gap-1.5 border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400 text-xs py-1">
              <ShieldAlert className="size-3.5" />
              SANDBOX GATEWAY
            </Badge>

            <Button
              variant="outline"
              size="icon"
              onClick={toggleTheme}
              className="h-9 w-9 rounded-lg border bg-background"
              title="Toggle Light/Dark Theme"
            >
              {isDark ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-700" />}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Wide Layout */}
      <main className="mx-auto max-w-[1600px] p-6 space-y-6">
        {/* Top Summary Metric Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card className="p-4 shadow-sm border bg-card">
            <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Total Documents</div>
            <div className="text-2xl font-black mt-1">
              {stats.completed} <span className="text-xs font-normal text-muted-foreground">/ {stats.total} in batch</span>
            </div>
            <Progress value={stats.total ? (stats.completed / stats.total) * 100 : 0} className="mt-2.5 h-1.5" />
          </Card>

          <Card className="p-4 shadow-sm border border-emerald-500/20 bg-emerald-500/5">
            <div className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center justify-between">
              <span>Compliant (Low)</span>
              <CheckCheck className="size-3.5" />
            </div>
            <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">{stats.lowRisk}</div>
            <div className="text-[11px] text-muted-foreground mt-1">Eligible for technical qualification</div>
          </Card>

          <Card className="p-4 shadow-sm border border-amber-500/20 bg-amber-500/5">
            <div className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider flex items-center justify-between">
              <span>Under Review</span>
              <AlertTriangle className="size-3.5" />
            </div>
            <div className="text-2xl font-black text-amber-600 dark:text-amber-400 mt-1">{stats.highRisk}</div>
            <div className="text-[11px] text-muted-foreground mt-1">Discrepancy / Turnover warnings</div>
          </Card>

          <Card className="p-4 shadow-sm border border-rose-500/20 bg-rose-500/5">
            <div className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider flex items-center justify-between">
              <span>Disqualified</span>
              <ShieldAlert className="size-3.5" />
            </div>
            <div className="text-2xl font-black text-rose-600 dark:text-rose-400 mt-1">{stats.critical}</div>
            <div className="text-[11px] text-muted-foreground mt-1">Debarred or severe failures</div>
          </Card>
        </div>

        {/* 3-Column Wide Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Column 1: Tender Config & Upload Area (3 Cols) */}
          <div className="lg:col-span-3 space-y-4">
            <Card className="shadow-sm border">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Upload className="size-4 text-primary" /> Tender Ingestion
                </CardTitle>
                <CardDescription className="text-xs">
                  Drop single or multiple GeM technical bid PDFs.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  className={cn(
                    "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-center transition-all",
                    isDragging
                      ? "border-primary bg-primary/10"
                      : "border-muted-foreground/20 hover:border-primary/50 hover:bg-muted/40"
                  )}
                >
                  <div className="p-3 rounded-full bg-primary/10 text-primary">
                    <Upload className="size-5" />
                  </div>
                  <span className="text-xs font-semibold">Drop PDF bids here</span>
                  <span className="text-[11px] text-muted-foreground">or click to browse from disk</span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="application/pdf,.pdf"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files) addFilesToQueue(e.target.files);
                      e.target.value = "";
                    }}
                  />
                </div>

                <div className="space-y-3 pt-1">
                  <div className="space-y-1">
                    <Label htmlFor="tender-id" className="text-xs">Tender Ref ID</Label>
                    <Input
                      id="tender-id"
                      className="h-8 text-xs bg-muted/20"
                      value={tenderId}
                      onChange={(e) => setTenderId(e.target.value)}
                    />
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="min-local-content" className="text-xs">Min Local Content Requirement (%)</Label>
                    <Input
                      id="min-local-content"
                      className="h-8 text-xs bg-muted/20"
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      value={minLocalContent}
                      onChange={(e) => setMinLocalContent(Number(e.target.value))}
                    />
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button
                    onClick={runSequentialBatchAudit}
                    disabled={isProcessingQueue || queue.length === 0}
                    className="flex-1 h-9 text-xs font-semibold"
                  >
                    {isProcessingQueue ? (
                      <>
                        <Loader2 className="mr-2 size-3.5 animate-spin" /> Auditing Batch...
                      </>
                    ) : (
                      <>
                        <Play className="mr-2 size-3.5" /> Start Audit
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={clearQueue}
                    disabled={isProcessingQueue || queue.length === 0}
                    title="Clear All Files"
                    className="h-9 w-9"
                  >
                    <Trash2 className="size-3.5 text-muted-foreground" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Column 2: Live Queue & Document Selector (3 Cols) */}
          <div className="lg:col-span-3 space-y-4">
            <Card className="shadow-sm border">
              <CardHeader className="py-3 px-4 border-b flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-muted-foreground">
                  <Layers className="size-3.5" /> Audit Queue ({queue.length})
                </CardTitle>
                <div className="flex items-center gap-1">
                  <Filter className="size-3 text-muted-foreground" />
                  <select
                    value={riskFilter}
                    onChange={(e) => setRiskFilter(e.target.value)}
                    className="text-[11px] bg-transparent border-0 font-medium text-muted-foreground focus:outline-none cursor-pointer"
                  >
                    <option value="ALL">All Bids</option>
                    <option value="LOW">Low Risk</option>
                    <option value="REVIEW">Under Review</option>
                    <option value="CRITICAL">Disqualified</option>
                  </select>
                </div>
              </CardHeader>
              <CardContent className="p-2 space-y-1.5 max-h-[620px] overflow-y-auto">
                {filteredQueue.length === 0 ? (
                  <div className="text-center py-16 text-xs text-muted-foreground">
                    No matching documents in queue.
                  </div>
                ) : (
                  filteredQueue.map((item, idx) => (
                    <div
                      key={item.id}
                      onClick={() => setSelectedQueueId(item.id)}
                      className={cn(
                        "flex items-center justify-between p-2.5 rounded-lg border text-xs cursor-pointer transition-all",
                        selectedItem?.id === item.id
                          ? "border-primary/50 bg-primary/10 shadow-xs dark:bg-primary/20"
                          : "border-transparent hover:bg-muted/50"
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0 pr-2">
                        <span className="font-mono text-muted-foreground text-[10px]">#{idx + 1}</span>
                        <FileText className="size-4 shrink-0 text-muted-foreground" />
                        <div className="truncate">
                          <p className="font-semibold truncate">{item.report?.bidder_name ?? item.file.name}</p>
                          <p className="text-[10px] text-muted-foreground truncate">{item.file.name}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {item.status === "QUEUED" && (
                          <Badge variant="outline" className="text-[10px] py-0">QUEUED</Badge>
                        )}
                        {item.status === "PROCESSING" && (
                          <Badge className="bg-primary/80 text-[10px] py-0 animate-pulse text-primary-foreground">
                            <Loader2 className="size-2.5 mr-1 animate-spin" /> AUDITING
                          </Badge>
                        )}
                        {item.status === "ERROR" && (
                          <Badge variant="destructive" className="text-[10px] py-0">ERROR</Badge>
                        )}
                        {item.status === "COMPLETED" && item.report && (
                          <Badge className={cn("text-[10px] py-0 font-bold", RISK_STYLES[item.report.risk_tier])}>
                            {item.report.compliance_score.toFixed(0)}
                          </Badge>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          disabled={isProcessingQueue}
                          onClick={(e) => removeItem(item.id, e)}
                          className="h-6 w-6 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="size-3" />
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          {/* Column 3: Full Audit Report & Clause Inspector (6 Cols) */}
          <div className="lg:col-span-6">
            {!selectedItem ? (
              <Card className="h-[520px] flex items-center justify-center text-center border shadow-sm">
                <CardContent className="space-y-3 py-16 text-muted-foreground">
                  <FileCheck2 className="size-12 mx-auto stroke-1" />
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground">Select a Document</p>
                    <p className="text-xs">Upload bid files and select a row to inspect its statutory compliance verification.</p>
                  </div>
                </CardContent>
              </Card>
            ) : selectedItem.status === "PROCESSING" ? (
              <Card className="h-[520px] flex items-center justify-center border shadow-sm">
                <CardContent className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
                  <Loader2 className="size-10 animate-spin text-primary" />
                  <p className="text-sm font-semibold text-foreground">Auditing {selectedItem.file.name}...</p>
                  <p className="text-xs">Extracting statutory fields and cross-reconciling GSTN, Udyam, &amp; Debarment registries.</p>
                </CardContent>
              </Card>
            ) : selectedItem.status === "ERROR" ? (
              <Alert variant="destructive">
                <AlertTriangle className="size-4" />
                <AlertTitle>Evaluation Error for {selectedItem.file.name}</AlertTitle>
                <AlertDescription className="text-xs mt-1">{selectedItem.error}</AlertDescription>
              </Alert>
            ) : selectedItem.report ? (
              <ReportInspector report={selectedItem.report} filename={selectedItem.file.name} />
            ) : (
              <Card className="h-[520px] flex items-center justify-center text-center border shadow-sm">
                <CardContent className="space-y-2 py-16 text-muted-foreground">
                  <Play className="size-10 mx-auto stroke-1 text-primary" />
                  <p className="text-sm font-semibold text-foreground">{selectedItem.file.name}</p>
                  <p className="text-xs">File is queued. Click "Start Audit" on the left to process.</p>
                </CardContent>
              </Card>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}

function ReportInspector({ report, filename }: { report: BidComplianceReport; filename: string }) {
  return (
    <div className="space-y-4 animate-in fade-in-50 duration-200">
      {/* Debarment Critical Banner */}
      {report.is_debarred && (
        <Alert variant="destructive" className="bg-red-950 text-red-100 border-red-800">
          <ShieldAlert className="size-4 text-red-400" />
          <AlertTitle className="text-sm font-bold">CRITICAL: Bidder is Debarred / Blacklisted</AlertTitle>
          <AlertDescription className="text-xs mt-1 text-red-200">
            {report.recommended_action}
          </AlertDescription>
        </Alert>
      )}

      {/* Main Score Header Card */}
      <Card className="shadow-sm border">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Building2 className="size-4 text-muted-foreground" />
                {report.bidder_name}
              </CardTitle>
              <CardDescription className="text-xs mt-0.5">
                File: <span className="font-mono text-foreground">{filename}</span> · Tender: {report.tender_id} · Audited: {formatEvaluatedAt(report.evaluated_at)}
              </CardDescription>
            </div>
            <Badge className={cn("text-xs font-semibold px-3 py-1", RISK_STYLES[report.risk_tier])}>
              {report.risk_tier} RISK
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between text-xs">
              <span className="font-medium text-muted-foreground">Statutory Compliance Score</span>
              <span className="text-2xl font-black text-foreground">
                {report.compliance_score.toFixed(1)} <span className="text-xs font-normal text-muted-foreground">/ 100</span>
              </span>
            </div>
            <Progress value={report.compliance_score} className={cn("h-2.5", SCORE_BAR_STYLES[report.risk_tier])} />
          </div>

          <div className="rounded-lg border bg-muted/40 p-3 text-xs leading-relaxed">
            <span className="font-semibold text-primary mr-1">Recommended Auditor Action:</span>
            {report.recommended_action}
          </div>
        </CardContent>
      </Card>

      {/* Detailed Clause Audit Table & Executive Summary */}
      <Tabs defaultValue="clauses" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="clauses" className="text-xs">
            Statutory Clauses ({report.clause_results.length})
          </TabsTrigger>
          <TabsTrigger value="summary" className="text-xs">
            Executive Summary
          </TabsTrigger>
        </TabsList>

        <TabsContent value="clauses" className="mt-3">
          <Card className="shadow-sm border">
            <CardContent className="p-0 overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs">
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead>Clause</TableHead>
                    <TableHead>Declared / Extracted</TableHead>
                    <TableHead>Expected / Registry</TableHead>
                    <TableHead className="text-right">Penalty</TableHead>
                    <TableHead className="max-w-xs">Audit Findings</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.clause_results.map((clause) => (
                    <TableRow key={clause.clause_id} className="text-xs">
                      <TableCell>
                        <Badge className={cn("text-[10px] font-medium py-0.5", STATUS_STYLES[clause.status])}>
                          <StatusIcon status={clause.status} />
                          {clause.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">
                        {clause.clause_title}
                        <div className="text-[10px] text-muted-foreground font-mono">
                          {clause.clause_id} · {clause.is_mandatory ? "mandatory" : "optional"}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        {clause.extracted_value ?? "—"}
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        {clause.expected_value ?? "—"}
                      </TableCell>
                      <TableCell className="text-right font-semibold text-rose-600 dark:text-rose-400 font-mono">
                        {clause.risk_penalty > 0 ? `-${clause.risk_penalty.toFixed(1)}` : "0.0"}
                      </TableCell>
                      <TableCell className="text-muted-foreground max-w-xs text-[11px] leading-relaxed">
                        {clause.discrepancy_notes ?? "Satisfied statutory requirement."}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="summary" className="mt-3">
          <Card className="shadow-sm border">
            <CardContent className="p-5 text-xs text-muted-foreground leading-relaxed whitespace-pre-line">
              {report.executive_summary}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default Index;